"""
Core data models for todoctl.

This module defines the fundamental domain objects used throughout the
application, including task status values, individual tasks, and
monthly task documents.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum

class Status(StrEnum):
    """
    Enumeration of possible task statuses.

    Represents the lifecycle state of a task within a monthly document.
    """
    OPEN = "OPEN"
    DOING = "DOING"
    SIDE = "SIDE"
    DONE = "DONE"

@dataclass(slots=True)
class Task:
    """
    Representation of a single task.

    Attributes:
        id (int): Unique identifier of the task within a document.
        title (str): Short description of the task.
        status (Status): Current state of the task.
    """
    id: int
    title: str
    status: Status = Status.OPEN

@dataclass(slots=True)
class MonthDocument:
    """
    Collection of tasks for a specific month.

    Groups tasks under a common month identifier and provides helpers
    for managing task identifiers.

    Attributes:
        month (str): Month identifier (e.g. "2026-03").
        tasks (list[Task]): List of tasks belonging to the month.
    """
    month: str
    tasks: list[Task] = field(default_factory=list)

    def next_id(self) -> int:
        """
        Compute the next available task ID.

        Determines the highest existing task ID and returns the next
        incremented value.

        Returns:
            int: Next available task ID.
        """
        return max((task.id for task in self.tasks), default=0) + 1
