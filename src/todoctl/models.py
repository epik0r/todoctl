from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum

class Status(StrEnum):
    OPEN = "OPEN"
    DOING = "DOING"
    SIDE = "SIDE"
    DONE = "DONE"

@dataclass(slots=True)
class Task:
    id: int
    title: str
    status: Status = Status.OPEN

@dataclass(slots=True)
class MonthDocument:
    month: str
    tasks: list[Task] = field(default_factory=list)

    def next_id(self) -> int:
        return max((task.id for task in self.tasks), default=0) + 1
