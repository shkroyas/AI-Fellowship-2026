"""Configuration for Track B assistant."""
import os
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    llm_provider: str = Field(default="groq", description="Primary LLM provider")
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY", exclude=True, repr=False)
    groq_api_key_2: Optional[str] = Field(default=None, alias="GROQ_API_KEY_2", exclude=True, repr=False)
    groq_api_key_3: Optional[str] = Field(default=None, alias="GROQ_API_KEY_3", exclude=True, repr=False)
    groq_api_key_4: Optional[str] = Field(default=None, alias="GROQ_API_KEY_4", exclude=True, repr=False)
    groq_api_key_5: Optional[str] = Field(default=None, alias="GROQ_API_KEY_5", exclude=True, repr=False)
    groq_active_key: int = Field(default=1, ge=1, le=5, alias="GROQ_ACTIVE_KEY")
    groq_model: str = Field(default="openai/gpt-oss-20b", alias="GROQ_MODEL")
    groq_tokens_per_minute: int = Field(default=8000, ge=1000)
    openrouter_api_key: Optional[str] = Field(default=None, alias="OPENROUTER_API_KEY", exclude=True, repr=False)
    openrouter_model: str = Field(default="nvidia/nemotron-3-super-120b-a12b:free", alias="OPENROUTER_MODEL")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    max_tokens: int = Field(default=1024, ge=1, le=8192)
    agentic_max_iterations: int = Field(default=5, ge=1, le=5)
    agentic_compact_threshold: int = Field(default=6000, ge=1000, le=20000)

    def groq_keys(self):
        return [key.strip() for key in [self.groq_api_key, self.groq_api_key_2,
                self.groq_api_key_3, self.groq_api_key_4, self.groq_api_key_5]
                if key and key.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
