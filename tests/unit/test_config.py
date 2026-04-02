"""Unit tests for core/config.py — default loading, env override, validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from xspy.core.config import XspySettings, load_llm_models, load_settings

if TYPE_CHECKING:
    import pytest


class TestXspySettings:
    def test_defaults(self):
        s = XspySettings()
        assert s.env == "development"
        assert s.log_level == "INFO"
        assert s.tts.preferred_engine == "index-tts"
        assert s.llm.default_model == "qwen3.5-local"
        assert s.audio.sample_rate == 24000
        assert s.pipeline.concurrency_limit == 4
        assert s.web.port == 8080

    def test_nested_config(self):
        s = XspySettings()
        assert s.tts.timeout_seconds == 60
        assert s.audio.normalization_lufs == -16.0

    def test_env_var_override(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("XSPY_ENV", "production")
        monkeypatch.setenv("XSPY_LOG_LEVEL", "DEBUG")
        s = XspySettings()
        assert s.env == "production"
        assert s.log_level == "DEBUG"

    def test_nested_env_override(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("XSPY_TTS__TIMEOUT_SECONDS", "120")
        s = XspySettings()
        assert s.tts.timeout_seconds == 120


class TestLoadSettings:
    def test_load_from_nonexistent_yaml(self, tmp_path: Path):
        s = load_settings(config_path=str(tmp_path / "nonexistent.yaml"))
        assert s.env == "development"

    def test_load_from_yaml(self, tmp_path: Path):
        yaml_path = tmp_path / "config.yaml"
        yaml_path.write_text("env: production\nlog_level: WARNING\n", encoding="utf-8")
        s = load_settings(config_path=str(yaml_path))
        assert s.env == "production"
        assert s.log_level == "WARNING"


class TestLoadLLMModels:
    def test_load_default_models(self):
        s = XspySettings()
        if Path(s.llm.models_file).exists():
            data = load_llm_models(s)
            assert "models" in data
            assert "task_routing" in data

    def test_missing_file(self, tmp_path: Path):
        s = XspySettings(llm={"models_file": str(tmp_path / "nope.json")})
        data = load_llm_models(s)
        assert data == {"models": [], "task_routing": {}}

    def test_env_var_resolution(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("MY_API_KEY", "sk-test-12345")
        models_file = tmp_path / "models.json"
        models_file.write_text(
            json.dumps(
                {
                    "models": [
                        {
                            "id": "test-model",
                            "api_key": "${MY_API_KEY}",
                            "base_url": "http://localhost:8000/v1",
                        }
                    ],
                    "task_routing": {},
                }
            ),
            encoding="utf-8",
        )
        s = XspySettings(llm={"models_file": str(models_file)})
        data = load_llm_models(s)
        assert data["models"][0]["api_key"] == "sk-test-12345"

    def test_env_var_missing_warns(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("MISSING_KEY", raising=False)
        models_file = tmp_path / "models.json"
        models_file.write_text(
            json.dumps(
                {
                    "models": [
                        {
                            "id": "test-model",
                            "api_key": "${MISSING_KEY}",
                            "base_url": "http://localhost:8000/v1",
                        }
                    ],
                    "task_routing": {},
                }
            ),
            encoding="utf-8",
        )
        s = XspySettings(llm={"models_file": str(models_file)})
        data = load_llm_models(s)
        assert data["models"][0]["api_key"] == ""
