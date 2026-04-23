"""
进度跟踪服务
支持实时进度报告和任务取消
"""

import threading
import uuid
from typing import Dict, Any, Optional, Callable
from .logger import logger


class ProgressTracker:
    """进度跟踪器"""

    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_task(self) -> str:
        task_id = str(uuid.uuid4())[:8]
        with self._lock:
            self._tasks[task_id] = {
                "status": "pending",
                "progress": 0,
                "message": "准备中...",
                "cancelled": False,
                "steps": [],
            }
        logger.info(f"创建任务: {task_id}")
        return task_id

    def update(self, task_id: str, progress: int, message: str, step: str = ""):
        with self._lock:
            if task_id not in self._tasks:
                return
            self._tasks[task_id]["progress"] = progress
            self._tasks[task_id]["message"] = message
            self._tasks[task_id]["status"] = "running"
            if step:
                self._tasks[task_id]["steps"].append(step)
        logger.info(f"任务 {task_id} 进度: {progress}% - {message}")

    def complete(self, task_id: str, message: str = "完成"):
        with self._lock:
            if task_id not in self._tasks:
                return
            self._tasks[task_id]["progress"] = 100
            self._tasks[task_id]["message"] = message
            self._tasks[task_id]["status"] = "completed"

    def fail(self, task_id: str, message: str):
        with self._lock:
            if task_id not in self._tasks:
                return
            self._tasks[task_id]["message"] = message
            self._tasks[task_id]["status"] = "failed"

    def cancel(self, task_id: str):
        with self._lock:
            if task_id not in self._tasks:
                return
            self._tasks[task_id]["cancelled"] = True
            self._tasks[task_id]["message"] = "已取消"
            self._tasks[task_id]["status"] = "cancelled"
        logger.info(f"任务 {task_id} 已取消")

    def is_cancelled(self, task_id: str) -> bool:
        with self._lock:
            if task_id not in self._tasks:
                return False
            return self._tasks[task_id].get("cancelled", False)

    def get_status(self, task_id: str) -> Dict[str, Any]:
        with self._lock:
            if task_id not in self._tasks:
                return {"status": "not_found", "progress": 0, "message": "任务不存在"}
            task = self._tasks[task_id]
            return {
                "task_id": task_id,
                "status": task["status"],
                "progress": task["progress"],
                "message": task["message"],
                "steps": task["steps"][-5:],
            }

    def cleanup(self, task_id: str):
        with self._lock:
            self._tasks.pop(task_id, None)


progress_tracker = ProgressTracker()
