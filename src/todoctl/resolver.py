"""
Month resolution helpers for todoctl.

This module converts user-provided month arguments into normalized
internal month identifiers. It supports explicit year-month values
as well as shorthand numeric month input.
"""
from __future__ import annotations
from datetime import datetime

def resolve_month(value: str | None) -> str:
    """
    Resolve a user-provided month value into a normalized identifier.

    Accepts multiple input formats including full year-month strings
    (YYYY-MM) and numeric month values (M or MM). If no value is provided,
    the current month is used. Numeric inputs are resolved using the
    current year.

    Args:
        value (str | None): User-provided month value.

    Returns:
        str: Normalized month string in the format "YYYY-MM".

    Raises:
        ValueError: If the input format is invalid or the month is out of range.
    """
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
