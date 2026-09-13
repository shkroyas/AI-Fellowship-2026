"""
Lightweight Local LLM Provider.

Runs a HuggingFace model directly using transformers — no vLLM server needed.
Designed for small models like gemma-2b-it on consumer GPUs (6GB VRAM).
"""

import json
import logging
import uuid
from typing import Any, Optional

from .provider import (
    ChatMessage,
    LLMProvider,
    LLMResponse,
    StructuredOutputSchema,
    ToolCall,
    ToolDefinition,
)

logger = logging.getLogger(__name__)


class LocalTransformersProvider(LLMProvider):
    """
    Local provider using transformers directly.

    No server required — loads the model into GPU and runs inference.
    """

    def __init__(
        self,
        model: str = "unsloth/gemma-2b-it",
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 1024,
    ):
        super().__init__(model, temperature, top_p, max_tokens)
        self._pipeline = None

    def _get_pipeline(self):
        """Lazy-load the model pipeline."""
        if self._pipeline is None:
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

            logger.info(f"Loading model: {self.model}")
            tokenizer = AutoTokenizer.from_pretrained(self.model)
            model = AutoModelForCausalLM.from_pretrained(
                self.model,
                torch_dtype=torch.bfloat16,
                device_map="auto",
            )
            self._pipeline = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                max_new_tokens=self.max_tokens,
                do_sample=True,
                temperature=self.temperature,
                top_p=self.top_p,
            )
            logger.info(f"Model loaded: {self.model}")
        return self._pipeline

    def _build_prompt(self, messages: list[ChatMessage]) -> str:
        """Convert messages to a single prompt string."""
        parts = []
        for msg in messages:
            if msg.role == "system":
                parts.append(f"<bos><start_of_turn>user\n{msg.content}<end_of_turn>\n")
            elif msg.role == "user":
                parts.append(f"<start_of_turn>user\n{msg.content}<end_of_turn>\n")
            elif msg.role == "assistant":
                parts.append(f"<start_of_turn>model\n{msg.content}<end_of_turn>\n")
        parts.append("<start_of_turn>model\n")
        return "".join(parts)

    async def chat(
        self,
        messages: list[ChatMessage],
        tools: Optional[list[ToolDefinition]] = None,
        structured_output: Optional[StructuredOutputSchema] = None,
    ) -> LLMResponse:
        """Generate a response using the local model."""
        try:
            pipe = self._get_pipeline()
            prompt = self._build_prompt(messages)

            output = pipe(prompt, return_full_text=False)
            content = output[0]["generated_text"].strip()

            # Clean up common artifacts
            if content.endswith("<end_of_turn>"):
                content = content[:-len("<end_of_turn>")].strip()

            return LLMResponse(
                content=content,
                tool_calls=[],  # Text-based decisions, not tool calling
                model=self.model,
                usage={
                    "prompt_tokens": len(pipe.tokenizer.encode(prompt, add_special_tokens=False)),
                    "completion_tokens": len(pipe.tokenizer.encode(content, add_special_tokens=False)),
                },
            )
        except Exception as e:
            logger.error(f"Local model error: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if the model can be loaded."""
        try:
            pipe = self._get_pipeline()
            output = pipe("Say ok", max_new_tokens=5, do_sample=False)
            return bool(output)
        except Exception as e:
            logger.error(f"Local model health check failed: {e}")
            return False
