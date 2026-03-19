"""
Backup creation utilities for todoctl.

This module is responsible for exporting encrypted todo data into
a compressed archive. It collects month files, the password check
file, and a checksum manifest so backups can be stored or moved
safely without exposing plaintext task data.
"""
from __future__ import annotations
import hashlib, json, tarfile
from datetime import datetime
from pathlib import Path
from .config import AppConfig

def create_backup(config: AppConfig, output: Path | None = None) -> Path:
    """
    Create a compressed backup archive of encrypted todo data.

    This function collects all relevant application data, including:
    - the password check file (`vault.check`) if present
    - all encrypted monthly todo files
    - a generated manifest containing SHA256 checksums for integrity verification

    The data is packaged into a `.tar.gz` archive. A temporary manifest file
    is created during the process and removed afterward.

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
    with tarfile.open(target, "w:gz") as tar:
        if config.check_file.exists():
            tar.add(config.check_file, arcname="vault.check")
            manifest["vault.check"] = hashlib.sha256(config.check_file.read_bytes()).hexdigest()
        for path in sorted(config.months_dir.glob(f"*{config.file_extension}")):
            arcname = f"months/{path.name}"
            tar.add(path, arcname=arcname)
            manifest[arcname] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
        manifest_path = config.backups_dir / ".manifest.json"
        manifest_path.write_bytes(manifest_bytes)
        tar.add(manifest_path, arcname="manifest.json")
        manifest_path.unlink(missing_ok=True)
    return target
