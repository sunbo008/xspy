"""Application configuration via Pydantic Settings.

Supports: config.yaml → .env → environment variables (highest priority).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Nested config sections
# ---------------------------------------------------------------------------


class TTSConfig(BaseModel):
    """TTS engine configuration."""

    preferred_engine: str = "index-tts"
    base_url: str = "http://192.168.1.100:7860"
    timeout_seconds: int = 60
    max_retries: int = 3
    concurrent_requests: int = 4


class LLMConfig(BaseModel):
    """LLM client configuration."""

    default_model: str = "qwen3.5-local"
    models_file: str = "config/llm_models.json"
    cache_dir: str = "data/cache/llm"
    allow_live: bool = True


class AudioConfig(BaseModel):
    """Audio processing configuration."""

    sample_rate: int = 24000
    bit_depth: int = 16
    channels: int = 1
    normalization_lufs: float = -16.0
    dialogue_silence_ms: int = 300
    narration_silence_ms: int = 500


class PipelineConfig(BaseModel):
    """Pipeline orchestrator configuration."""

    concurrency_limit: int = 4
    checkpoint_dir: str = "data/checkpoints"
    intermediate_dir: str = "data/intermediate"
    output_dir: str = "data/output"


class WebConfig(BaseModel):
    """Web UI configuration."""

    host: str = "0.0.0.0"
    port: int = 8080
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])


# ---------------------------------------------------------------------------
# Root settings
# ---------------------------------------------------------------------------


class XspySettings(BaseSettings):
    """Root application settings."""

    model_config = SettingsConfigDict(
        env_prefix="XSPY_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    env: str = "development"
    log_level: str = "INFO"
    data_dir: str = "data"

    tts: TTSConfig = Field(default_factory=TTSConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    web: WebConfig = Field(default_factory=WebConfig)


def load_settings(config_path: str = "config/config.yaml") -> XspySettings:
    """Load settings from YAML file, then apply env var overrides."""
    yaml_data: dict[str, Any] = {}
    path = Path(config_path)
    if path.exists():
        yaml_data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    return XspySettings(**yaml_data)


def load_llm_models(settings: XspySettings) -> dict[str, Any]:
    """Load the multi-model LLM configuration JSON.

    Resolves ${ENV_VAR} references in api_key fields.
    """
    models_path = Path(settings.llm.models_file)
    if not models_path.exists():
        return {"models": [], "task_routing": {}}

    data = json.loads(models_path.read_text(encoding="utf-8"))

    for model in data.get("models", []):
        api_key = model.get("api_key", "")
        if api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]
            resolved = os.getenv(env_var, "")
            if not resolved:
                import structlog

                logger = structlog.get_logger()
                logger.warning("llm.api_key.env_missing", env_var=env_var, model_id=model["id"])
            model["api_key"] = resolved

    return data
