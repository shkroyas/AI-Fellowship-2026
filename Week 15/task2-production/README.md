# Task 2: Productionized AI Assistant

This directory contains the production-ready implementation of the AI Assistant built in Task 1, specifically tailored to productionize the **NyayaSetu Gemma model** (Nepali Legal Assistant) that was fine-tuned in previous sessions.

## 🌟 Production Enhancements

The application has been upgraded with enterprise-grade features:

### Frontend UI
- **Beautiful Streamlit Interface**: Glassmorphism design, smooth animations, and responsive layout
- **Chat History**: Full conversation tracking with token usage metrics
- **Visual Indicators**: Badges for tool usage, RAG context, and source attribution
- **Configuration Panel**: Sidebar controls for provider selection, RAG, tools, and prompt style
- **Knowledge Base Management**: Direct UI for document uploading and text ingestion

### Backend Middleware
- **Rate Limiting**: Token bucket algorithm to prevent API abuse (60 req/min default)
- **Retry Mechanism**: Exponential backoff with jitter for handling transient failures
- **Fallback Provider**: Automatic failover chain (e.g., Gemini → OpenAI → vLLM)
- **Response Caching**: In-memory LRU cache with TTL to reduce latency and API costs
- **Batch Processing**: Async handling of concurrent requests for improved throughput
- **Graceful Degradation**: Clear error messages when all providers fail

## 🚀 Running with Docker Compose

The easiest way to run the full stack is with Docker Compose:

```bash
# Setup environment variables (copy from example and add your keys)
cp ../task1-ai-assistant/.env.example .env
# Edit .env with your API keys

# Build and start all services
docker-compose up --build -d

# View logs
docker-compose logs -f
```

The services will be available at:
- **Frontend UI**: http://localhost:8501
- **Backend API**: http://localhost:8000

## ☁️ AWS Deployment

See `deploy/aws/README.md` for comprehensive instructions on deploying this stack to AWS ECS Fargate.

## 🧠 Model Optimization Strategy

See `backend/optimization/onnx_notes.md` for a detailed analysis on why ONNX conversion is suitable for the embedding model but not the LLM, and how we optimized the LLM using vLLM and quantization instead.
