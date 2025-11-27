from enum import Enum


class TaskStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    ARCHIVED = "archived"


ALLOWED_TASK_STATUSES = {s.value for s in TaskStatus}
