"""Unit tests for emotion sub-modules: rule_engine, smoother, tts_adapter."""

from __future__ import annotations

from xspy.core.models import EmotionDetail, EmotionType, Utterance
from xspy.emotion.rule_engine import detect_emotion_from_cue, detect_paraverbals
from xspy.emotion.smoother import detect_emotion_jumps, smooth_emotions
from xspy.emotion.tts_adapter import EmotionTTSAdapter


class TestRuleEngine:
    def test_detect_joyful(self):
        assert detect_emotion_from_cue("他笑着说") == EmotionType.JOYFUL

    def test_detect_furious(self):
        assert detect_emotion_from_cue("他愤怒地吼道") == EmotionType.FURIOUS

    def test_detect_contemptuous(self):
        assert detect_emotion_from_cue("冷笑一声") == EmotionType.CONTEMPTUOUS

    def test_detect_sorrowful_cry(self):
        assert detect_emotion_from_cue("她哭了起来") == EmotionType.SORROWFUL

    def test_detect_none(self):
        assert detect_emotion_from_cue("他走进了房间") is None

    def test_detect_paraverbals_sigh(self):
        result = detect_paraverbals("他叹了口气")
        assert "sigh" in result

    def test_detect_paraverbals_laughter(self):
        result = detect_paraverbals("哈哈大笑")
        assert "laughter" in result

    def test_detect_multiple(self):
        result = detect_paraverbals("他叹了口气，然后哈哈笑了")
        assert "sigh" in result
        assert "laughter" in result

    def test_detect_no_paraverbals(self):
        result = detect_paraverbals("他说道")
        assert result == []


class TestSmoother:
    @staticmethod
    def _utt(uid: str, speaker: str, emotion: EmotionType, vad: tuple) -> Utterance:
        return Utterance(
            id=uid,
            speaker_id=speaker,
            text="test",
            emotion_type=emotion,
            emotion_detail=EmotionDetail(type=emotion, vad=vad, intensity=0.8),
        )

    def test_no_smoothing_for_single(self):
        utts = [self._utt("u1", "A", EmotionType.NEUTRAL, (0.5, 0.3, 0.5))]
        result = smooth_emotions(utts)
        assert len(result) == 1

    def test_smooth_big_jump(self):
        utts = [
            self._utt("u1", "A", EmotionType.JOYFUL, (0.9, 0.7, 0.6)),
            self._utt("u2", "A", EmotionType.FURIOUS, (0.1, 0.9, 0.7)),
        ]
        result = smooth_emotions(utts)
        assert result[1].emotion_detail is not None
        v = result[1].emotion_detail.vad
        assert v[0] < 0.9 and v[0] > 0.1  # interpolated

    def test_different_speakers_not_smoothed(self):
        utts = [
            self._utt("u1", "A", EmotionType.JOYFUL, (0.9, 0.7, 0.6)),
            self._utt("u2", "B", EmotionType.FURIOUS, (0.1, 0.9, 0.7)),
        ]
        result = smooth_emotions(utts)
        assert result[1].emotion_detail.vad == (0.1, 0.9, 0.7)

    def test_detect_jumps(self):
        utts = [
            self._utt("u1", "A", EmotionType.SERENE, (0.8, 0.2, 0.5)),
            self._utt("u2", "A", EmotionType.FURIOUS, (0.1, 0.9, 0.7)),
        ]
        jumps = detect_emotion_jumps(utts)
        assert len(jumps) == 1
        assert jumps[0][0] == 1


class TestTTSAdapter:
    def test_load_mapping(self):
        adapter = EmotionTTSAdapter()
        engines = adapter.get_supported_engines()
        assert "index-tts" in engines or len(engines) == 0

    def test_adapt_neutral(self):
        adapter = EmotionTTSAdapter()
        detail = EmotionDetail(type=EmotionType.NEUTRAL, intensity=0.5)
        params = adapter.adapt(detail, engine="index-tts")
        assert params.speed >= 0.5

    def test_adapt_high_intensity(self):
        adapter = EmotionTTSAdapter()
        detail = EmotionDetail(type=EmotionType.FURIOUS, intensity=1.0)
        params = adapter.adapt(detail, engine="index-tts")
        assert params.energy >= 1.0

    def test_adapt_unknown_engine(self):
        adapter = EmotionTTSAdapter()
        detail = EmotionDetail(type=EmotionType.JOYFUL, intensity=0.5)
        params = adapter.adapt(detail, engine="nonexistent")
        assert params.speed >= 0.5  # falls back to defaults
