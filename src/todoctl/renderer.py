from __future__ import annotations
from .models import MonthDocument, Status

STATUS_ORDER = {
    Status.DOING: 0,
    Status.OPEN: 1,
    Status.SIDE: 2,
    Status.DONE: 3,
}

def sort_tasks(doc: MonthDocument) -> MonthDocument:
    doc.tasks.sort(key=lambda task: (STATUS_ORDER[task.status], task.title.lower(), task.id))
    return doc

def render_month(doc: MonthDocument) -> str:
    sort_tasks(doc)
    lines = [f"# todoctl month: {doc.month}", ""]
    for task in doc.tasks:
        lines.append(f"[{task.id}] [{task.status.value}] {task.title}")
    lines.append("")
    return "\n".join(lines)
