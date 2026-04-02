"""OpenAI SDK compatible LLM client."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog
from openai import OpenAI

from xspy.core.exceptions import LLMConnectionError, LLMResponseError

logger = structlog.get_logger()


@dataclass
class ModelConfig:
    """Configuration for a single LLM model."""

    id: str
    name: str
    base_url: str
    api_key: str = "not-needed"
    model: str = ""
    max_tokens: int = 8192
    temperature: float = 0.3
    capabilities: list[str] = field(default_factory=list)
    priority: int = 1


class OpenAICompatibleClient:
    """Generic LLM client that works with any OpenAI-compatible API."""

    def __init__(self, config: ModelConfig) -> None:
        self._config = config
        self._client = OpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=120.0,
        )

    @property
    def model_id(self) -> str:
        return self._config.id

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        """Send a chat completion request."""
        resolved_model = model or self._config.model
        resolved_temp = temperature if temperature is not None else self._config.temperature
        resolved_max = max_tokens if max_tokens is not None else self._config.max_tokens

        log = logger.bind(model_id=self._config.id, model=resolved_model)
        log.debug("llm.request", message_count=len(messages))

        try:
            kwargs: dict[str, Any] = {
                "model": resolved_model,
                "messages": messages,
                "temperature": resolved_temp,
                "max_tokens": resolved_max,
            }
            if response_format:
                kwargs["response_format"] = response_format

            response = self._client.chat.completions.create(**kwargs)
        except Exception as e:
            log.error("llm.connection_failed", error=str(e))
            raise LLMConnectionError(
                f"Failed to connect to LLM '{self._config.id}': {e}",
                module="llm",
                context={"base_url": self._config.base_url},
            ) from e

        choice = response.choices[0] if response.choices else None
        if not choice or not choice.message.content:
            log.error("llm.empty_response")
            raise LLMResponseError(
                f"LLM '{self._config.id}' returned empty response",
                module="llm",
            )

        content = choice.message.content
        log.debug(
            "llm.response",
            content_length=len(content),
            usage_tokens=response.usage.total_tokens if response.usage else 0,
        )
        return content
