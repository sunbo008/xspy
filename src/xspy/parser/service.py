"""NovelParserService: the main parser that delegates to format-specific parsers."""

from __future__ import annotations

import hashlib

import structlog

from xspy.core.exceptions import ParserError
from xspy.core.models import NovelMetadata, ParseInput, ParseResult
from xspy.parser.epub_parser import parse_epub
from xspy.parser.pdf_parser import parse_pdf
from xspy.parser.txt_parser import parse_txt

logger = structlog.get_logger()

_PARSERS = {
    ".txt": parse_txt,
    ".epub": parse_epub,
    ".pdf": parse_pdf,
}


class NovelParserService:
    """Parse novel files into structured chapters."""

    def process(self, input: ParseInput) -> ParseResult:
        file_path = input.file_path
        log = logger.bind(file=str(file_path))

        if not file_path.exists():
            raise ParserError(
                f"File not found: {file_path}",
                module="parser",
                context={"file_path": str(file_path)},
            )

        suffix = file_path.suffix.lower()
        parser_fn = _PARSERS.get(suffix)
        if not parser_fn:
            raise ParserError(
                f"Unsupported file format: {suffix}",
                module="parser",
                context={"supported": list(_PARSERS.keys())},
            )

        log.info("parser.start", format=suffix)
        raw_text = parser_fn(file_path, encoding_override=input.encoding_override)
        log.debug("parser.raw_text", length=len(raw_text))

        from xspy.parser.splitter import split_chapters

        chapters = split_chapters(
            raw_text,
            chapter_pattern_override=input.chapter_pattern_override,
        )

        file_hash = hashlib.md5(file_path.read_bytes()).hexdigest()
        total_words = sum(ch.word_count for ch in chapters)

        metadata = NovelMetadata(
            title=file_path.stem,
            total_word_count=total_words,
            source_format=suffix,
            file_hash=file_hash,
        )

        log.info("parser.done", chapters=len(chapters), total_words=total_words)
        return ParseResult(metadata=metadata, chapters=chapters)
