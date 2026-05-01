"""
进度跟踪路由
"""

import asyncio
from fastapi import APIRouter
from ..progress import progress_tracker

router = APIRouter(prefix="/api", tags=["progress"])


@router.post("/create-task")
async def create_task():
    task_id = progress_tracker.create_task()
    return {"task_id": task_id}


@router.get("/progress/{task_id}")
async def get_progress(task_id: str):
    import json

    async def event_generator():
        last_status = None
        while True:
            status = progress_tracker.get_status(task_id)
            current = json.dumps(status, ensure_ascii=False)

            if current != last_status:
                yield f"data: {current}\n\n"
                last_status = current

            if status.get("status") in ("completed", "failed", "cancelled", "not_found"):
                progress_tracker.cleanup(task_id)
                break

            await asyncio.sleep(0.3)

    from fastapi.responses import StreamingResponse
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/cancel/{task_id}")
async def cancel_task(task_id: str):
    progress_tracker.cancel(task_id)
    return {"success": True, "message": "任务已取消"}
