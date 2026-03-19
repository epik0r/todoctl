from __future__ import annotations
from datetime import datetime

def resolve_month(value: str | None) -> str:
    now = datetime.now()
    if value is None or not str(value).strip():
        return now.strftime("%Y-%m")
    raw = str(value).strip()
    if len(raw) == 7 and raw[4] == "-":
        year = int(raw[:4])
        month = int(raw[5:])
        if month < 1 or month > 12:
            raise ValueError("Invalid month")
        return f"{year:04d}-{month:02d}"
    if raw.isdigit():
        month = int(raw)
        if month < 1 or month > 12:
            raise ValueError("Invalid month")
        return f"{now.year:04d}-{month:02d}"
    raise ValueError("Month must be YYYY-MM, MM or M")
