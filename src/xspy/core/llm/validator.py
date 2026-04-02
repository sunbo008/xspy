"""JSON Schema validation for LLM outputs."""

from __future__ import annotations

import json
from typing import Any

import structlog

from xspy.core.exceptions import LLMResponseError

logger = structlog.get_logger()


def validate_json_output(
    raw_text: str,
    *,
    required_fields: list[str] | None = None,
    expected_type: type | None = None,
) -> dict[str, Any] | list[Any]:
    """Parse and validate LLM JSON output.

    Handles common LLM quirks: markdown code fences, trailing commas, etc.

    Args:
        raw_text: Raw text from LLM response
        required_fields: Field names that must be present (for dict outputs)
        expected_type: Expected top-level type (dict or list)

    Returns:
        Parsed JSON data

    Raises:
        LLMResponseError: If parsing or validation fails
    """
    cleaned = _strip_code_fences(raw_text)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("llm.validation.json_parse_failed", error=str(e), raw_length=len(raw_text))
        raise LLMResponseError(
            f"LLM output is not valid JSON: {e}",
            module="llm.validator",
            context={"raw_preview": raw_text[:200]},
        ) from e

    if expected_type and not isinstance(data, expected_type):
        raise LLMResponseError(
            f"Expected {expected_type.__name__}, got {type(data).__name__}",
            module="llm.validator",
        )

    if required_fields and isinstance(data, dict):
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise LLMResponseError(
                f"Missing required fields: {missing}",
                module="llm.validator",
                context={"available_fields": list(data.keys())},
            )

    return data


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences wrapping JSON."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()
