"""
Backup creation utilities for todoctl.

This module is responsible for exporting encrypted todo data into
a compressed archive. It collects month files, the password check
file, and a checksum manifest so backups can be stored or moved
safely without exposing plaintext task data.
"""
from __future__ import annotations

import hashlib
import io
import json
import tarfile
from datetime import datetime
from pathlib import Path

from .config import AppConfig


def _build_sanitized_tarinfo(arcname: str, data: bytes, mode: int = 0o600) -> tarfile.TarInfo:
    """
    Create a sanitized tar entry without leaking local account metadata.

    The resulting TarInfo contains only the relative archive name, file size,
    and a minimal permission mode. User- and group-related metadata are reset
    so backup archives do not disclose local system information.
    """
    info = tarfile.TarInfo(name=arcname)
    info.size = len(data)
    info.mode = mode
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    return info


def _add_bytes_to_tar(tar: tarfile.TarFile, arcname: str, data: bytes, mode: int = 0o600) -> None:
    """
    Add a file to the tar archive from in-memory bytes using sanitized metadata.
    """
    info = _build_sanitized_tarinfo(arcname=arcname, data=data, mode=mode)
    tar.addfile(info, io.BytesIO(data))


def _add_file_to_tar(tar: tarfile.TarFile, source: Path, arcname: str, mode: int = 0o600) -> str:
    """
    Read a file from disk and add it to the tar archive with sanitized metadata.

    Returns:
        str: SHA256 checksum of the file contents.
    """
    data = source.read_bytes()
    _add_bytes_to_tar(tar=tar, arcname=arcname, data=data, mode=mode)
    return hashlib.sha256(data).hexdigest()


def create_backup(config: AppConfig, output: Path | None = None) -> Path:
    """
    Create a compressed backup archive of encrypted todo data.

    This function collects all relevant application data, including:
    - the password check file (`vault.check`) if present
    - all encrypted monthly todo files
    - a generated manifest containing SHA256 checksums for integrity verification

    The data is packaged into a `.tar.gz` archive.

    Args:
        config (AppConfig): Application configuration containing paths and settings.
        output (Path | None, optional): Optional target path for the backup archive.
            If not provided, a timestamped file will be created in the configured
            backup directory.

    Returns:
        Path: The path to the created backup archive.

    Raises:
        OSError: If file operations (reading, writing, archiving) fail.
    """
    config.ensure_directories()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = output or (config.backups_dir / f"todoctl_backup_{ts}.tar.gz")
    target.parent.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, str] = {}

    with tarfile.open(target, mode="w:gz", format=tarfile.PAX_FORMAT) as tar:
        if config.check_file.exists():
            arcname = "vault.check"
            manifest[arcname] = _add_file_to_tar(
                tar=tar,
                source=config.check_file,
                arcname=arcname,
                mode=0o600,
            )

        for path in sorted(config.months_dir.glob(f"*{config.file_extension}")):
            arcname = f"months/{path.name}"
            manifest[arcname] = _add_file_to_tar(
                tar=tar,
                source=path,
                arcname=arcname,
                mode=0o600,
            )

        manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
        _add_bytes_to_tar(
            tar=tar,
            arcname="manifest.json",
            data=manifest_bytes,
            mode=0o600,
        )

    return target
