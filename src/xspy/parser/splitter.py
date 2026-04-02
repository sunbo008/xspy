"""Chapter splitting logic for novel text."""

from __future__ import annotations

import re

from xspy.core.models import Chapter

_DEFAULT_CHAPTER_PATTERN = (
    r"^\s*第[零一二三四五六七八九十百千万\d]+[章节回卷集篇]"
    r"|^\s*Chapter\s+\d+"
    r"|^\s*CHAPTER\s+\d+"
)


def split_chapters(
    text: str,
    *,
    chapter_pattern_override: str | None = None,
) -> list[Chapter]:
    """Split novel text into chapters using regex pattern matching.

    Falls back to a single chapter if no chapter markers are found.
    """
    pattern = chapter_pattern_override or _DEFAULT_CHAPTER_PATTERN
    matches = list(re.finditer(pattern, text, re.MULTILINE))

    if not matches:
        return [
            Chapter(
                index=0,
                title="",
                text=text.strip(),
                word_count=len(text.strip()),
            )
        ]

    chapters: list[Chapter] = []

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[start:end].strip()

        first_newline = chunk.find("\n")
        title_line = chunk[:first_newline].strip() if first_newline >= 0 else chunk.strip()
        body = chunk[first_newline:].strip() if first_newline >= 0 else ""

        chapters.append(
            Chapter(
                index=i,
                title=title_line,
                text=body,
                word_count=len(body),
            )
        )

    return chapters
