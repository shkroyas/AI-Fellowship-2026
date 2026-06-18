from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional

from config import Config

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - optional dependency
    genai = None

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None


@dataclass
class GeminiKeyRotator:
    keys: list[str]
    current_index: int = 0

    def has_keys(self) -> bool:
        return bool(self.keys)

    def get_current_key(self) -> str:
        if not self.keys:
            raise ValueError("No Gemini API keys configured.")
        return self.keys[self.current_index]

    def rotate(self) -> str:
        if not self.keys:
            raise ValueError("No Gemini API keys configured.")
        self.current_index = (self.current_index + 1) % len(self.keys)
        return self.get_current_key()


_rotator: Optional[GeminiKeyRotator] = None


def _get_rotator() -> GeminiKeyRotator:
    global _rotator
    if _rotator is None:
        _rotator = GeminiKeyRotator(Config.get_gemini_api_keys())
    return _rotator


def _call_gemini(prompt: str, temperature: float = 0.1) -> str:
    rotator = _get_rotator()
    if not rotator.has_keys() or genai is None:
        raise RuntimeError("Gemini is not configured in this environment.")

    max_attempts = max(len(rotator.keys) * 2, 3)
    for attempt in range(max_attempts):
        try:
            genai.configure(api_key=rotator.get_current_key())
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(temperature=temperature),
            )
            return (response.text or "").strip()
        except Exception as exc:
            error_text = str(exc).lower()
            if "429" in error_text or "quota" in error_text or "resource exhausted" in error_text:
                if len(rotator.keys) > 1:
                    rotator.rotate()
                    continue
                time.sleep(min(5 * (attempt + 1), 20))
                continue
            raise

    raise RuntimeError("Gemini LLM call failed after retries.")


def _call_openai(prompt: str, temperature: float = 0.1) -> str:
    if OpenAI is None:
        raise RuntimeError("OpenAI SDK is not installed.")

    api_key = Config.get_openai_api_key()
    if not api_key:
        raise RuntimeError("OpenAI API key is not configured.")

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        input=prompt,
        temperature=temperature,
    )
    return (response.output_text or "").strip()


def call_llm_with_rotation(prompt: str, temperature: float = 0.1, response_schema=None) -> str:
    provider = Config.preferred_llm_provider()
    if provider == "openai":
        return _call_openai(prompt, temperature=temperature)
    if provider == "gemini":
        return _call_gemini(prompt, temperature=temperature)
    raise RuntimeError("No LLM credentials configured. Use the deterministic fallback agents instead.")
