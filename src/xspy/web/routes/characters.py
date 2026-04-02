"""Character and voice assignment endpoints."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from xspy.core.models import CastRegistry, VoiceAssignment

router = APIRouter()

_INTERMEDIATE_DIR = Path("data/intermediate")


class CharacterUpdate(BaseModel):
    voice_description: str | None = None
    profile_overrides: dict | None = None


@router.get("/{novel_slug}/cast", response_model=CastRegistry)
async def get_cast(novel_slug: str) -> CastRegistry:
    """Get the cast registry for a novel."""
    path = _INTERMEDIATE_DIR / novel_slug / "cast_registry.json"
    if not path.exists():
        raise HTTPException(404, "Cast registry not found. Run character analysis first.")
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = data.get("data", data)
    return CastRegistry.model_validate(raw)


@router.put("/{novel_slug}/cast/{speaker_id}")
async def update_character(
    novel_slug: str, speaker_id: str, update: CharacterUpdate
) -> dict[str, str]:
    """Update a character's profile or voice description."""
    path = _INTERMEDIATE_DIR / novel_slug / "cast_registry.json"
    if not path.exists():
        raise HTTPException(404, "Cast registry not found")

    data = json.loads(path.read_text(encoding="utf-8"))
    raw = data.get("data", data)
    registry = CastRegistry.model_validate(raw)

    found = False
    for char in registry.characters:
        if char.speaker_id == speaker_id:
            if update.voice_description is not None:
                char.voice_description = update.voice_description
            found = True
            break

    if not found:
        raise HTTPException(404, f"Character '{speaker_id}' not found")

    data["data"] = json.loads(registry.model_dump_json())
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "updated", "speaker_id": speaker_id}


@router.get("/{novel_slug}/voices", response_model=VoiceAssignment)
async def get_voice_assignment(novel_slug: str) -> VoiceAssignment:
    """Get voice assignments for a novel."""
    path = _INTERMEDIATE_DIR / novel_slug / "voice_assignment.json"
    if not path.exists():
        raise HTTPException(404, "Voice assignment not found. Run voice bank first.")
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = data.get("data", data)
    return VoiceAssignment.model_validate(raw)
