"""
AI Assistant - FastAPI Backend.

Main application entry point providing REST API endpoints for:
- Chat with AI (with optional RAG context)
- Document ingestion and management
- Tool calling
- Structured output generation
- Health checks
"""

import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import settings
from .llm.provider import (
    ChatMessage,
    LLMResponse,
    StructuredOutputSchema,
    ToolCall,
    get_provider,
)
from .prompts.system_prompts import (
    ASSISTANT_SYSTEM_PROMPT,
    RAG_SYSTEM_PROMPT,
    STRUCTURED_OUTPUT_PROMPT,
    PROMPT_CONFIGS,
    ANALYSIS_SCHEMA,
    QA_SCHEMA,
)
from .rag.retriever import RAGRetriever
from .tools.registry import tool_registry
from .tools.calculator import calculator_tool
from .tools.web_search import web_search_tool, datetime_tool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global instances
rag_retriever: Optional[RAGRetriever] = None


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
    """Application lifespan handler for startup/shutdown."""
    global rag_retriever

    logger.info("Starting AI Assistant...")

    # Register tools
    register_tools()
    logger.info(f"Registered tools: {tool_registry.list_tools()}")

    # Initialize RAG retriever
    try:
        rag_retriever = RAGRetriever()
        # Auto-ingest documents from sample_docs directory
        count = rag_retriever.ingest_documents()
        logger.info(f"Ingested {count} chunks from sample documents")
    except Exception as e:
        logger.warning(f"RAG initialization warning: {e}")

    yield

    logger.info("Shutting down AI Assistant...")


