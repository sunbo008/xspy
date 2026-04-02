"""EPUB file parser."""

from __future__ import annotations

import re
from pathlib import Path

import ebooklib
from ebooklib import epub


def parse_epub(file_path: Path, *, encoding_override: str | None = None) -> str:
    """Extract text content from an EPUB file."""
    book = epub.read_epub(str(file_path), options={"ignore_ncx": True})
    parts: list[str] = []

    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        content = item.get_content()
        if isinstance(content, bytes):
            text = content.decode(encoding_override or "utf-8", errors="replace")
        else:
            text = str(content)
        text = _strip_html(text)
        if text.strip():
            parts.append(text.strip())

    return "\n\n".join(parts)


def _strip_html(html: str) -> str:
    """Remove HTML tags and decode entities."""
    text = re.sub(r"<[^>]+>", "", html)
    text = text.replace("&nbsp;", " ")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&amp;", "&")
    text = text.replace("&quot;", '"')
    return text
