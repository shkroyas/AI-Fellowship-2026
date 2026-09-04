"""
Task 2: Production AI Assistant Backend.

Enhanced version of the Task 1 backend with production features:
- Rate limiting
- Retry mechanism
- Fallback provider
- Response caching
- Concurrent request handling
- Error handling & graceful degradation
"""

import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Import from Task 1 (shared codebase)
import sys
import os

# Add task1 to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "task1-ai-assistant"))

from app.config import settings
from app.llm.provider import ChatMessage, get_provider, LLMResponse
from app.prompts.system_prompts import (
    ASSISTANT_SYSTEM_PROMPT,
    RAG_SYSTEM_PROMPT,
    PROMPT_CONFIGS,
    ANALYSIS_SCHEMA,
    STRUCTURED_OUTPUT_PROMPT,
)
from app.rag.retriever import RAGRetriever
from app.tools.registry import tool_registry
from app.tools.calculator import calculator_tool
from app.tools.web_search import web_search_tool, datetime_tool

from middleware.rate_limiter import RateLimiterMiddleware, rate_limiter
from middleware.retry import RetryHandler
from middleware.cache import ResponseCache
from middleware.fallback import FallbackManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ── Global instances ──
rag_retriever: Optional[RAGRetriever] = None
retry_handler = RetryHandler(max_retries=3, base_delay=1.0, max_delay=30.0)
response_cache = ResponseCache(max_size=1000, ttl_seconds=300)
fallback_manager = FallbackManager()


