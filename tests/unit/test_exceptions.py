"""Unit tests for core/exceptions.py — hierarchy and attributes."""

from __future__ import annotations

from xspy.core.exceptions import (
    AgentError,
    AudioError,
    ConfigError,
    EmotionError,
    LLMCacheMissError,
    LLMConnectionError,
    LLMError,
    LLMResponseError,
    ParserError,
    PipelineError,
    TTSConnectionError,
    TTSError,
    TTSTimeoutError,
    VoiceError,
    XspyError,
)


class TestExceptionHierarchy:
    def test_all_inherit_from_xspy_error(self):
        for exc_cls in [
            ConfigError,
            ParserError,
            LLMError,
            LLMConnectionError,
            LLMResponseError,
            LLMCacheMissError,
            AgentError,
            EmotionError,
            VoiceError,
            TTSError,
            TTSConnectionError,
            TTSTimeoutError,
            AudioError,
            PipelineError,
        ]:
            assert issubclass(exc_cls, XspyError)

    def test_llm_subtypes(self):
        assert issubclass(LLMConnectionError, LLMError)
        assert issubclass(LLMResponseError, LLMError)
        assert issubclass(LLMCacheMissError, LLMError)

    def test_tts_subtypes(self):
        assert issubclass(TTSConnectionError, TTSError)
        assert issubclass(TTSTimeoutError, TTSError)

    def test_context_attribute(self):
        err = XspyError("test", module="parser", context={"file": "a.txt"})
        assert err.module == "parser"
        assert err.context == {"file": "a.txt"}
        assert str(err) == "test"

    def test_default_context(self):
        err = XspyError("simple error")
        assert err.module == ""
        assert err.context == {}
