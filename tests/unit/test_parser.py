"""Unit tests for the novel parser module."""

from __future__ import annotations

from pathlib import Path

import pytest

from xspy.core.exceptions import ParserError
from xspy.core.models import ParseInput
from xspy.parser.service import NovelParserService
from xspy.parser.splitter import split_chapters

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestSplitChapters:
    def test_chinese_chapter_markers(self):
        text = "第一章 开始\n正文1\n第二章 继续\n正文2"
        chapters = split_chapters(text)
        assert len(chapters) == 2
        assert chapters[0].title == "第一章 开始"
        assert chapters[1].title == "第二章 继续"

    def test_no_chapter_markers(self):
        text = "这是一段没有章节标记的文本。"
        chapters = split_chapters(text)
        assert len(chapters) == 1
        assert chapters[0].index == 0

    def test_custom_pattern(self):
        text = "=== Part 1 ===\nbody1\n=== Part 2 ===\nbody2"
        chapters = split_chapters(text, chapter_pattern_override=r"^=== Part \d+ ===")
        assert len(chapters) == 2

    def test_word_count(self):
        text = "第一章 测试\n一二三四五\n第二章 测试2\n六七八"
        chapters = split_chapters(text)
        assert chapters[0].word_count > 0
        assert chapters[1].word_count > 0

    def test_english_chapter(self):
        text = "Chapter 1\nFirst chapter body\nChapter 2\nSecond chapter body"
        chapters = split_chapters(text)
        assert len(chapters) == 2


class TestNovelParserService:
    def test_parse_txt(self):
        novel_path = FIXTURES_DIR / "novels" / "test_novel.txt"
        if not novel_path.exists():
            pytest.skip("Test novel fixture not found")

        parser = NovelParserService()
        result = parser.process(ParseInput(file_path=novel_path))
        assert result.metadata.source_format == ".txt"
        assert len(result.chapters) == 3
        assert result.chapters[0].title == "第一章 初入江湖"
        assert result.metadata.total_word_count > 0

    def test_file_not_found(self):
        parser = NovelParserService()
        with pytest.raises(ParserError, match="File not found"):
            parser.process(ParseInput(file_path=Path("/nonexistent/novel.txt")))

    def test_unsupported_format(self, tmp_path: Path):
        bad_file = tmp_path / "novel.docx"
        bad_file.write_text("content")
        parser = NovelParserService()
        with pytest.raises(ParserError, match="Unsupported file format"):
            parser.process(ParseInput(file_path=bad_file))


class TestTxtParser:
    def test_encoding_detection(self, tmp_path: Path):
        content = "中文测试内容"
        f = tmp_path / "test.txt"
        f.write_bytes(content.encode("gb2312"))

        from xspy.parser.txt_parser import parse_txt

        result = parse_txt(f)
        assert "中文" in result

    def test_explicit_encoding(self, tmp_path: Path):
        content = "UTF-8 内容"
        f = tmp_path / "test.txt"
        f.write_text(content, encoding="utf-8")

        from xspy.parser.txt_parser import parse_txt

        result = parse_txt(f, encoding_override="utf-8")
        assert result == content
