"""
Editor integration for todoctl.

This module provides the workflow for opening decrypted monthly todo
content in a text editor, parsing the modified file after editing,
and saving it back in encrypted form.
"""
from __future__ import annotations
import os, subprocess, tempfile
from .config import AppConfig
from .parser import parse_month
from .renderer import render_month, sort_tasks
from .store import load_month, save_month

def edit_month(config: AppConfig, month: str) -> bool:
    """
    Open, edit, and optionally save a monthly todo document.

    Loads the encrypted monthly document, renders it into a temporary
    plaintext file, and opens it in the configured text editor. After
    editing, the content is parsed, normalized, and only saved back in
    encrypted form if the normalized content has changed.

    Args:
        config (AppConfig): Loaded application configuration.
        month (str): Target month identifier (e.g. "2026-03").

    Returns:
        bool: True if changes were saved, False if nothing changed.

    Raises:
        subprocess.CalledProcessError: If the editor exits with an error.
    """
    doc = load_month(config, month)
    original_rendered = render_month(doc)
    editor = config.editor or os.environ.get("EDITOR", "vim") or "vim"

    with tempfile.NamedTemporaryFile("w+", suffix=".todo", delete=False, encoding="utf-8") as handle:
        temp_path = handle.name
        handle.write(original_rendered)
        handle.flush()

    try:
        subprocess.run([editor, temp_path], check=True)

        with open(temp_path, "r", encoding="utf-8") as handle:
            content = handle.read()

        updated = parse_month(content, fallback_month=month)
        sort_tasks(updated)

        updated_rendered = render_month(updated)
        if updated_rendered == original_rendered:
            return False

        save_month(config, updated)
        return True
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