# Create FastAPI app
app = FastAPI(
    title="AI Assistant API",
    description=(
        "A robust AI assistant with RAG, tool calling, and structured output. "
        "Supports multiple LLM providers (Gemini, OpenAI, local vLLM)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/Response Models ──


class ChatRequest(BaseModel):
    """Chat request body."""
    message: str = Field(..., description="User message")
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID for context")
    history: list[dict[str, str]] = Field(default_factory=list, description="Conversation history")
    use_rag: bool = Field(default=True, description="Whether to use RAG for context")
    use_tools: bool = Field(default=True, description="Whether to enable tool calling")
    prompt_style: str = Field(default="balanced", description="Prompt style: creative, balanced, precise, deterministic")
    provider: Optional[str] = Field(default=None, description="LLM provider override")


class ChatResponse(BaseModel):
    """Chat response body."""
    response: str
    conversation_id: str
    tool_calls_made: list[dict[str, Any]] = Field(default_factory=list)
    rag_context_used: bool = False
    sources: list[str] = Field(default_factory=list)
    usage: dict[str, int] = Field(default_factory=dict)
    model: str = ""


class StructuredOutputRequest(BaseModel):
    """Request for structured JSON output."""
    message: str
    output_type: str = Field(default="analysis", description="Type: 'analysis' or 'qa'")
    custom_schema: Optional[dict] = Field(default=None, description="Custom JSON schema")
    provider: Optional[str] = Field(default=None)


class IngestRequest(BaseModel):
    """Document ingestion request."""
    text: Optional[str] = Field(default=None, description="Raw text to ingest")
    source: str = Field(default="api_input", description="Source identifier")


class IngestResponse(BaseModel):
    """Document ingestion response."""
    chunks_added: int
    message: str


# ── API Endpoints ──


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    provider = get_provider()
    llm_healthy = await provider.health_check()

    return {
        "status": "healthy" if llm_healthy else "degraded",
        "llm_provider": settings.llm_provider,
        "llm_available": llm_healthy,
        "rag_initialized": rag_retriever is not None,
        "tools_registered": tool_registry.list_tools(),
        "rag_stats": rag_retriever.get_stats() if rag_retriever else None,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint.

    Processes user messages with optional RAG context and tool calling.
    Supports multiple LLM providers and prompt engineering styles.
    """
    conversation_id = request.conversation_id or str(uuid.uuid4())

    try:
        # Get LLM provider
        provider = get_provider(request.provider)

        # Apply prompt style configuration
        config = PROMPT_CONFIGS.get(request.prompt_style, PROMPT_CONFIGS["balanced"])
        provider.temperature = config["temperature"]
        provider.top_p = config["top_p"]

        # Build messages
        messages = []

        # System prompt
        system_prompt = ASSISTANT_SYSTEM_PROMPT

        # Add RAG context if enabled
        rag_used = False
        sources = []
        if request.use_rag and rag_retriever:
            context = rag_retriever.build_context(request.message)
            if "No relevant documents found" not in context:
                system_prompt = RAG_SYSTEM_PROMPT.format(context=context)
                rag_used = True
                # Extract source names
                import re
                sources = re.findall(r'\[Source \d+: (.+?) \(', context)

        messages.append(ChatMessage(role="system", content=system_prompt))

        # Add conversation history
        for h in request.history:
            messages.append(ChatMessage(role=h["role"], content=h["content"]))

        # Add current message
        messages.append(ChatMessage(role="user", content=request.message))

        # Get tool definitions if enabled
        tools = tool_registry.get_definitions() if request.use_tools else None

        # Call LLM
        response = await provider.chat(messages=messages, tools=tools)

        # Handle tool calls if any
        tool_calls_made = []
        if response.tool_calls:
            for tc in response.tool_calls:
                result = await tool_registry.execute(tc.name, tc.arguments)
                tool_calls_made.append({
                    "tool": tc.name,
                    "arguments": tc.arguments,
                    "result": result,
                })

                # Add tool call and result to messages for follow-up
                messages.append(ChatMessage(
                    role="assistant",
                    content=f"I'll use the {tc.name} tool.",
                ))
                messages.append(ChatMessage(
                    role="tool",
                    content=result,
                    tool_call_id=tc.id,
                ))

            # Get final response incorporating tool results
            response = await provider.chat(messages=messages, tools=tools)

        return ChatResponse(
            response=response.content,
            conversation_id=conversation_id,
            tool_calls_made=tool_calls_made,
            rag_context_used=rag_used,
            sources=sources,
            usage=response.usage,
            model=response.model,
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/structured", response_model=dict)
async def structured_chat(request: StructuredOutputRequest):
    """
    Generate structured JSON output from the AI.

    Supports predefined schemas (analysis, qa) or custom schemas.
    """
    try:
        provider = get_provider(request.provider)
        provider.temperature = 0.2  # Low temperature for structured output

        # Select schema
        if request.custom_schema:
            schema = request.custom_schema
            schema_name = "custom"
        elif request.output_type == "analysis":
            schema = ANALYSIS_SCHEMA
            schema_name = "analysis"
        elif request.output_type == "qa":
            schema = QA_SCHEMA
            schema_name = "qa"
        else:
            raise HTTPException(status_code=400, detail=f"Unknown output type: {request.output_type}")

        messages = [
            ChatMessage(role="system", content=STRUCTURED_OUTPUT_PROMPT),
            ChatMessage(role="user", content=request.message),
        ]

        structured_schema = StructuredOutputSchema(
            name=schema_name,
            description=f"Structured {schema_name} output",
            schema_dict=schema,
        )

        response = await provider.chat(
            messages=messages,
            structured_output=structured_schema,
        )

        # Parse and validate the JSON output
        try:
            result = json.loads(response.content)
        except json.JSONDecodeError:
            result = {"raw_response": response.content, "error": "Failed to parse as JSON"}

        return {
            "output": result,
            "schema_used": schema_name,
            "model": response.model,
            "usage": response.usage,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Structured output error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/ingest", response_model=IngestResponse)
async def ingest_document(request: IngestRequest):
    """Ingest text into the RAG knowledge base."""
    if not rag_retriever:
        raise HTTPException(status_code=503, detail="RAG system not initialized")

    if not request.text:
        raise HTTPException(status_code=400, detail="No text provided")

    try:
        chunks = rag_retriever.ingest_text(request.text, request.source)
        return IngestResponse(
            chunks_added=chunks,
            message=f"Successfully ingested {chunks} chunks from '{request.source}'",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and ingest a document file."""
    if not rag_retriever:
        raise HTTPException(status_code=503, detail="RAG system not initialized")

    try:
        content = await file.read()
        text = content.decode("utf-8", errors="replace")
        chunks = rag_retriever.ingest_text(text, source=file.filename or "upload")

        return {
            "filename": file.filename,
            "chunks_added": chunks,
            "message": f"Successfully ingested '{file.filename}' ({chunks} chunks)",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/stats")
async def document_stats():
    """Get RAG pipeline statistics."""
    if not rag_retriever:
        return {"status": "not_initialized"}
    return rag_retriever.get_stats()


@app.get("/tools")
async def list_tools():
    """List all available tools."""
    return {
        "tools": [
            {
                "name": td.name,
                "description": td.description,
                "parameters": td.parameters,
            }
            for td in tool_registry.get_definitions()
        ]
    }


@app.get("/config")
async def get_config():
    """Get current configuration (non-sensitive)."""
    return {
        "llm_provider": settings.llm_provider,
        "model": {
            "gemini": settings.gemini_model,
            "openai": settings.openai_model,
            "vllm": settings.vllm_model,
        },
        "generation": {
            "temperature": settings.temperature,
            "top_p": settings.top_p,
            "max_tokens": settings.max_tokens,
        },
        "rag": {
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
            "embedding_model": settings.embedding_model,
            "retrieval_top_k": settings.retrieval_top_k,
        },
        "prompt_styles": {
            name: config["description"]
            for name, config in PROMPT_CONFIGS.items()
        },
    }
