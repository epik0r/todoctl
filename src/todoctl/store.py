"""
Persistent storage operations for todoctl.

This module manages encrypted month files, password check files, and
high-level task operations such as loading, saving, adding, updating,
and removing tasks from monthly documents.
"""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from .config import AppConfig
from .crypto import create_check_blob, decrypt_text, encrypt_text, verify_check_blob
from .models import MonthDocument, Status, Task
from .parser import parse_month
from .renderer import render_month, sort_tasks

MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


def _atomic_write_bytes(path: Path, data: bytes, mode: int = 0o600) -> None:
    """
    Atomically write bytes to a file.

    Data is written to a temporary file in the same directory, flushed to disk,
    and then atomically moved into place with os.replace(). This reduces the
    risk of partial file corruption if the process is interrupted during write.

    Args:
        path (Path): Final destination path.
        data (bytes): File content to write.
        mode (int): File mode to apply to the temporary file.

    Raises:
        OSError: If writing or replacement fails.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    tmp_path = Path(tmp_name)

    try:
        os.chmod(tmp_path, mode)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(tmp_path, path)

        try:
            dir_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass

    except Exception:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


def month_path(config: AppConfig, month: str) -> Path:
    """
    Build the filesystem path for a month document.

    Args:
        config (AppConfig): Application configuration.
        month (str): Month identifier in YYYY-MM format.

    Returns:
        Path: Path to the encrypted month file.
    """
    return config.months_dir / f"{month}.todo.enc"


def list_months(config: AppConfig) -> list[str]:
    """
    Return all available month identifiers from the configured month directory.

    The function scans the month storage directory and extracts valid
    YYYY-MM identifiers from encrypted month filenames.

    Args:
        config (AppConfig): Application configuration.

    Returns:
        list[str]: All discovered month identifiers, sorted descending.
    """
    months_dir = config.months_dir
    if not months_dir.exists():
        return []

    months: set[str] = set()

    for path in months_dir.iterdir():
        if not path.is_file():
            continue

        if path.name.endswith(".todo.enc"):
            month = path.name[:-9]
            if MONTH_RE.fullmatch(month):
                months.add(month)

    return sorted(months, reverse=True)


def init_store(config: AppConfig) -> None:
    """
    Initialize the storage structure and password check file.

    Ensures required directories exist and creates an encrypted
    password check file if it is missing.

    Args:
        config (AppConfig): Application configuration.
    """
    config.ensure_directories()
    if not config.check_file.exists():
        check_blob = create_check_blob(
            confirm_password=True,
            ttl_hours=config.passphrase_cache_hours,
            index_file=config.session_index_file,
        )
        _atomic_write_bytes(config.check_file, check_blob)


def verify_store_password(config: AppConfig) -> bool:
    """
    Verify the stored password using the check file.

    Args:
        config (AppConfig): Application configuration.

    Returns:
        bool: True if the password is valid, False otherwise.
    """
    if not config.check_file.exists():
        return False
    return verify_check_blob(
        config.check_file.read_bytes(),
        ttl_hours=config.passphrase_cache_hours,
        index_file=config.session_index_file,
    )


def load_month(config: AppConfig, month: str) -> MonthDocument:
    """
    Load and decrypt a month document.

    If the file does not exist, an empty document is returned.

    Args:
        config (AppConfig): Application configuration.
        month (str): Month identifier.

    Returns:
        MonthDocument: Loaded and parsed document.
    """
    path = month_path(config, month)
    if not path.exists():
        return MonthDocument(month=month, tasks=[])
    text = decrypt_text(
        path.read_bytes(),
        ttl_hours=config.passphrase_cache_hours,
        index_file=config.session_index_file,
    )
    doc = parse_month(text, fallback_month=month)
    return sort_tasks(doc)


def save_month(config: AppConfig, doc: MonthDocument) -> Path:
    """
    Encrypt and save a month document.

    Ensures directories exist, sorts tasks, and writes the encrypted
    representation to disk atomically.

    Args:
        config (AppConfig): Application configuration.
        doc (MonthDocument): Document to save.

    Returns:
        Path: Path to the saved file.
    """
    config.ensure_directories()
    sort_tasks(doc)
    ciphertext = encrypt_text(
        render_month(doc),
        ttl_hours=config.passphrase_cache_hours,
        index_file=config.session_index_file,
    )
    path = month_path(config, doc.month)
    _atomic_write_bytes(path, ciphertext)
    return path


def add_task(config: AppConfig, month: str, title: str) -> MonthDocument:
    """
    Add a new task to a month document.

    Creates a new task with an automatically assigned ID and OPEN status.

    Args:
        config (AppConfig): Application configuration.
        month (str): Month identifier.
        title (str): Task title.

    Returns:
        MonthDocument: Updated document.
    """
    doc = load_month(config, month)
    doc.tasks.append(Task(id=doc.next_id(), title=title, status=Status.OPEN))
    save_month(config, doc)
    return doc


def set_status(config: AppConfig, month: str, task_id: int, status: Status) -> MonthDocument:
    """
    Update the status of a task.

    Searches for a task by ID and updates its status.

    Args:
        config (AppConfig): Application configuration.
        month (str): Month identifier.
        task_id (int): ID of the task to update.
        status (Status): New status value.

    Returns:
        MonthDocument: Updated document.

    Raises:
        ValueError: If the task ID is not found.
    """
    doc = load_month(config, month)
    for task in doc.tasks:
        if task.id == task_id:
            task.status = status
            save_month(config, doc)
            return doc
    raise ValueError(f"Task ID {task_id} not found in {month}")


def remove_task(config: AppConfig, month: str, task_id: int) -> MonthDocument:
    """
    Remove a task from a month document.

    Deletes a task by ID and persists the updated document.

    Args:
        config (AppConfig): Application configuration.
        month (str): Month identifier.
        task_id (int): ID of the task to remove.

    Returns:
        MonthDocument: Updated document.

    Raises:
        ValueError: If the task ID is not found.
    """
    doc = load_month(config, month)
    before = len(doc.tasks)
    doc.tasks = [task for task in doc.tasks if task.id != task_id]
    if len(doc.tasks) == before:
        raise ValueError(f"Task ID {task_id} not found in {month}")
    save_month(config, doc)
    return doc
