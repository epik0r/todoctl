"""
Configuration handling for todoctl.

This module defines default filesystem locations, the main application
configuration model, and helpers for loading and writing configuration
files. It centralizes runtime paths and user-configurable settings.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
import tomllib
from todoctl.fs_secure import write_private_text


DEFAULT_CONFIG_DIR = Path.home() / ".config" / "todoctl"
DEFAULT_DATA_DIR = Path.home() / ".local" / "share" / "todoctl"
DEFAULT_MONTHS_DIR = DEFAULT_DATA_DIR / "months"
DEFAULT_BACKUPS_DIR = DEFAULT_DATA_DIR / "backups"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.toml"
DEFAULT_CHECK_FILE = DEFAULT_DATA_DIR / "vault.check"
DEFAULT_SESSION_INDEX_FILE = DEFAULT_DATA_DIR / "session_keys.json"
DEFAULT_BOOTSTRAP_STATE = DEFAULT_DATA_DIR / "bootstrap_state.json"
DEFAULT_BOOTSTRAP_LOG = DEFAULT_DATA_DIR / "bootstrap.log"

DEFAULT_SECURITY_MODE = "standard"
VALID_SECURITY_MODES = {"standard", "hardened"}


def _expand(value: str) -> Path:
    """
    Expand and normalize a filesystem path.

    Resolves user home shortcuts (e.g. "~") and returns an absolute path.

    Args:
        value (str): Path string to expand.

    Returns:
        Path: Resolved absolute path.
    """
    return Path(value).expanduser().resolve()


def _normalize_security_mode(value: object) -> str:
    """
    Normalize and validate the configured security mode.

    Args:
        value (object): Raw security mode value from the config file.

    Returns:
        str: Valid security mode.
    """
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in VALID_SECURITY_MODES:
            return normalized
    return DEFAULT_SECURITY_MODE


def _normalize_optional_path(value: object) -> Path | None:
    """
    Normalize an optional filesystem path from configuration.

    Args:
        value (object): Raw config value.

    Returns:
        Path | None: Expanded path or None.
    """
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            return _expand(stripped)
    return None


def _toml_escape(value: str) -> str:
    """
    Escape a string for simple TOML serialization.

    Args:
        value (str): Raw string value.

    Returns:
        str: Escaped string.
    """
    return value.replace("\\", "\\\\").replace('"', '\\"')


@dataclass(slots=True)
class AppConfig:
    """
    Main application configuration model.

    Holds all configurable paths and runtime settings required by the
    application, including editor configuration, filesystem locations,
    and bootstrap/session metadata.
    """

    editor: str
    data_dir: Path
    months_dir: Path
    backups_dir: Path
    check_file: Path
    file_extension: str
    passphrase_cache_hours: int
    config_path: Path
    session_index_file: Path
    bootstrap_state_file: Path
    bootstrap_log_file: Path
    security_mode: str
    secure_temp_dir: Path | None

    @classmethod
    def default(cls) -> "AppConfig":
        """
        Create a default configuration instance.

        Uses environment variables and predefined constants to initialize
        a fully populated configuration object.

        Returns:
            AppConfig: Default configuration instance.
        """
        return cls(
            editor=os.environ.get("EDITOR", "vim") or "vim",
            data_dir=DEFAULT_DATA_DIR,
            months_dir=DEFAULT_MONTHS_DIR,
            backups_dir=DEFAULT_BACKUPS_DIR,
            check_file=DEFAULT_CHECK_FILE,
            file_extension=".todo.enc",
            passphrase_cache_hours=8,
            config_path=DEFAULT_CONFIG_PATH,
            session_index_file=DEFAULT_SESSION_INDEX_FILE,
            bootstrap_state_file=DEFAULT_BOOTSTRAP_STATE,
            bootstrap_log_file=DEFAULT_BOOTSTRAP_LOG,
            security_mode=DEFAULT_SECURITY_MODE,
            secure_temp_dir=None,
        )

    def ensure_directories(self) -> None:
        """
        Ensure that all required directories exist.

        Creates configuration and data directories if they are missing.
        This includes paths for configuration, data storage, monthly files,
        and backups.
        """
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.months_dir.mkdir(parents=True, exist_ok=True)
        self.backups_dir.mkdir(parents=True, exist_ok=True)


def load_config() -> AppConfig:
    """
    Load the application configuration from disk.

    If no configuration file exists, a default configuration is returned.
    Otherwise, values from the TOML file override the defaults.

    Returns:
        AppConfig: Loaded configuration instance.
    """
    cfg = AppConfig.default()
    if not cfg.config_path.exists():
        return cfg

    with cfg.config_path.open("rb") as handle:
        data = tomllib.load(handle)

    cfg.editor = str(data.get("editor", cfg.editor))
    cfg.data_dir = _expand(data.get("data_dir", str(cfg.data_dir)))
    cfg.months_dir = _expand(data.get("months_dir", str(cfg.months_dir)))
    cfg.backups_dir = _expand(data.get("backups_dir", str(cfg.backups_dir)))
    cfg.check_file = _expand(data.get("check_file", str(cfg.check_file)))
    cfg.file_extension = str(data.get("file_extension", cfg.file_extension))
    cfg.passphrase_cache_hours = int(data.get("passphrase_cache_hours", cfg.passphrase_cache_hours))
    cfg.session_index_file = _expand(data.get("session_index_file", str(cfg.session_index_file)))
    cfg.bootstrap_state_file = _expand(data.get("bootstrap_state_file", str(cfg.bootstrap_state_file)))
    cfg.bootstrap_log_file = _expand(data.get("bootstrap_log_file", str(cfg.bootstrap_log_file)))
    cfg.security_mode = _normalize_security_mode(data.get("security_mode", cfg.security_mode))
    cfg.secure_temp_dir = _normalize_optional_path(data.get("secure_temp_dir"))

    return cfg


def write_default_config(config: AppConfig) -> Path:
    """
    Write the current configuration to disk as a TOML file.

    Ensures the configuration directory exists and serializes the
    configuration fields into a TOML-compatible format.

    Args:
        config (AppConfig): Configuration instance to write.

    Returns:
        Path: Path to the written configuration file.
    """
    config.config_path.parent.mkdir(parents=True, exist_ok=True)

    secure_temp_dir = ""
    if config.secure_temp_dir is not None:
        secure_temp_dir = str(config.secure_temp_dir)

    content = (
        f'editor = "{_toml_escape(config.editor)}"\n'
        f'data_dir = "{_toml_escape(str(config.data_dir))}"\n'
        f'months_dir = "{_toml_escape(str(config.months_dir))}"\n'
        f'backups_dir = "{_toml_escape(str(config.backups_dir))}"\n'
        f'check_file = "{_toml_escape(str(config.check_file))}"\n'
        f'file_extension = "{_toml_escape(config.file_extension)}"\n'
        f'passphrase_cache_hours = {config.passphrase_cache_hours}\n'
        f'session_index_file = "{_toml_escape(str(config.session_index_file))}"\n'
        f'bootstrap_state_file = "{_toml_escape(str(config.bootstrap_state_file))}"\n'
        f'bootstrap_log_file = "{_toml_escape(str(config.bootstrap_log_file))}"\n'
        f'security_mode = "{_toml_escape(config.security_mode)}"\n'
        f'secure_temp_dir = "{_toml_escape(secure_temp_dir)}"\n'
    )
    write_private_text(config.config_path, content, encoding="utf-8")
    return config.config_path
