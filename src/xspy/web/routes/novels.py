"""Novel management endpoints."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

router = APIRouter()
logger = structlog.get_logger()

_UPLOAD_DIR = Path("data/uploads")
_ALLOWED_EXTENSIONS = {".txt", ".epub", ".pdf"}


class NovelInfo(BaseModel):
    id: str
    filename: str
    file_size: int
    status: str = "uploaded"


class NovelListResponse(BaseModel):
    novels: list[NovelInfo]


@router.post("/upload", response_model=NovelInfo)
async def upload_novel(file: UploadFile) -> NovelInfo:
    """Upload a novel file for processing."""
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported format: {suffix}. Allowed: {_ALLOWED_EXTENSIONS}")

    novel_id = uuid.uuid4().hex[:12]
    upload_dir = _UPLOAD_DIR / novel_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    dest = upload_dir / file.filename
    content = await file.read()

    max_size = 100 * 1024 * 1024  # 100MB
    if len(content) > max_size:
        raise HTTPException(413, "File too large (max 100MB)")

    dest.write_bytes(content)
    logger.info("novel.uploaded", novel_id=novel_id, filename=file.filename, size=len(content))

    return NovelInfo(id=novel_id, filename=file.filename, file_size=len(content))


@router.get("/", response_model=NovelListResponse)
async def list_novels() -> NovelListResponse:
    """List all uploaded novels."""
    novels: list[NovelInfo] = []
    if _UPLOAD_DIR.exists():
        for d in sorted(_UPLOAD_DIR.iterdir()):
            if d.is_dir():
                files = list(d.glob("*.*"))
                if files:
                    f = files[0]
                    novels.append(
                        NovelInfo(
                            id=d.name,
                            filename=f.name,
                            file_size=f.stat().st_size,
                        )
                    )
    return NovelListResponse(novels=novels)


@router.delete("/{novel_id}")
async def delete_novel(novel_id: str) -> dict[str, str]:
    """Delete an uploaded novel and its data."""
    upload_path = _UPLOAD_DIR / novel_id
    if not upload_path.exists():
        raise HTTPException(404, "Novel not found")

    shutil.rmtree(upload_path)
    logger.info("novel.deleted", novel_id=novel_id)
    return {"status": "deleted", "novel_id": novel_id}
