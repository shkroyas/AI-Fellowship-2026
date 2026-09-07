# AI Fellowship Week 15 - AI Assistant Project Documentation

This document provides a comprehensive overview of the Week 15 assignment, detailing the development, code versions, and transition from local development (with vLLM) to production deployment.

## 📌 Project Overview
The project is divided into two main tasks:
- **Task 1 (Core AI Assistant):** Focused on the local development of a robust backend featuring Retrieval-Augmented Generation (RAG), Tool Calling (Web Search, Calculator), and integration with various LLMs (notably local vLLM, Gemini, and OpenAI).
- **Task 2 (Production Hardening & Deployment):** Focused on preparing the system for production by implementing a Streamlit frontend, Docker container orchestration, resilience middleware (caching, retries, rate limiting, fallback chains), and scripts for AWS deployment.

---

## 🛠️ Task 1: Core AI Assistant (Pre-Deployment)

### 1. Local Development with vLLM
Before moving to deployment, the assistant was developed to run entirely locally using `vLLM` for accelerated LLM inference.
- **Model Used:** `unsloth/gemma-2b-it`
- **vLLM Engine Configuration:** The vLLM engine was configured to run on a local GPU, exposed via an OpenAI-compatible API endpoint on port `8001`.
- **FastAPI Backend:** The core backend (`app/main.py`) acts as the orchestrator. It handles incoming queries and dynamically routes them to the locally running vLLM model.

### 2. Retrieval-Augmented Generation (RAG)
- **Vector Database:** `ChromaDB` (local SQLite) is used to store document embeddings.
- **Embeddings:** `all-MiniLM-L6-v2` (SentenceTransformers) generates vector representations of ingested documents.
- **Document Pipeline:** The `app/rag` module handles reading markdown/text files, chunking them into semantic segments, and embedding them into the ChromaDB instance.
- **Context Injection:** When a user asks a question, the system retrieves the top relevant chunks and injects them into the system prompt for the local vLLM model to answer based on specific context.

### 3. Tool Calling
- The assistant is equipped with external capabilities managed by `app/tools/registry.py`.
- Includes a **Calculator** tool for arithmetic operations and a **Web Search** tool.
- The prompt engineering in `app/prompts/system_prompts.py` ensures the LLM knows when and how to request tool execution.

---

## 🚀 Task 2: Production Hardening (Deployment Version)

To prepare the application for real-world usage, significant architectural changes were introduced to harden the application and make it resilient and scalable.

### 1. What Changed for Deployment?
While Task 1 relied on running the Python scripts and vLLM directly on the host machine, Task 2 transitioned the architecture to a fully **containerized microservices approach**:

- **Streamlit Frontend Introduced:** A user-friendly web interface (`frontend/streamlit_app.py`) was created, completely decoupling the UI from the backend API.
- **Containerization (Docker Compose):** Both the FastAPI backend and Streamlit frontend were Dockerized using `Dockerfile.backend` and `Dockerfile.frontend`. They are orchestrated via `docker-compose.yml`, putting them on an internal Docker network so the UI can communicate securely with the backend.
- **Managed LLM Fallbacks:** Relying solely on a local vLLM instance in production can be risky due to GPU constraints or crashes. A **Fallback Manager** was introduced in `backend/middleware/fallback.py`:
  - **Primary:** Local vLLM (fastest, lowest cost if GPU available).
  - **Secondary:** Google Gemini (cloud fallback if vLLM fails).
  - **Tertiary:** OpenAI GPT-4 (ultimate fallback).

### 2. Resilience Middleware
To ensure the backend API can handle production traffic, several middleware components were added:
- **Rate Limiting:** Token Bucket algorithm implemented to prevent API spam and DDoS attempts, returning HTTP 429 when limits are exceeded.
- **LRU Caching:** Frequently asked identical queries are cached with a Time-To-Live (TTL) to save computation and LLM token costs.
- **Exponential Backoff:** If an external LLM provider times out, the system automatically retries with increasing delays before failing over.

### 3. AWS ECS Fargate Deployment
The system was packaged for deployment to AWS Elastic Container Service (ECS) using Fargate (serverless containers).
- **Deployment Scripts:** Shell scripts (`deploy/aws/deploy.sh`) automate tagging the Docker images and pushing them to AWS Elastic Container Registry (ECR).
- **Architecture:** The AWS architecture utilizes an Application Load Balancer (ALB) to route incoming internet traffic to the containerized frontend.
- **Secrets Management:** API keys are removed from local `.env` files and managed securely via AWS Parameter Store, injected as environment variables at runtime.

---

## 🏃 Setup & Execution Guide (For Evaluator)

### Running the Pre-Deployment Version (Task 1)
1. Navigate to the Task 1 directory: `cd "Week 15/task1-ai-assistant"`
2. Set up a virtual environment: `python -m venv venv && source venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Start the local vLLM server (requires NVIDIA GPU):
   ```bash
   docker run --gpus all -v ~/.cache/huggingface:/root/.cache/huggingface -p 8001:8001 --ipc=host vllm/vllm-openai:latest --model unsloth/gemma-2b-it
   ```
5. Run the FastAPI application: `uvicorn app.main:app --reload --port 8000`

### Running the Production Version (Task 2)
The production version simulates the deployment environment using Docker Compose.
1. Navigate to the Task 2 directory: `cd "Week 15/task2-production"`
2. Ensure Docker and Docker Compose are installed.
3. Build and start the cluster:
   ```bash
   docker-compose up --build
   ```
4. Access the Streamlit User Interface at `http://localhost:8501`.
5. Access the FastAPI Swagger Documentation at `http://localhost:8000/docs`.

### Notes for the Evaluator
- All environment variables (e.g., `GOOGLE_API_KEY`, `OPENAI_API_KEY`) must be populated in the `.env` files within each respective directory before running.
- The transition from Task 1 to Task 2 demonstrates a clear evolution from a raw engineering prototype to a hardened, scalable, cloud-ready architecture.

