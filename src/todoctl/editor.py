"""
Editor integration for todoctl.

This module provides the workflow for opening decrypted monthly todo
content in a text editor, parsing the modified file after editing,
and saving it back in encrypted form.
"""
from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
from pathlib import Path

from .config import AppConfig
from .parser import parse_month
from .renderer import render_month, sort_tasks
from .store import load_month, save_month


class SecureEditingError(RuntimeError):
    """
    Raised when hardened editing cannot use a valid secure temp directory.
    """


def _is_writable_directory(path: Path) -> bool:
    """
    Return whether a path exists and is writable as a directory.

    Args:
        path (Path): Directory path to validate.

    Returns:
        bool: True if the directory exists and is writable.
    """
    try:
        return path.is_dir() and os.access(path, os.W_OK | os.X_OK)
    except OSError:
        return False


def _best_effort_wipe(path: Path) -> None:
    """
    Best-effort overwrite of a plaintext temporary file before deletion.

    This reduces trivial recovery opportunities but does not provide
    guaranteed secure deletion on all filesystems.

    Args:
        path (Path): File path to wipe.
    """
    try:
        size = path.stat().st_size
    except OSError:
        return

    try:
        with path.open("r+b") as handle:
            if size > 0:
                handle.seek(0)
                handle.write(b"\x00" * size)
                handle.flush()
                os.fsync(handle.fileno())
    except OSError:
        pass


def _build_editor_command(editor: str, temp_path: Path, hardened: bool) -> list[str]:
    """
    Build the editor command for the temporary file.

    In hardened mode, vi and vim are started with settings that reduce
    additional persistence such as swap, backup, and viminfo files.

    Args:
        editor (str): Configured editor command.
        temp_path (Path): Temporary plaintext file path.
        hardened (bool): Whether hardened editing mode is active.

    Returns:
        list[str]: Command and arguments for subprocess execution.
    """
    parts = shlex.split(editor) if editor else ["vim"]
    if not parts:
        parts = ["vim"]

    executable = Path(parts[0]).name.lower()

    if hardened and executable in {"vi", "vim"}:
        return [
            *parts,
            "-n",
            "-i",
            "NONE",
            "-u",
            "NONE",
            "-U",
            "NONE",
            "-c",
            "set nobackup nowritebackup noswapfile viminfo= nomodeline noexrc",
            str(temp_path),
        ]

    return [*parts, str(temp_path)]


def _create_standard_tempfile(original_rendered: str) -> Path:
    """
    Create a plaintext temporary file using the standard system temp directory.

    This preserves the historical behavior of todoctl.

    Args:
        original_rendered (str): Plaintext content to write.

    Returns:
        Path: Path to the created temporary file.
    """
    with tempfile.NamedTemporaryFile(
        "w+",
        suffix=".todo",
        delete=False,
        encoding="utf-8",
    ) as handle:
        handle.write(original_rendered)
        handle.flush()
        return Path(handle.name)


def _create_hardened_tempfile(config: AppConfig, original_rendered: str) -> Path:
    """
    Create a plaintext temporary file inside the configured secure temp directory.

    Hardened mode requires a writable secure temp directory configured via
    AppConfig.secure_temp_dir. No fallback to a disk-backed temp directory
    is allowed.

    Args:
        config (AppConfig): Loaded application configuration.
        original_rendered (str): Plaintext content to write.

    Returns:
        Path: Path to the created temporary file.

    Raises:
        SecureEditingError: If no valid secure temp directory is configured.
    """
    secure_dir = config.secure_temp_dir
    if secure_dir is None:
        raise SecureEditingError(
            "Hardened editing mode is enabled, but secure_temp_dir is not configured."
        )

    if not _is_writable_directory(secure_dir):
        raise SecureEditingError(
            f"Hardened editing mode requires a writable secure_temp_dir: {secure_dir}"
        )

    fd, temp_path = tempfile.mkstemp(
        prefix="todoctl_",
        suffix=".todo",
        dir=str(secure_dir),
        text=True,
    )
    os.chmod(temp_path, 0o600)

    with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
        handle.write(original_rendered)
        handle.flush()
        os.fsync(handle.fileno())

    return Path(temp_path)


def edit_month(config: AppConfig, month: str) -> bool:
    """
    Open, edit, and optionally save a monthly todo document.

    Loads the encrypted monthly document, renders it into a temporary
    plaintext file, and opens it in the configured text editor. After
    editing, the content is parsed, normalized, and only saved back in
    encrypted form if the normalized content has changed.

    In standard mode, the historical temp file behavior is preserved.
    In hardened mode, editing requires a configured RAM-backed directory
    and vi/vim are started with reduced persistence settings.

    Args:
        config (AppConfig): Loaded application configuration.
        month (str): Target month identifier (e.g. "2026-03").

    Returns:
        bool: True if changes were saved, False if nothing changed.

    Raises:
        subprocess.CalledProcessError: If the editor exits with an error.
        SecureEditingError: If hardened mode cannot be used safely.
    """
    doc = load_month(config, month)
    original_rendered = render_month(doc)
    editor = config.editor or os.environ.get("EDITOR", "vim") or "vim"
    hardened = config.security_mode == "hardened"

    if hardened:
        temp_path = _create_hardened_tempfile(config, original_rendered)
    else:
        temp_path = _create_standard_tempfile(original_rendered)

    try:
        command = _build_editor_command(editor, temp_path, hardened)
        subprocess.run(command, check=True)

        with temp_path.open("r", encoding="utf-8") as handle:
            content = handle.read()

        updated = parse_month(content, fallback_month=month)
        sort_tasks(updated)

        updated_rendered = render_month(updated)
        if updated_rendered == original_rendered:
            return False

        save_month(config, updated)
        return True
    finally:
        if hardened:
            _best_effort_wipe(temp_path)
        try:
            temp_path.unlink()
        except OSError:
            pass
