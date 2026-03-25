"""
Secure filesystem helper utilities for writing files with explicit permissions.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


def ensure_dir(path: Path) -> None:
    """
    Ensure that a directory exists.

    Parameters:
        path: Directory path to create if needed
    """
    path.mkdir(parents=True, exist_ok=True)


def ensure_private_dir(path: Path, mode: int = 0o700) -> None:
    """
    Ensure that a private directory exists and enforce restrictive permissions.

    Parameters:
        path: Directory path to create or validate
        mode: Permission mode to enforce (default: 0700)
    """
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, mode)


def write_text_atomic(path: Path, content: str, mode: int = 0o600, encoding: str = "utf-8") -> None:
    """
    Write text content to a file atomically with explicit permissions.

    Parameters:
        path: Target file path
        content: Text content to write
        mode: File permission mode
        encoding: Text encoding
    """
    ensure_dir(path.parent)

    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent))
    tmp_path = Path(tmp_name)

    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding=encoding) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(tmp_path, path)
        os.chmod(path, mode)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def write_private_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    """
    Write sensitive text data with strict permissions (0600).

    Parameters:
        path: Target file path
        content: Text content to write
        encoding: Text encoding
    """
    write_text_atomic(path, content, mode=0o600, encoding=encoding)


def write_user_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    """
    Write non-sensitive user-local text data with standard permissions (0644).

    Parameters:
        path: Target file path
        content: Text content to write
        encoding: Text encoding
    """
    write_text_atomic(path, content, mode=0o644, encoding=encoding)
