from __future__ import annotations

import os
from urllib.parse import quote_plus

from dotenv import load_dotenv


load_dotenv()


class Config:
    """Centralized environment configuration."""

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "classicmodels")
    DB_USER = os.getenv("DB_USER", "myuser")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "mypassword")
    DATABASE_URL = os.getenv("DATABASE_URL", "").strip() or None
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip() or None
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip() or None
    GEMINI_API_KEYS = os.getenv("GEMINI_API_KEYS", "").strip() or None
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").strip().lower() or None
    MAX_QUERY_ROWS = int(os.getenv("MAX_QUERY_ROWS", "500"))

    @classmethod
    def build_database_url(cls) -> str:
        if cls.DATABASE_URL:
            url = cls.DATABASE_URL
            if cls.DB_HOST not in {"localhost", "127.0.0.1", "::1"}:
                for host_alias in ("localhost", "127.0.0.1", "[::1]", "::1"):
                    url = url.replace(f"@{host_alias}", f"@{cls.DB_HOST}")
            return url

        password = quote_plus(cls.DB_PASSWORD)
        host = quote_plus(cls.DB_HOST)
        return f"postgresql+psycopg://{cls.DB_USER}:{password}@{host}:{cls.DB_PORT}/{cls.DB_NAME}"

    @classmethod
    def get_gemini_api_keys(cls) -> list[str]:
        raw_value = cls.GEMINI_API_KEYS or cls.GEMINI_API_KEY or os.getenv("API_KEY", "").strip()
        if not raw_value:
            return []

        if raw_value.startswith("[") and raw_value.endswith("]"):
            raw_value = raw_value[1:-1].strip()

        values = [value.strip().strip("'").strip('"') for value in raw_value.split(",") if value.strip()]
        return values or [raw_value.strip().strip("'").strip('"')]

    @classmethod
    def get_openai_api_key(cls) -> str | None:
        return cls.OPENAI_API_KEY

    @classmethod
    def preferred_llm_provider(cls) -> str | None:
        if cls.LLM_PROVIDER in {"deterministic", "none", "off", "fallback"}:
            return None
        if cls.LLM_PROVIDER in {"openai", "gemini"}:
            return cls.LLM_PROVIDER
        if cls.get_openai_api_key():
            return "openai"
        if cls.get_gemini_api_keys():
            return "gemini"
        return None

    @classmethod
    def has_llm_credentials(cls) -> bool:
        return cls.preferred_llm_provider() is not None
