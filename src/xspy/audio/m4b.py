"""M4B audiobook assembly with chapter markers."""

from __future__ import annotations

from pathlib import Path

import structlog
from pydub import AudioSegment

from xspy.core.models import AudioBookMetadata, ChapterAudio, ChapterMarker

logger = structlog.get_logger()


def assemble_m4b(
    chapters: list[ChapterAudio],
    output_path: Path,
    *,
    metadata: AudioBookMetadata | None = None,
    bitrate: str = "128k",
) -> tuple[Path, list[ChapterMarker], int]:
    """Assemble chapter WAV files into a single M4B audiobook.

    Returns: (output_path, chapter_markers, total_duration_ms)
    """
    chapters_sorted = sorted(chapters, key=lambda c: c.chapter_index)

    combined = AudioSegment.empty()
    markers: list[ChapterMarker] = []

    for ch in chapters_sorted:
        if not ch.file_path.exists():
            logger.warning("m4b.chapter_missing", chapter_index=ch.chapter_index)
            continue

        markers.append(
            ChapterMarker(
                title=ch.chapter_title or f"Chapter {ch.chapter_index + 1}",
                start_ms=len(combined),
            )
        )

        audio = AudioSegment.from_file(str(ch.file_path))
        combined += audio

    output_path.parent.mkdir(parents=True, exist_ok=True)

    combined.export(
        str(output_path),
        format="ipod",
        codec="aac",
        bitrate=bitrate,
        tags={
            "title": metadata.title if metadata else "Audiobook",
            "artist": metadata.author if metadata else "",
        },
    )

    total_ms = len(combined)
    logger.info("m4b.assembled", chapters=len(markers), duration_ms=total_ms)
    return output_path, markers, total_ms


def write_chapter_metadata(
    markers: list[ChapterMarker],
    output_path: Path,
) -> Path:
    """Write chapter markers to a metadata file for ffmpeg chapter injection."""
    meta_path = output_path.with_suffix(".chapters.txt")
    lines = [";FFMETADATA1"]
    for i, m in enumerate(markers):
        end_ms = markers[i + 1].start_ms if i + 1 < len(markers) else m.start_ms + 600000
        lines.extend(
            [
                "",
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={m.start_ms}",
                f"END={end_ms}",
                f"title={m.title}",
            ]
        )
    meta_path.write_text("\n".join(lines), encoding="utf-8")
    return meta_path
