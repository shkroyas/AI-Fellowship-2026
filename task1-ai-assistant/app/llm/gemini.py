"""
Google Gemini LLM Provider.

Implements the LLMProvider interface for Google's Gemini API
with support for function calling and structured output.
"""

import json
import logging
import uuid
from typing import Any, Optional

import google.generativeai as genai

from .provider import (
    ChatMessage,
    LLMProvider,
    LLMResponse,
    StructuredOutputSchema,
    ToolCall,
    ToolDefinition,
)

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Google Gemini API provider."""

    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 2048,
    ):
        super().__init__(model, temperature, top_p, max_tokens)
        if not api_key:
            raise ValueError("Google API key is required for Gemini provider")

        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(model)

    def _convert_tools_to_gemini(self, tools: list[ToolDefinition]) -> list[dict]:
        """Convert our tool definitions to Gemini's function declaration format."""
        function_declarations = []
        for tool in tools:
            func_decl = {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            function_declarations.append(func_decl)
        return function_declarations

    def _build_gemini_messages(self, messages: list[ChatMessage]) -> tuple[Optional[str], list[dict]]:
        """Convert ChatMessage list to Gemini format (system instruction + history)."""
        system_instruction = None
        history = []

        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content
            elif msg.role == "user":
                history.append({"role": "user", "parts": [msg.content]})
            elif msg.role == "assistant":
                history.append({"role": "model", "parts": [msg.content]})
            elif msg.role == "tool":
                history.append({
                    "role": "function",
                    "parts": [{"function_response": {
                        "name": msg.tool_call_id or "tool",
                        "response": {"result": msg.content}
                    }}]
                })

        return system_instruction, history

    async def chat(
        self,
        messages: list[ChatMessage],
        tools: Optional[list[ToolDefinition]] = None,
        structured_output: Optional[StructuredOutputSchema] = None,
    ) -> LLMResponse:
        """Send a chat request to Gemini."""
        try:
            system_instruction, history = self._build_gemini_messages(messages)

            generation_config = genai.GenerationConfig(
                temperature=self.temperature,
                top_p=self.top_p,
                max_output_tokens=self.max_tokens,
            )

            # For structured output, request JSON
            if structured_output:
                generation_config.response_mime_type = "application/json"

            # Create model with system instruction if provided
            model = genai.GenerativeModel(
                self.model,
                system_instruction=system_instruction,
                generation_config=generation_config,
            )

            # Set up tools if provided
            gemini_tools = None
            if tools:
                gemini_tools = [
                    genai.protos.Tool(
                        function_declarations=[
                            genai.protos.FunctionDeclaration(
                                name=t.name,
                                description=t.description,
                                parameters=genai.protos.Schema(
                                    type=genai.protos.Type.OBJECT,
                                    properties={
                                        k: genai.protos.Schema(
                                            type=genai.protos.Type.STRING,
                                            description=v.get("description", ""),
                                        )
                                        for k, v in t.parameters.get("properties", {}).items()
                                    },
                                    required=t.parameters.get("required", []),
                                ),
                            )
                            for t in tools
                        ]
                    )
                ]

            chat_session = model.start_chat(history=history[:-1] if history else [])

            # Get the last user message
            last_msg = history[-1]["parts"][0] if history else ""
            response = chat_session.send_message(
                last_msg,
                tools=gemini_tools,
            )

            # Parse response
            tool_calls = []
            content = ""

            for part in response.parts:
                if hasattr(part, "function_call") and part.function_call.name:
                    fc = part.function_call
                    tool_calls.append(ToolCall(
                        id=str(uuid.uuid4()),
                        name=fc.name,
                        arguments=dict(fc.args) if fc.args else {},
                    ))
                elif hasattr(part, "text"):
                    content += part.text

            # Validate structured output if requested
            if structured_output and content:
                self._validate_json_output(content)

            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                model=self.model,
                usage={
                    "prompt_tokens": response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0,
                    "completion_tokens": response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0,
                },
            )

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if Gemini API is accessible."""
        try:
            model = genai.GenerativeModel(self.model)
            response = model.generate_content("Say 'ok'")
            return bool(response.text)
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            return False
