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
    # Primary provider: groq, openai, or openrouter
    llm_provider: str = Field(default="groq", description="Primary LLM provider")

    # Groq (primary)
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY", exclude=True, repr=False)
    groq_api_key_2: Optional[str] = Field(default=None, alias="GROQ_API_KEY_2", exclude=True, repr=False)
    groq_api_key_3: Optional[str] = Field(default=None, alias="GROQ_API_KEY_3", exclude=True, repr=False)
    groq_api_key_4: Optional[str] = Field(default=None, alias="GROQ_API_KEY_4", exclude=True, repr=False)
    groq_api_key_5: Optional[str] = Field(default=None, alias="GROQ_API_KEY_5", exclude=True, repr=False)
    groq_active_key: int = Field(default=1, ge=1, le=5, alias="GROQ_ACTIVE_KEY")
    groq_model: str = Field(default="openai/gpt-oss-20b", alias="GROQ_MODEL")

    groq_tokens_per_minute: int = Field(default=6000, ge=1000)

    def groq_keys(self):
        return [key.strip() for key in [self.groq_api_key, self.groq_api_key_2,
                self.groq_api_key_3, self.groq_api_key_4, self.groq_api_key_5]
                if key and key.strip()]

    # OpenRouter (fallback)
    openrouter_api_key: Optional[str] = Field(default=None, alias="OPENROUTER_API_KEY", exclude=True, repr=False)
    openrouter_model: str = Field(default="nvidia/nemotron-3-super-120b-a12b:free", alias="OPENROUTER_MODEL")

    # OpenAI (optional secondary fallback)
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY", exclude=True, repr=False)
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    # ── Generation Parameters ──
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    max_tokens: int = Field(default=1024, ge=1, le=8192)

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

    # ── Agentic Loop Configuration ──
    agentic_max_iterations: int = Field(
        default=5, ge=1, le=5, description="Max iterations for agentic loop"
    )
    agentic_compact_threshold: int = Field(
        default=6000, ge=1000, le=20000,
        description="Character threshold for context compaction",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Singleton settings instance
settings = Settings()