def register_tools():
    """Register all available tools."""
    for tool_def in [calculator_tool, web_search_tool, datetime_tool]:
        tool_registry.register(
            name=tool_def["name"],
            description=tool_def["description"],
            parameters=tool_def["parameters"],
            executor=tool_def["executor"],
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with production initialization."""
    global rag_retriever

    logger.info("🚀 Starting Production AI Assistant...")

    # Register tools
    register_tools()

    # Initialize RAG
    try:
        rag_retriever = RAGRetriever()
        count = rag_retriever.ingest_documents()
        logger.info(f"📚 Ingested {count} chunks")
    except Exception as e:
        logger.warning(f"RAG init warning: {e}")

    # Register fallback providers
    fallback_manager.register_providers(["gemini", "openai", "local_vllm"])

    logger.info("✅ Production AI Assistant ready")
    yield
    logger.info("👋 Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Production AI Assistant",
    description="Production-ready AI assistant with rate limiting, retry, caching, and fallback",
    version="2.0.0",
    lifespan=lifespan,
)

# ── Middleware Stack ──

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting
app.add_middleware(
    RateLimiterMiddleware,
    requests_per_minute=60,
    burst_size=10,
)


# ── Error Handling Middleware ──
@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    """Global error handling with graceful degradation."""
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = str(uuid.uuid4())
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Unhandled error after {process_time:.2f}s: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "The service encountered an unexpected error. Please try again.",
                "request_id": str(uuid.uuid4()),
            },
        )


# ── Request/Response Models ──

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    history: list[dict[str, str]] = Field(default_factory=list)
    use_rag: bool = True
    use_tools: bool = True
    prompt_style: str = "balanced"
    provider: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    tool_calls_made: list[dict[str, Any]] = Field(default_factory=list)
    rag_context_used: bool = False
    sources: list[str] = Field(default_factory=list)
    usage: dict[str, int] = Field(default_factory=dict)
    model: str = ""
    latency_ms: float = 0
    cached: bool = False
    retries: int = 0


class BatchChatRequest(BaseModel):
    """Batch chat request for concurrent processing."""
    requests: list[ChatRequest]


# ── Core Chat Logic ──

async def process_chat(request: ChatRequest) -> ChatResponse:
    """Process a single chat request with retry and fallback."""
    conversation_id = request.conversation_id or str(uuid.uuid4())
    start_time = time.time()

    # Check cache
    cache_key = response_cache.make_key(request.message, request.provider, request.prompt_style)
    cached = response_cache.get(cache_key)
    if cached:
        logger.info(f"Cache hit for: {request.message[:50]}")
        cached["cached"] = True
        cached["conversation_id"] = conversation_id
        return ChatResponse(**cached)

    retries = 0

    async def _do_chat(provider_name: Optional[str] = None) -> ChatResponse:
        nonlocal retries
        provider = get_provider(provider_name or request.provider)

        config = PROMPT_CONFIGS.get(request.prompt_style, PROMPT_CONFIGS["balanced"])
        provider.temperature = config["temperature"]
        provider.top_p = config["top_p"]

        messages = []
        system_prompt = ASSISTANT_SYSTEM_PROMPT

        rag_used = False
        sources = []
        if request.use_rag and rag_retriever:
            context = rag_retriever.build_context(request.message)
            if "No relevant documents found" not in context:
                system_prompt = RAG_SYSTEM_PROMPT.format(context=context)
                rag_used = True
                import re
                sources = re.findall(r'\[Source \d+: (.+?) \(', context)

        messages.append(ChatMessage(role="system", content=system_prompt))
        for h in request.history:
            messages.append(ChatMessage(role=h["role"], content=h["content"]))
        messages.append(ChatMessage(role="user", content=request.message))

        tools = tool_registry.get_definitions() if request.use_tools else None
        response = await provider.chat(messages=messages, tools=tools)

        tool_calls_made = []
        if response.tool_calls:
            for tc in response.tool_calls:
                result = await tool_registry.execute(tc.name, tc.arguments)
                tool_calls_made.append({
                    "tool": tc.name,
                    "arguments": tc.arguments,
                    "result": result,
                })
                messages.append(ChatMessage(role="assistant", content=f"Using {tc.name} tool."))
                messages.append(ChatMessage(role="tool", content=result, tool_call_id=tc.id))

            response = await provider.chat(messages=messages, tools=tools)

        latency_ms = (time.time() - start_time) * 1000

        return ChatResponse(
            response=response.content,
            conversation_id=conversation_id,
            tool_calls_made=tool_calls_made,
            rag_context_used=rag_used,
            sources=sources,
            usage=response.usage,
            model=response.model,
            latency_ms=latency_ms,
            retries=retries,
        )

    # Try with retry and fallback
    try:
        result = await retry_handler.execute(
            _do_chat,
            on_retry=lambda attempt, exc: logger.warning(
                f"Retry {attempt}: {exc}"
            ),
        )
        retries = retry_handler.last_attempt_count

        # Cache successful response
        response_cache.set(cache_key, result.model_dump())
        return result

    except Exception as primary_error:
        logger.error(f"Primary provider failed: {primary_error}")

        # Try fallback providers
        fallback_provider = fallback_manager.get_next_fallback(request.provider)
        if fallback_provider:
            logger.info(f"Trying fallback provider: {fallback_provider}")
            try:
                result = await _do_chat(fallback_provider)
                result.model = f"{result.model} (fallback)"
                return result
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")

        # Graceful degradation
        return ChatResponse(
            response=(
                "I apologize, but I'm currently experiencing difficulties connecting to the AI service. "
                "Please try again in a moment. If the issue persists, check the backend logs."
            ),
            conversation_id=conversation_id,
            model="degraded",
            latency_ms=(time.time() - start_time) * 1000,
        )


# ── API Endpoints ──

@app.get("/health")
async def health_check():
    """Comprehensive health check."""
    health = {
        "status": "healthy",
        "timestamp": time.time(),
        "components": {
            "rag": rag_retriever is not None,
            "tools": tool_registry.list_tools(),
            "cache": response_cache.stats(),
            "rate_limiter": rate_limiter.stats() if rate_limiter else {},
        },
    }

    # Check LLM provider
    try:
        provider = get_provider()
        llm_ok = await provider.health_check()
        health["components"]["llm"] = {"available": llm_ok, "provider": settings.llm_provider}
        if not llm_ok:
            health["status"] = "degraded"
    except Exception as e:
        health["components"]["llm"] = {"available": False, "error": str(e)}
        health["status"] = "degraded"

    return health


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Production chat endpoint with retry, caching, and fallback."""
    return await process_chat(request)


@app.post("/chat/batch")
async def batch_chat(batch: BatchChatRequest):
    """
    Process multiple chat requests concurrently.

    Handles concurrent/batch request processing for improved throughput.
    """
    if len(batch.requests) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 requests per batch")

    start_time = time.time()

    # Process all requests concurrently
    tasks = [process_chat(req) for req in batch.requests]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    responses = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            responses.append({
                "index": i,
                "error": str(result),
                "response": None,
            })
        else:
            responses.append({
                "index": i,
                "error": None,
                "response": result.model_dump(),
            })

    return {
        "batch_size": len(batch.requests),
        "total_time_ms": (time.time() - start_time) * 1000,
        "results": responses,
    }


@app.post("/documents/ingest")
async def ingest_document(text: str = None, source: str = "api_input"):
    """Ingest text into RAG knowledge base."""
    if not rag_retriever:
        raise HTTPException(status_code=503, detail="RAG not initialized")
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    chunks = rag_retriever.ingest_text(text, source)
    return {"chunks_added": chunks, "message": f"Ingested {chunks} chunks from '{source}'"}


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and ingest a document."""
    if not rag_retriever:
        raise HTTPException(status_code=503, detail="RAG not initialized")

    content = await file.read()
    text = content.decode("utf-8", errors="replace")
    chunks = rag_retriever.ingest_text(text, source=file.filename or "upload")
    return {"filename": file.filename, "chunks_added": chunks, "message": f"Ingested '{file.filename}'"}


@app.get("/documents/stats")
async def document_stats():
    """RAG pipeline statistics."""
    if not rag_retriever:
        return {"status": "not_initialized"}
    return rag_retriever.get_stats()


@app.get("/tools")
async def list_tools():
    """List available tools."""
    return {"tools": [{"name": td.name, "description": td.description} for td in tool_registry.get_definitions()]}


@app.get("/cache/stats")
async def cache_stats():
    """Get cache statistics."""
    return response_cache.stats()


@app.delete("/cache/clear")
async def clear_cache():
    """Clear the response cache."""
    response_cache.clear()
    return {"message": "Cache cleared"}


@app.get("/metrics")
async def metrics():
    """Application metrics for monitoring."""
    return {
        "cache": response_cache.stats(),
        "rate_limiter": rate_limiter.stats() if rate_limiter else {},
        "rag": rag_retriever.get_stats() if rag_retriever else None,
        "uptime": time.time(),
    }
