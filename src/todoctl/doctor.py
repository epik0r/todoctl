"""
Diagnostic reporting for todoctl.

This module collects runtime health and environment information such as
configuration status, keyring availability, shell session state, and
optional password verification. It is used by the doctor command to
help debug installation and runtime issues.
"""
from __future__ import annotations
import os
import keyring
from .config import AppConfig
from .shell_session_cache import ENV_NAME, session_id, session_status
from .store import verify_store_password


def collect_doctor_report(
    config: AppConfig,
    verify_password: bool = False
) -> list[tuple[str, str, str]]:
    """
    Collect a diagnostic report of the current application state.

    Gathers information about configuration files, data directories,
    shell session environment, keyring backend, and optional password
    verification. The result is a list of status entries suitable for
    display in the doctor command output.

    Args:
        config (AppConfig): Loaded application configuration.
        verify_password (bool): Whether to verify the stored password
            using the check file.

    Returns:
        list[tuple[str, str, str]]: A list of diagnostic rows in the form
            (component, status, details).
    """
    rows: list[tuple[str, str, str]] = []
    rows.append((
        "config file",
        "OK" if config.config_path.exists() else "WARN",
        str(config.config_path),
    ))
    rows.append((
        "data dir",
        "OK" if config.data_dir.exists() else "WARN",
        str(config.data_dir),
    ))
    rows.append((
        "months dir",
        "OK" if config.months_dir.exists() else "WARN",
        str(config.months_dir),
    ))
    rows.append((
        "check file",
        "OK" if config.check_file.exists() else "WARN",
        str(config.check_file),
    ))
    rows.append((
        "shell session id",
        "OK",
        session_id(),
    ))
    rows.append((
        "shell session env",
        "OK" if ENV_NAME in os.environ else "INFO",
        ENV_NAME,
    ))
    try:
        backend = keyring.get_keyring()
        rows.append(("keyring backend", "OK", backend.__class__.__name__))
    except Exception as exc:
        rows.append(("keyring backend", "WARN", str(exc)))
    state, details = session_status()
    rows.append(("shell-session cache", state, details))
    if verify_password:
        ok = verify_store_password(config)
        rows.append(("password verification", "OK" if ok else "WARN", "vault.check verification"))
    return rows
