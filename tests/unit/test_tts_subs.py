"""Unit tests for TTS sub-modules: mock, normalizer, health."""

from __future__ import annotations

from pathlib import Path

from xspy.core.models import TTSRequest
from xspy.tts.mock import MockTTSEngine
from xspy.tts.normalizer import get_audio_info, normalize_audio


class TestMockTTSEngine:
    def test_generates_wav(self, tmp_path: Path):
        mock = MockTTSEngine(output_dir=tmp_path)
        req = TTSRequest(text="你好世界", voice_id="test-voice")
        resp = mock.process(req)

        assert resp.audio_path is not None
        assert resp.audio_path.exists()
        assert resp.engine_used == "mock"
        assert resp.duration_ms == len("你好世界") * 100  # 100ms per char

    def test_deterministic(self, tmp_path: Path):
        mock = MockTTSEngine(output_dir=tmp_path)
        req = TTSRequest(text="测试", voice_id="v1")
        r1 = mock.process(req)
        r2 = mock.process(req)
        assert r1.duration_ms == r2.duration_ms

    def test_call_count(self, tmp_path: Path):
        mock = MockTTSEngine(output_dir=tmp_path)
        assert mock.call_count == 0
        mock.process(TTSRequest(text="a", voice_id="v1"))
        mock.process(TTSRequest(text="b", voice_id="v2"))
        assert mock.call_count == 2

    def test_valid_wav_format(self, tmp_path: Path):
        mock = MockTTSEngine(output_dir=tmp_path)
        resp = mock.process(TTSRequest(text="验证格式", voice_id="v1"))
        assert resp.audio_path is not None
        info = get_audio_info(resp.audio_path)
        assert info["sample_rate"] == 24000
        assert info["channels"] == 1

    def test_normalize_mock_wav(self, tmp_path: Path):
        mock = MockTTSEngine(output_dir=tmp_path)
        resp = mock.process(TTSRequest(text="归一化测试", voice_id="v1"))
        assert resp.audio_path is not None
        output = normalize_audio(resp.audio_path, sample_rate=16000)
        info = get_audio_info(output)
        assert info["sample_rate"] == 16000
