"""PDF file parser using pdfplumber."""

from __future__ import annotations

from pathlib import Path

import pdfplumber


def parse_pdf(file_path: Path, *, encoding_override: str | None = None) -> str:
    """Extract text content from a PDF file."""
    parts: list[str] = []
    with pdfplumber.open(str(file_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text.strip():
                parts.append(text.strip())
    return "\n\n".join(parts)
