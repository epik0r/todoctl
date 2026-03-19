"""
Rendering and sorting helpers for todoctl.

This module transforms structured monthly todo data into the editable
text format used by todoctl and applies consistent task ordering based
on status, title, and task ID.
"""
from __future__ import annotations
from .models import MonthDocument, Status

STATUS_ORDER = {
    Status.DOING: 0,
    Status.OPEN: 1,
    Status.SIDE: 2,
    Status.DONE: 3,
}

def sort_tasks(doc: MonthDocument) -> MonthDocument:
    """
    Sort tasks within a month document.

    Orders tasks by status priority, then alphabetically by title,
    and finally by task ID to ensure deterministic output.

    Args:
        doc (MonthDocument): The document containing tasks to sort.

    Returns:
        MonthDocument: The same document instance with sorted tasks.
    """
    doc.tasks.sort(key=lambda task: (STATUS_ORDER[task.status], task.title.lower(), task.id))
    return doc

def render_month(doc: MonthDocument) -> str:
    """
    Render a month document into editable text format.

    Sorts tasks and converts them into the standard todoctl text
    representation, including a header and formatted task lines.

    Args:
        doc (MonthDocument): The document to render.

    Returns:
        str: Text representation of the month document.
    """
    sort_tasks(doc)
    lines = [f"# todoctl month: {doc.month}", ""]
    for task in doc.tasks:
        lines.append(f"[{task.id}] [{task.status.value}] {task.title}")
    lines.append("")
    return "\n".join(lines)
