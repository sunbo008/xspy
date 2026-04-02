"""WebSocket endpoint for real-time pipeline progress streaming."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from xspy.web.routes.tasks import _task_store

router = APIRouter()


@router.websocket("/ws/progress/{task_id}")
async def progress_ws(websocket: WebSocket, task_id: str) -> None:
    """Stream pipeline progress for a task via WebSocket."""
    await websocket.accept()

    try:
        while True:
            task = _task_store.get(task_id)
            if not task:
                await websocket.send_json({"error": "Task not found"})
                break

            await websocket.send_json(
                {
                    "task_id": task["task_id"],
                    "status": task["status"],
                    "progress": task["progress"],
                    "message": task["message"],
                }
            )

            if task["status"] in ("completed", "failed"):
                break

            await asyncio.sleep(1)

    except WebSocketDisconnect:
        pass
