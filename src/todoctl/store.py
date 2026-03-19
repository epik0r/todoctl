"""
Persistent storage operations for todoctl.

This module manages encrypted month files, password check files, and
high-level task operations such as loading, saving, adding, updating,
and removing tasks from monthly documents.
"""
from __future__ import annotations
from pathlib import Path
from .config import AppConfig
from .crypto import create_check_blob, decrypt_text, encrypt_text, verify_check_blob
from .models import MonthDocument, Status, Task
from .parser import parse_month
from .renderer import render_month, sort_tasks

def month_path(config: AppConfig, month: str) -> Path:
    """
    Construct the filesystem path for a month document.

    Args:
        config (AppConfig): Application configuration.
        month (str): Month identifier.

    Returns:
        Path: Path to the encrypted month file.
    """
    return config.months_dir / f"{month}{config.file_extension}"

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
        config.check_file.write_bytes(create_check_blob(confirm_password=True, ttl_hours=config.passphrase_cache_hours, index_file=config.session_index_file))

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
    return verify_check_blob(config.check_file.read_bytes(), ttl_hours=config.passphrase_cache_hours, index_file=config.session_index_file)

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
    text = decrypt_text(path.read_bytes(), ttl_hours=config.passphrase_cache_hours, index_file=config.session_index_file)
    doc = parse_month(text, fallback_month=month)
    return sort_tasks(doc)

def save_month(config: AppConfig, doc: MonthDocument) -> Path:
    """
    Encrypt and save a month document.

    Ensures directories exist, sorts tasks, and writes the encrypted
    representation to disk.

    Args:
        config (AppConfig): Application configuration.
        doc (MonthDocument): Document to save.

    Returns:
        Path: Path to the saved file.
    """
    config.ensure_directories()
    sort_tasks(doc)
    ciphertext = encrypt_text(render_month(doc), ttl_hours=config.passphrase_cache_hours, index_file=config.session_index_file)
    path = month_path(config, doc.month)
    path.write_bytes(ciphertext)
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
