"""LLM client protocol — all implementations must conform to this interface."""

from __future__ import annotations

from typing import Any, Protocol


class LLMClientProtocol(Protocol):
    """Protocol for OpenAI-compatible LLM clients."""

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        """Send a chat completion request and return the assistant message content."""
        ...

    @property
    def model_id(self) -> str:
        """Return the model identifier for this client."""
        ...
