"""Unit tests for pipeline progress tracker."""

from __future__ import annotations

from xspy.pipeline.progress import PipelinePhase, ProgressEvent, ProgressTracker


class TestProgressTracker:
    def test_phases_emit_events(self):
        events: list[ProgressEvent] = []
        tracker = ProgressTracker(total_chapters=3, callback=events.append)

        tracker.enter_phase(PipelinePhase.PARSING, "Starting parse")
        assert len(events) == 1
        assert events[0].phase == PipelinePhase.PARSING
        assert events[0].percent == 0.0

    def test_progress_increases(self):
        events: list[ProgressEvent] = []
        tracker = ProgressTracker(total_chapters=3, callback=events.append)

        tracker.enter_phase(PipelinePhase.PARSING)
        tracker.update_phase(0.5)
        tracker.complete_phase(PipelinePhase.PARSING)

        assert events[-1].percent > 0.0

    def test_complete_phase_accumulates(self):
        events: list[ProgressEvent] = []
        tracker = ProgressTracker(total_chapters=3, callback=events.append)

        tracker.enter_phase(PipelinePhase.PARSING)
        tracker.complete_phase(PipelinePhase.PARSING)
        p1 = events[-1].percent

        tracker.enter_phase(PipelinePhase.CHARACTER_ANALYSIS)
        tracker.complete_phase(PipelinePhase.CHARACTER_ANALYSIS)
        p2 = events[-1].percent

        assert p2 > p1

    def test_no_callback(self):
        tracker = ProgressTracker(total_chapters=3)
        tracker.enter_phase(PipelinePhase.PARSING)
        tracker.complete_phase(PipelinePhase.PARSING)
