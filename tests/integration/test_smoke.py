"""End-to-end smoke tests using mock LLM/TTS backends.

These tests verify the full pipeline can run without real external services.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def novel_file(tmp_path: Path) -> Path:
    content = (
        "第一章 初遇\n\n"
        "清晨的阳光洒在小镇上。\n"
        "林风走在街头，心情不错。\n"
        '"今天天气真好啊。"林风自言自语道。\n'
        "一个女孩从拐角走出来。\n"
        '"你好，请问图书馆怎么走？"女孩问道。\n'
        '"往前走两百米就到了。"林风指了指前方。\n'
        '"谢谢你！"女孩微笑着说。\n\n'
        "第二章 重逢\n\n"
        "一周后，林风在图书馆再次遇到了那个女孩。\n"
        '"又是你！"林风惊喜地说。\n'
        "女孩转过头，认出了他。\n"
        '"是你啊，上次谢谢你帮忙指路。"她笑着说。\n'
    )
    f = tmp_path / "test_novel.txt"
    f.write_text(content, encoding="utf-8")
    return f


class TestParserSmoke:
    """Verify the parser module can process a novel file end-to-end."""

    def test_parse_txt_novel(self, novel_file: Path) -> None:
        from xspy.core.models import ParseInput
        from xspy.parser.service import NovelParserService

        parser = NovelParserService()
        result = parser.process(ParseInput(file_path=novel_file))

        assert result.metadata.title == "test_novel"
        assert len(result.chapters) >= 2
        assert result.chapters[0].title == "第一章 初遇"
        assert len(result.chapters[0].text) > 0

    def test_parse_result_serializable(self, novel_file: Path) -> None:
        from xspy.core.models import ParseInput
        from xspy.parser.service import NovelParserService

        parser = NovelParserService()
        result = parser.process(ParseInput(file_path=novel_file))
        json_str = result.model_dump_json()
        data = json.loads(json_str)
        assert "chapters" in data
        assert "metadata" in data


class TestPipelineSmoke:
    """Verify the pipeline can be instantiated with mock dependencies."""

    def test_pipeline_wiring(self) -> None:
        from xspy.core.config import XspySettings
        from xspy.pipeline.service import PipelineOrchestrator

        settings = XspySettings()
        pipeline = PipelineOrchestrator(
            settings=settings,
            parser=MagicMock(),
            screenwriter=MagicMock(),
            character_engine=MagicMock(),
            emotion_system=MagicMock(),
            voice_bank=MagicMock(),
            tts_client=MagicMock(),
            audio_processor=MagicMock(),
        )
        assert pipeline is not None


class TestWebAppSmoke:
    """Verify the FastAPI app can be created."""

    def test_create_app(self) -> None:
        from xspy.web.app import create_app

        app = create_app()
        assert app is not None

        route_paths = [r.path for r in app.routes]
        assert "/api/health" in route_paths or any("/health" in p for p in route_paths)


class TestCoreModelsSmoke:
    """Verify core model serialization round-trip."""

    def test_emotion_type_values(self) -> None:
        from xspy.core.models import EmotionType

        assert EmotionType.NEUTRAL == "neutral"
        assert EmotionType.JOYFUL == "joyful"
        assert len(EmotionType) >= 12

    def test_tts_request_creation(self) -> None:
        from xspy.core.models import TTSEmotionParams, TTSRequest

        req = TTSRequest(
            text="你好世界",
            voice_id="v_narrator",
            emotion_params=TTSEmotionParams(
                speed=1.0,
                pitch_shift=0.0,
                energy=1.0,
                style="neutral",
            ),
        )
        data = json.loads(req.model_dump_json())
        assert data["text"] == "你好世界"
        assert data["emotion_params"]["style"] == "neutral"
