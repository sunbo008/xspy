"""Screenplay review and editing endpoints."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from xspy.core.models import ChapterScreenplay, EmotionType

router = APIRouter()

_INTERMEDIATE_DIR = Path("data/intermediate")


class UtteranceUpdate(BaseModel):
    speaker_id: str | None = None
    text: str | None = None
    emotion_type: EmotionType | None = None


@router.get("/{novel_slug}/chapters")
async def list_chapters(novel_slug: str) -> dict:
    """List available screenplay chapters."""
    sp_dir = _INTERMEDIATE_DIR / novel_slug / "screenplay"
    en_dir = _INTERMEDIATE_DIR / novel_slug / "enriched_screenplay"

    chapters = []
    target = en_dir if en_dir.exists() else sp_dir
    if target and target.exists():
        for f in sorted(target.glob("ch*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            raw = data.get("data", data)
            chapters.append(
                {
                    "file": f.name,
                    "chapter_index": raw.get("chapter_index", 0),
                    "chapter_title": raw.get("chapter_title", ""),
                    "utterance_count": len(raw.get("utterances", [])),
                    "enriched": target == en_dir,
                }
            )
    return {"chapters": chapters}


@router.get("/{novel_slug}/chapters/{chapter_index}", response_model=ChapterScreenplay)
async def get_chapter(novel_slug: str, chapter_index: int) -> ChapterScreenplay:
    """Get a specific chapter screenplay."""
    for subdir in ["enriched_screenplay", "screenplay"]:
        path = _INTERMEDIATE_DIR / novel_slug / subdir / f"ch{chapter_index:03d}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            raw = data.get("data", data)
            return ChapterScreenplay.model_validate(raw)
    raise HTTPException(404, f"Chapter {chapter_index} not found")


@router.put("/{novel_slug}/chapters/{chapter_index}/utterances/{utterance_id}")
async def update_utterance(
    novel_slug: str,
    chapter_index: int,
    utterance_id: str,
    update: UtteranceUpdate,
) -> dict[str, str]:
    """Update a single utterance in a chapter screenplay."""
    for subdir in ["enriched_screenplay", "screenplay"]:
        path = _INTERMEDIATE_DIR / novel_slug / subdir / f"ch{chapter_index:03d}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            raw = data.get("data", data)
            screenplay = ChapterScreenplay.model_validate(raw)

            for utt in screenplay.utterances:
                if utt.id == utterance_id:
                    if update.speaker_id is not None:
                        utt.speaker_id = update.speaker_id
                    if update.text is not None:
                        utt.text = update.text
                    if update.emotion_type is not None:
                        utt.emotion_type = update.emotion_type

                    data["data"] = json.loads(screenplay.model_dump_json())
                    path.write_text(
                        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                    return {"status": "updated", "utterance_id": utterance_id}

            raise HTTPException(404, f"Utterance '{utterance_id}' not found")

    raise HTTPException(404, f"Chapter {chapter_index} not found")
