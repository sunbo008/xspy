"""Pipeline task management endpoints."""

from __future__ import annotations

import uuid
from pathlib import Path

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from xspy.core.models import PipelineInput

router = APIRouter()
logger = structlog.get_logger()

_UPLOAD_DIR = Path("data/uploads")
_task_store: dict[str, dict] = {}


class TaskStartRequest(BaseModel):
    novel_id: str
    chapter_indices: list[int] | None = None
    force_stages: list[str] | None = None


class TaskStatusResponse(BaseModel):
    task_id: str
    novel_id: str
    status: str
    progress: float = 0.0
    message: str = ""


@router.post("/start", response_model=TaskStatusResponse)
async def start_task(req: TaskStartRequest, bg: BackgroundTasks) -> TaskStatusResponse:
    """Start a novel processing pipeline task."""
    upload_dir = _UPLOAD_DIR / req.novel_id
    if not upload_dir.exists():
        raise HTTPException(404, "Novel not found. Upload first.")

    novel_files = list(upload_dir.glob("*.*"))
    if not novel_files:
        raise HTTPException(404, "No novel file found in upload directory")

    task_id = uuid.uuid4().hex[:12]
    _task_store[task_id] = {
        "task_id": task_id,
        "novel_id": req.novel_id,
        "status": "queued",
        "progress": 0.0,
        "message": "Queued for processing",
    }

    bg.add_default(
        _run_pipeline,
        task_id,
        novel_files[0],
        req.chapter_indices,
    )

    logger.info("task.started", task_id=task_id, novel_id=req.novel_id)
    return TaskStatusResponse(**_task_store[task_id])


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """Get the status of a processing task."""
    if task_id not in _task_store:
        raise HTTPException(404, "Task not found")
    return TaskStatusResponse(**_task_store[task_id])


@router.get("/", response_model=list[TaskStatusResponse])
async def list_tasks() -> list[TaskStatusResponse]:
    """List all tasks."""
    return [TaskStatusResponse(**t) for t in _task_store.values()]


async def _run_pipeline(
    task_id: str,
    novel_file: Path,
    chapter_indices: list[int] | None,
) -> None:
    """Background pipeline execution."""
    _task_store[task_id]["status"] = "running"
    _task_store[task_id]["message"] = "Pipeline started"

    try:
        from xspy.pipeline.__main__ import _build_orchestrator

        orchestrator = _build_orchestrator()
        result = orchestrator.process(
            PipelineInput(
                novel_file=novel_file,
                chapter_indices=chapter_indices,
            )
        )

        _task_store[task_id]["status"] = "completed"
        _task_store[task_id]["progress"] = 100.0
        _task_store[task_id]["message"] = (
            f"Done: {result.stats.chapters_processed} chapters in {result.stats.total_duration_ms}ms"
        )
    except Exception as e:
        logger.error("task.failed", task_id=task_id, error=str(e))
        _task_store[task_id]["status"] = "failed"
        _task_store[task_id]["message"] = str(e)
