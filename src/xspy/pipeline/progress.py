"""Real-time pipeline progress tracking."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum


class PipelinePhase(StrEnum):
    """Pipeline processing phases."""

    PARSING = "parsing"
    CHARACTER_ANALYSIS = "character_analysis"
    SCREENWRITING = "screenwriting"
    EMOTION_INFERENCE = "emotion_inference"
    VOICE_ASSIGNMENT = "voice_assignment"
    TTS_SYNTHESIS = "tts_synthesis"
    AUDIO_ASSEMBLY = "audio_assembly"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class ProgressEvent:
    """A single progress update event."""

    phase: PipelinePhase
    percent: float
    message: str = ""
    chapter_index: int | None = None
    elapsed_ms: int = 0
    eta_ms: int = 0
    timestamp: float = field(default_factory=time.time)


ProgressCallback = Callable[[ProgressEvent], None]


class ProgressTracker:
    """Tracks and emits pipeline progress events."""

    def __init__(self, total_chapters: int, callback: ProgressCallback | None = None) -> None:
        self._total_chapters = max(total_chapters, 1)
        self._callback = callback
        self._start_time = time.monotonic()
        self._phase_weights = {
            PipelinePhase.PARSING: 0.05,
            PipelinePhase.CHARACTER_ANALYSIS: 0.10,
            PipelinePhase.SCREENWRITING: 0.20,
            PipelinePhase.EMOTION_INFERENCE: 0.15,
            PipelinePhase.VOICE_ASSIGNMENT: 0.05,
            PipelinePhase.TTS_SYNTHESIS: 0.35,
            PipelinePhase.AUDIO_ASSEMBLY: 0.10,
        }
        self._completed_phases: list[PipelinePhase] = []
        self._current_phase: PipelinePhase | None = None
        self._phase_progress: float = 0.0

    def enter_phase(self, phase: PipelinePhase, message: str = "") -> None:
        """Mark the start of a new pipeline phase."""
        self._current_phase = phase
        self._phase_progress = 0.0
        self._emit(phase, self._overall_percent(), message)

    def update_phase(
        self,
        progress: float,
        *,
        message: str = "",
        chapter_index: int | None = None,
    ) -> None:
        """Update progress within the current phase (0.0 to 1.0)."""
        self._phase_progress = max(0.0, min(1.0, progress))
        if self._current_phase:
            self._emit(self._current_phase, self._overall_percent(), message, chapter_index)

    def complete_phase(self, phase: PipelinePhase) -> None:
        """Mark a phase as complete."""
        self._completed_phases.append(phase)
        self._phase_progress = 1.0
        self._emit(phase, self._overall_percent(), f"{phase.value} complete")

    def _overall_percent(self) -> float:
        """Calculate overall pipeline progress percentage."""
        completed_weight = sum(self._phase_weights.get(p, 0) for p in self._completed_phases)
        current_weight = 0.0
        if self._current_phase:
            current_weight = self._phase_weights.get(self._current_phase, 0) * self._phase_progress
        return round((completed_weight + current_weight) * 100, 1)

    def _emit(
        self,
        phase: PipelinePhase,
        percent: float,
        message: str = "",
        chapter_index: int | None = None,
    ) -> None:
        elapsed_ms = int((time.monotonic() - self._start_time) * 1000)
        eta_ms = int(elapsed_ms / max(percent, 0.1) * (100 - percent)) if percent > 0 else 0

        event = ProgressEvent(
            phase=phase,
            percent=percent,
            message=message,
            chapter_index=chapter_index,
            elapsed_ms=elapsed_ms,
            eta_ms=eta_ms,
        )
        if self._callback:
            self._callback(event)
