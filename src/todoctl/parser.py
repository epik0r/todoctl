"""
Parsing logic for todoctl month documents.

This module converts editable text representations of monthly todo data
into structured in-memory models. It supports both the current todoctl
format and selected legacy shorthand markers for compatibility.
"""
from __future__ import annotations
import re
from .models import MonthDocument, Status, Task

HEADER_RE = re.compile(r"^#\s+todoctl month:\s+(\d{4}-\d{2})\s*$")
STD_RE = re.compile(r"^\[(?P<id>\d+)\]\s+\[(?P<status>OPEN|DOING|SIDE|DONE)\]\s+(?P<title>.+?)\s*$")

def parse_month(text: str, fallback_month: str) -> MonthDocument:
    """
    Parse a textual month document into a structured model.

    Processes the given text line by line, extracting the month header
    and converting task entries into Task objects. Supports both the
    standard todoctl format and legacy shorthand notations for task
    states. Automatically assigns incremental IDs for entries without
    explicit identifiers and removes duplicate IDs by keeping the last
    occurrence.

    Args:
        text (str): Raw text content of the month document.
        fallback_month (str): Default month identifier if no header is found.

    Returns:
        MonthDocument: Parsed month document with tasks.
    """
    month = fallback_month
    tasks: list[Task] = []
    next_auto_id = 1

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        match = HEADER_RE.match(line)
        if match:
            month = match.group(1)
            continue
        if line.startswith("#"):
            continue
        std = STD_RE.match(line)
        if std:
            task_id = int(std.group("id"))
            status = Status(std.group("status"))
            title = std.group("title").strip()
            tasks.append(Task(id=task_id, status=status, title=title))
            next_auto_id = max(next_auto_id, task_id + 1)
            continue
        if line.startswith("!--"):
            tasks.append(Task(id=next_auto_id, status=Status.DONE, title=line[3:].strip()))
            next_auto_id += 1
            continue
        if line.startswith("---"):
            tasks.append(Task(id=next_auto_id, status=Status.DOING, title=line[3:].strip()))
            next_auto_id += 1
            continue
        if line.startswith("(") and line.endswith(")"):
            tasks.append(Task(id=next_auto_id, status=Status.SIDE, title=line[1:-1].strip()))
            next_auto_id += 1
            continue
        tasks.append(Task(id=next_auto_id, status=Status.OPEN, title=line))
        next_auto_id += 1

    dedup: dict[int, Task] = {}
    for task in tasks:
        dedup[task.id] = task
    return MonthDocument(month=month, tasks=list(dedup.values()))
