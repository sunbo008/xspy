"""ModelRouter: routes tasks to the best available LLM model."""

from __future__ import annotations

import structlog

from xspy.core.exceptions import LLMConnectionError, LLMError
from xspy.core.llm.client import ModelConfig, OpenAICompatibleClient

logger = structlog.get_logger()


class ModelRouter:
    """Routes LLM requests to models based on task type and priority."""

    def __init__(
        self,
        models: list[ModelConfig],
        task_routing: dict[str, str],
    ) -> None:
        self._models: dict[str, ModelConfig] = {m.id: m for m in models}
        self._clients: dict[str, OpenAICompatibleClient] = {}
        self._task_routing = task_routing

    def _get_client(self, model_id: str) -> OpenAICompatibleClient:
        if model_id not in self._clients:
            config = self._models.get(model_id)
            if not config:
                raise LLMError(
                    f"Model '{model_id}' not found in configuration",
                    module="llm.router",
                )
            self._clients[model_id] = OpenAICompatibleClient(config)
        return self._clients[model_id]

    def get_model_for_task(self, task_type: str) -> str:
        """Return the model_id assigned to a given task type."""
        model_id = self._task_routing.get(task_type)
        if model_id and model_id in self._models:
            return model_id
        return self._fallback_model(task_type)

    def _fallback_model(self, task_type: str) -> str:
        """Find the highest-priority model that supports this task."""
        candidates = [
            m for m in self._models.values() if task_type in m.capabilities or not m.capabilities
        ]
        if not candidates:
            candidates = list(self._models.values())
        candidates.sort(key=lambda m: m.priority)
        if not candidates:
            raise LLMError(
                f"No model available for task '{task_type}'",
                module="llm.router",
            )
        return candidates[0].id

    def chat(
        self,
        task_type: str,
        messages: list[dict[str, str]],
        **kwargs: object,
    ) -> str:
        """Route a chat request to the best model for the given task.

        Implements fallback: if the primary model fails, tries the next
        by priority.
        """
        primary_id = self.get_model_for_task(task_type)
        fallback_ids = self._get_fallback_chain(task_type, primary_id)

        for model_id in [primary_id, *fallback_ids]:
            try:
                client = self._get_client(model_id)
                return client.chat(messages, **kwargs)  # type: ignore[arg-type]
            except LLMConnectionError:
                logger.warning("llm.router.fallback", failed=model_id, task=task_type)
                continue

        raise LLMConnectionError(
            f"All models failed for task '{task_type}'",
            module="llm.router",
            context={"attempted": [primary_id, *fallback_ids]},
        )

    def _get_fallback_chain(self, task_type: str, exclude: str) -> list[str]:
        """Get ordered fallback model IDs (by priority) excluding the primary."""
        candidates = [
            m
            for m in self._models.values()
            if m.id != exclude and (task_type in m.capabilities or not m.capabilities)
        ]
        candidates.sort(key=lambda m: m.priority)
        return [m.id for m in candidates]
