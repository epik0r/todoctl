from __future__ import annotations
import re
from .models import MonthDocument, Status, Task

HEADER_RE = re.compile(r"^#\s+todoctl month:\s+(\d{4}-\d{2})\s*$")
STD_RE = re.compile(r"^\[(?P<id>\d+)\]\s+\[(?P<status>OPEN|DOING|SIDE|DONE)\]\s+(?P<title>.+?)\s*$")

def parse_month(text: str, fallback_month: str) -> MonthDocument:
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
