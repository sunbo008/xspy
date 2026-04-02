"""Unified exception hierarchy for the xspy project.

Structure:
    XspyError
    ├── ConfigError          — configuration loading / validation
    ├── ParserError          — novel file parsing
    ├── LLMError             — LLM client, routing, validation
    │   ├── LLMConnectionError
    │   ├── LLMResponseError
    │   └── LLMCacheMissError
    ├── AgentError           — screenwriter / character engine
    ├── EmotionError         — emotion inference
    ├── VoiceError           — voice bank
    ├── TTSError             — TTS synthesis
    │   ├── TTSConnectionError
    │   └── TTSTimeoutError
    ├── AudioError           — audio processing
    └── PipelineError        — orchestrator / scheduling
"""


class XspyError(Exception):
    """Base exception for all xspy errors."""

    def __init__(self, message: str, *, module: str = "", context: dict | None = None) -> None:
        self.module = module
        self.context = context or {}
        super().__init__(message)


# --- Config ---


class ConfigError(XspyError):
    """Configuration loading or validation failure."""


# --- Parser ---


class ParserError(XspyError):
    """Novel file parsing failure."""


# --- LLM ---


class LLMError(XspyError):
    """LLM client base error."""


class LLMConnectionError(LLMError):
    """Cannot reach LLM endpoint."""


class LLMResponseError(LLMError):
    """LLM returned invalid or unparseable response."""


class LLMCacheMissError(LLMError):
    """LLM cache miss in replay-only mode."""


# --- Agent ---


class AgentError(XspyError):
    """Screenwriter or character engine failure."""


# --- Emotion ---


class EmotionError(XspyError):
    """Emotion inference failure."""


# --- Voice ---


class VoiceError(XspyError):
    """Voice bank assignment failure."""


# --- TTS ---


class TTSError(XspyError):
    """TTS synthesis base error."""


class TTSConnectionError(TTSError):
    """Cannot reach TTS server."""


class TTSTimeoutError(TTSError):
    """TTS request timed out."""


# --- Audio ---


class AudioError(XspyError):
    """Audio processing failure."""


# --- Pipeline ---


class PipelineError(XspyError):
    """Pipeline orchestration failure."""
