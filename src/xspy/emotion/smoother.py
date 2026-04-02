"""Emotion transition smoothing.

Ensures that emotions don't jump abruptly between adjacent utterances
unless a scene break or dramatic event justifies it.
"""

from __future__ import annotations

from xspy.core.models import Utterance

_VAD_JUMP_THRESHOLD = 0.5


def smooth_emotions(utterances: list[Utterance]) -> list[Utterance]:
    """Apply smoothing to a sequence of emotion-annotated utterances.

    Rules:
    1. If same speaker has a VAD jump > threshold between consecutive turns,
       interpolate toward the new value.
    2. Narrator emotions should transition gradually between scenes.
    """
    if len(utterances) <= 1:
        return utterances

    result: list[Utterance] = [utterances[0]]

    for i in range(1, len(utterances)):
        curr = utterances[i]
        prev = result[-1]

        if not curr.emotion_detail or not prev.emotion_detail:
            result.append(curr)
            continue

        if curr.speaker_id == prev.speaker_id:
            jump = _vad_distance(prev.emotion_detail.vad, curr.emotion_detail.vad)
            if jump > _VAD_JUMP_THRESHOLD:
                smoothed_vad = _interpolate_vad(prev.emotion_detail.vad, curr.emotion_detail.vad)
                smoothed_intensity = (
                    prev.emotion_detail.intensity + curr.emotion_detail.intensity
                ) / 2
                new_detail = curr.emotion_detail.model_copy(
                    update={"vad": smoothed_vad, "intensity": smoothed_intensity}
                )
                curr = curr.model_copy(update={"emotion_detail": new_detail})

        result.append(curr)

    return result


def detect_emotion_jumps(utterances: list[Utterance]) -> list[tuple[int, float]]:
    """Return indices and magnitudes of large emotion jumps."""
    jumps: list[tuple[int, float]] = []
    for i in range(1, len(utterances)):
        curr = utterances[i]
        prev = utterances[i - 1]
        if curr.emotion_detail and prev.emotion_detail:
            dist = _vad_distance(prev.emotion_detail.vad, curr.emotion_detail.vad)
            if dist > _VAD_JUMP_THRESHOLD:
                jumps.append((i, dist))
    return jumps


def _vad_distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    """Euclidean distance in VAD space."""
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def _interpolate_vad(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
    ratio: float = 0.6,
) -> tuple[float, float, float]:
    """Interpolate between two VAD vectors (bias toward `b`)."""
    return (
        round(a[0] * (1 - ratio) + b[0] * ratio, 3),
        round(a[1] * (1 - ratio) + b[1] * ratio, 3),
        round(a[2] * (1 - ratio) + b[2] * ratio, 3),
    )
