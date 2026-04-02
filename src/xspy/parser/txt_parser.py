"""TXT file parser with encoding auto-detection."""

from __future__ import annotations

from pathlib import Path

import chardet


def parse_txt(file_path: Path, *, encoding_override: str | None = None) -> str:
    """Read a TXT file and return its content as a string."""
    raw_bytes = file_path.read_bytes()

    if encoding_override:
        return raw_bytes.decode(encoding_override)

    detection = chardet.detect(raw_bytes)
    encoding = detection.get("encoding") or "utf-8"

    return raw_bytes.decode(encoding, errors="replace")
