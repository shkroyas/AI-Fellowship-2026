# AI Assistant Production Architecture (Week 15)

This repository contains the complete implementation for the Week 15 AI Fellowship Assignment. It is divided into two major tasks: **Task 1 (Core AI Assistant)** and **Task 2 (Production Hardening & Deployment)**.

## 🚀 Task 1: Core AI Assistant
Task 1 focuses on building the foundational FastAPI backend. 
- **LLM Integrations**: Dynamically supports Google Gemini, OpenAI GPT-4, and Local vLLM (`unsloth/gemma-2b-it`).
- **Retrieval-Augmented Generation (RAG)**: Built-in vector database (ChromaDB) using `all-MiniLM-L6-v2` embeddings for document ingestion, chunking, and contextual retrieval.
- **Tool Calling**: Agents have access to external tools like Web Search, Calculator, and Date/Time functions.
- **Dynamic Prompting**: Configurable generation parameters (`temperature`, `top_p`, `max_tokens`) with prompt styles (creative, balanced, precise).

## 🛡️ Task 2: Production Hardening
Task 2 wraps the Task 1 backend in a robust, production-ready environment.
- **Streamlit Frontend**: A professional, responsive UI that communicates seamlessly with the FastAPI backend over internal Docker networks.
- **Resilience Middleware**: 
  - Token Bucket Rate Limiting (429 errors for spam prevention).
  - Exponential Backoff Retries (resilience against LLM API timeouts).
  - LRU Caching (TTL-based response caching for identical queries).
- **Failover Chain**: Automatic Fallback Manager (`Primary vLLM → Secondary Gemini → Tertiary OpenAI`).
- **Container Orchestration**: Fully Dockerized using `docker-compose` to spin up the UI, Backend, and GPU-accelerated vLLM inference container simultaneously.

## ☁️ Deployment (AWS ECS Fargate)
The stack is configured to deploy to AWS Elastic Container Service (ECS) using Serverless Fargate.
- **Elastic Container Registry (ECR)**: Automated scripts to tag and push the `frontend` and `backend` images.
- **Application Load Balancer (ALB)**: Routes public internet traffic directly to the containerized frontend.
- **AWS Parameter Store**: Secures API Keys (`GOOGLE_API_KEY`, `OPENAI_API_KEY`) as encrypted secrets injected directly into the Fargate execution roles.

## 🏃 Quick Start Guide

### 1. Local Testing (Docker Compose)
Run the entire production stack (Frontend + Backend) locally:
```bash
cd task2-production
docker compose up --build -d
```
Access the application at: `http://localhost:8501`

### 2. Local GPU Testing (vLLM)
To harness your NVIDIA GPU for local inference, start the vLLM engine first:
```bash
docker run --gpus all \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    -p 8001:8001 \
    --ipc=host \
    vllm/vllm-openai:latest \
    --model unsloth/gemma-2b-it \
    --port 8001 \
    --max-model-len 1024 \
    --gpu-memory-utilization 0.92 \
    --enforce-eager \
    --max-num-seqs 16
```
*(Once running, start `docker compose` to connect the stack).*

### 3. AWS Deployment
To push the system to AWS ECR:
```bash
export AWS_ACCOUNT_ID="your-aws-account-id"
export AWS_REGION="us-east-1"
cd ../task2-production/deploy/aws
chmod +x deploy.sh
./deploy.sh
```
Follow the detailed guide in `task2-production/deploy/aws/README.md` to register the ECS tasks.
