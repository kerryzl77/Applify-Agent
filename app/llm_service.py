"""Shared OpenAI client and model helpers."""

from __future__ import annotations

from typing import Any, Optional, Type

from openai import OpenAI
from pydantic import BaseModel

from app.config import get_settings


class LLMService:
    """Centralized OpenAI access with a shared default model."""

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        settings = get_settings()
        self.model = model or settings.openai_default_model
        self.client = OpenAI(api_key=api_key or settings.openai_api_key)

    def generate_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_completion_tokens: int = 300,
        temperature: float = 0.6,
        response_format: Optional[dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> str:
        response = self.client.chat.completions.create(
            model=model or self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_completion_tokens=max_completion_tokens,
            temperature=temperature,
            response_format=response_format,
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("LLM returned empty content")
        return content.strip()

    def parse_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: Type[BaseModel],
        model: Optional[str] = None,
    ) -> BaseModel:
        response = self.client.responses.parse(
            model=model or self.model,
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_prompt}],
                },
            ],
            text_format=schema,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise ValueError("LLM returned no parsed output")
        return parsed


def get_default_model() -> str:
    return get_settings().openai_default_model
