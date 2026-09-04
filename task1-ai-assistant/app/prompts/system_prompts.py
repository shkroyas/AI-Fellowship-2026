"""
System Prompts Module.

Contains carefully engineered system prompts for different use cases.
Demonstrates prompt engineering with temperature and top_p tuning.
"""


# ── Main Assistant System Prompt ──
ASSISTANT_SYSTEM_PROMPT = """You are an intelligent AI assistant with access to a knowledge base and external tools.

## Your Capabilities:
1. **Knowledge Base Search**: You can search through ingested documents to find relevant information.
2. **Calculator**: You can perform mathematical computations.
3. **Web Search**: You can search the internet for current information.
4. **Current Time**: You can get the current date and time.

## Guidelines:
- Always be helpful, accurate, and concise.
- When answering questions about documents, cite the source and relevance score.
- If you're uncertain about something, say so and suggest using web search.
- Use tools when they would provide better answers than your training data.
- Format responses clearly with markdown when appropriate.
- For mathematical questions, always use the calculator tool for accuracy.

## Response Format:
- Use clear, well-structured responses.
- Use bullet points and headers for complex topics.
- Include citations when referencing documents from the knowledge base.
"""

# ── RAG-Enhanced System Prompt ──
RAG_SYSTEM_PROMPT = """You are an AI assistant with access to a knowledge base.
Answer questions based on the provided context. If the context doesn't contain
relevant information, say so clearly.

## Context from Knowledge Base:
{context}

## Instructions:
- Base your answers primarily on the provided context.
- Cite sources when referencing specific information.
- If the context is insufficient, acknowledge this and provide your best general knowledge.
- Be precise and factual.
"""

# ── Structured Output System Prompt ──
STRUCTURED_OUTPUT_PROMPT = """You are an AI that produces structured JSON output.
Always respond with valid JSON matching the requested schema.
Never include explanatory text outside the JSON object.
Ensure all required fields are present and properly typed."""

# ── Prompt Engineering Parameters ──
PROMPT_CONFIGS = {
    "creative": {
        "temperature": 1.2,
        "top_p": 0.95,
        "description": "High creativity for brainstorming and creative tasks",
    },
    "balanced": {
        "temperature": 0.7,
        "top_p": 0.9,
        "description": "Balanced output for general conversation",
    },
    "precise": {
        "temperature": 0.2,
        "top_p": 0.5,
        "description": "Low temperature for factual and precise responses",
    },
    "deterministic": {
        "temperature": 0.0,
        "top_p": 1.0,
        "description": "Deterministic output for reproducible results",
    },
}

# ── Structured Output Schemas ──
ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "Brief summary of the analysis"},
        "key_points": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of key points",
        },
        "sentiment": {
            "type": "string",
            "enum": ["positive", "negative", "neutral", "mixed"],
            "description": "Overall sentiment",
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Confidence score",
        },
        "topics": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Identified topics",
        },
    },
    "required": ["summary", "key_points", "sentiment", "confidence"],
}

QA_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string", "description": "The answer to the question"},
        "sources": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Sources used for the answer",
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Confidence in the answer",
        },
    },
    "required": ["answer", "confidence"],
}
