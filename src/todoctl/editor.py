from __future__ import annotations
import os, subprocess, tempfile
from .config import AppConfig
from .parser import parse_month
from .renderer import render_month, sort_tasks
from .store import load_month, save_month

def edit_month(config: AppConfig, month: str) -> None:
    doc = load_month(config, month)
    editor = config.editor or os.environ.get("EDITOR", "vim") or "vim"
    with tempfile.NamedTemporaryFile("w+", suffix=".todo", delete=False, encoding="utf-8") as handle:
        temp_path = handle.name
        handle.write(render_month(doc))
        handle.flush()
    try:
        subprocess.run([editor, temp_path], check=True)
        with open(temp_path, "r", encoding="utf-8") as handle:
            content = handle.read()
        updated = parse_month(content, fallback_month=month)
        sort_tasks(updated)
        save_month(config, updated)
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
