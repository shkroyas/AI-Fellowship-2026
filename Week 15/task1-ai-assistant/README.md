# Task 1: AI Assistant (Applied AI)

A robust AI assistant utilizing modern LLM APIs and RAG (Retrieval-Augmented Generation) architectures.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                          │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  /chat    │  │ /chat/struct │  │  /documents/ingest       │  │
│  │  /tools   │  │ /config      │  │  /documents/upload       │  │
│  └────┬─────┘  └──────┬───────┘  └────────────┬─────────────┘  │
│       │               │                        │                │
│  ┌────▼───────────────▼────────────────────────▼─────────────┐  │
│  │                  Request Router                            │  │
│  └────┬──────────────┬────────────────────────┬──────────────┘  │
│       │              │                        │                 │
│  ┌────▼────┐   ┌─────▼──────┐          ┌──────▼──────────┐     │
│  │   LLM   │   │    RAG     │          │  Tool Registry  │     │
│  │Provider │   │  Pipeline  │          │  ┌───────────┐  │     │
│  │ Layer   │   │            │          │  │Calculator │  │     │
│  │         │   │ ┌────────┐ │          │  │Web Search │  │     │
│  │┌───────┐│   │ │Ingester│ │          │  │DateTime   │  │     │
│  ││Gemini ││   │ │Chunker │ │          │  └───────────┘  │     │
│  ││OpenAI ││   │ │Embedder│ │          └─────────────────┘     │
│  ││vLLM   ││   │ └───┬────┘ │                                  │
│  │└───────┘│   │     │      │                                  │
│  └─────────┘   │ ┌───▼────┐ │                                  │
│                │ │ChromaDB│ │                                  │
│                │ │(Vector)│ │                                  │
│                │ └────────┘ │                                  │
│                └────────────┘                                  │
└─────────────────────────────────────────────────────────────────┘
```

## ✨ Features

### Core Functionality
- **LLM Integration**: Supports Google Gemini, OpenAI, and local vLLM (Mistral/Llama)
- **Prompt Engineering**: Configurable temperature, top_p, and multiple prompt styles
- **Structured Output**: JSON schema-validated responses using Pydantic
- **Tool Calling**: Calculator, web search, and datetime tools with extensible registry

### RAG Pipeline
- **Document Ingestion**: Supports TXT, MD, PDF, JSON, CSV files
- **Smart Chunking**: Recursive, sentence-based, and fixed-size strategies
- **Vector Storage**: ChromaDB with sentence-transformers embeddings
- **Context Building**: Relevance-scored retrieval with source attribution

### Local Deployment
- **vLLM Integration**: Serve Mistral-7B or Llama 3 locally
- **Docker Support**: Full containerization with health checks

## 🚀 Quick Start

### 1. Setup Environment
```bash
# Clone and navigate
cd task1-ai-assistant

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your API keys
```

### 2. Run the Server
```bash
# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# API docs available at http://localhost:8000/docs
```

### 3. Test the API
```bash
# Chat endpoint
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is RAG?", "use_rag": true}'

# Structured output
curl -X POST http://localhost:8000/chat/structured \
  -H "Content-Type: application/json" \
  -d '{"message": "Analyze the benefits of AI", "output_type": "analysis"}'

# Ingest document
curl -X POST http://localhost:8000/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{"text": "Your document content here", "source": "my_doc"}'
```

### 4. Run with Docker
```bash
docker build -t ai-assistant .
docker run -p 8000:8000 --env-file .env ai-assistant
```

### 5. Local Model with vLLM
```bash
# Install vLLM
pip install vllm

# Serve Mistral locally
vllm serve mistralai/Mistral-7B-Instruct-v0.3 --port 8001

# Update .env
LLM_PROVIDER=local_vllm
VLLM_BASE_URL=http://localhost:8001/v1
```

## 📁 Project Structure

```
task1-ai-assistant/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py             # Configuration management
│   ├── llm/
│   │   ├── provider.py       # Base LLM interface
│   │   ├── gemini.py         # Google Gemini provider
│   │   ├── openai_client.py  # OpenAI provider
│   │   └── local_vllm.py     # vLLM local provider
│   ├── rag/
│   │   ├── ingestion.py      # Document loading
│   │   ├── chunking.py       # Text chunking
│   │   ├── embeddings.py     # Vectorization + ChromaDB
│   │   └── retriever.py      # RAG orchestrator
│   ├── tools/
│   │   ├── registry.py       # Tool management
│   │   ├── calculator.py     # Math tool
│   │   └── web_search.py     # Web search tool
│   └── prompts/
│       └── system_prompts.py # Prompt engineering
├── data/
│   └── sample_docs/          # Sample documents for RAG
├── Dockerfile
├── requirements.txt
└── README.md
```

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with provider status |
| `/chat` | POST | Main chat with RAG + tools |
| `/chat/structured` | POST | Structured JSON output |
| `/documents/ingest` | POST | Ingest text into knowledge base |
| `/documents/upload` | POST | Upload file to knowledge base |
| `/documents/stats` | GET | RAG pipeline statistics |
| `/tools` | GET | List available tools |
| `/config` | GET | Current configuration |

## ⚙️ Prompt Engineering

Four pre-configured prompt styles:

| Style | Temperature | Top-P | Use Case |
|-------|------------|-------|----------|
| `creative` | 1.2 | 0.95 | Brainstorming, creative writing |
| `balanced` | 0.7 | 0.9 | General conversation |
| `precise` | 0.2 | 0.5 | Factual responses |
| `deterministic` | 0.0 | 1.0 | Reproducible results |
