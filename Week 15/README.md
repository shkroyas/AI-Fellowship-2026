# Week 15 AI Fellowship Assignment

This repository contains the complete implementation for the Week 15 AI Fellowship Assignment: Building and Productionizing an AI Assistant.

## Project Structure

- `task1-ai-assistant/`: Contains the core API, RAG pipeline, LLM integrations (Gemini, OpenAI, vLLM), and tool calling logic.
- `task2-production/`: Contains the productionized version with a Streamlit UI, middleware (rate limiting, retry, caching, fallback), and AWS deployment guides.
- `architecture/`: Contains architecture diagrams.

## Quick Start

The fastest way to run the entire system is using Docker Compose:

```bash
cd task2-production
# Create your .env file
cp ../task1-ai-assistant/.env.example .env
# Edit .env to add your GOOGLE_API_KEY and OPENAI_API_KEY
# Start the system
docker-compose up -d
```

Access the UI at `http://localhost:8501`.

## Detailed Documentation

Please refer to the detailed READMEs in each sub-directory:
- [Task 1 README](./task1-ai-assistant/README.md)
- [Task 2 README](./task2-production/README.md)
- [AWS Deployment Guide](./task2-production/deploy/aws/README.md)
- [ONNX Optimization Notes](./task2-production/backend/optimization/onnx_notes.md)
