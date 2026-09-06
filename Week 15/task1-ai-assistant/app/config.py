"""
Configuration module for the AI Assistant.
Manages environment variables, API keys, and application settings.
"""

import os
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── LLM Provider Configuration ──
    # Primary provider: gemini, openai, or local_vllm
    llm_provider: str = Field(default="gemini", description="Primary LLM provider")

    # Google Gemini
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-2.0-flash", alias="GEMINI_MODEL")

    # OpenAI
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    # Local vLLM
    vllm_base_url: str = Field(
        default="http://localhost:8000/v1", alias="VLLM_BASE_URL"
    )
    vllm_model: str = Field(
        default="mistralai/Mistral-7B-Instruct-v0.3", alias="VLLM_MODEL"
    )

    # ── Generation Parameters ──
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    max_tokens: int = Field(default=2048, ge=1, le=8192)

    # ── RAG Configuration ──
    chroma_persist_dir: str = Field(default="./data/chroma_db")
    chunk_size: int = Field(default=500, ge=100, le=2000)
    chunk_overlap: int = Field(default=50, ge=0, le=500)
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2", alias="EMBEDDING_MODEL"
    )
    retrieval_top_k: int = Field(default=5, ge=1, le=20)

    # ── Server Configuration ──
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    debug: bool = Field(default=False)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Singleton settings instance
settings = Settings()
