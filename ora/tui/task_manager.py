"""Mock task queue for MVP."""

import random
import time
from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class MockTask:
    id: str
    description: str
    status: TaskStatus
    progress: float = 0.0
    created_at: float = field(default_factory=time.time)


class TaskManager:
    """Mock task manager. Phase 2 replaces with real async task queue."""

    def __init__(self) -> None:
        self.tasks: list[MockTask] = [
            MockTask(
                id="scan-downloads",
                description="Scanning ~/Downloads for duplicates",
                status=TaskStatus.RUNNING,
                progress=0.34,
            ),
            MockTask(
                id="cache-cleanup",
                description="Clearing stale cache entries",
                status=TaskStatus.RUNNING,
                progress=0.71,
            ),
            MockTask(
                id="dep-audit",
                description="Auditing Python dependencies",
                status=TaskStatus.COMPLETED,
                progress=1.0,
            ),
            MockTask(
                id="log-rotate",
                description="Rotating system logs",
                status=TaskStatus.PAUSED,
                progress=0.0,
            ),
        ]

    def tick(self) -> None:
        """Advance mock task progress. Called on timer."""
        for task in self.tasks:
            if task.status == TaskStatus.RUNNING:
                task.progress = min(1.0, task.progress + random.uniform(0.01, 0.04))
                if task.progress >= 1.0:
                    task.status = TaskStatus.COMPLETED
