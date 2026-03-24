"""
Bootstrap and integration helpers for todoctl.

This module installs and removes user-environment integrations such as
shell session initialization, shell completion, and optional vim support.
It also maintains bootstrap state and writes debug information for
troubleshooting integration issues.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import traceback
from importlib.resources import files
from pathlib import Path

from .config import AppConfig, write_default_config

SHELL_MARKER_START = "# >>> todoctl shell integration >>>"
SHELL_MARKER_END = "# <<< todoctl shell integration <<<"
BASH_COMPLETION_SOURCE_MARKER = "# >>> todoctl bash completion >>>"
BASH_COMPLETION_SOURCE_END = "# <<< todoctl bash completion <<<"
ZSH_COMPLETION_MARKER = "# >>> todoctl zsh completion >>>"
ZSH_COMPLETION_END = "# <<< todoctl zsh completion <<<"

VIM_FTDETECT = "todoctl.vim"
VIM_SYNTAX = "todoctl.vim"
VIM_FTPLUGIN = "todoctl.vim"


def _log(config: AppConfig, message: str) -> None:
    """
    Append a log message to the bootstrap log file.

    Ensures that the parent directory exists before writing.
    Each message is written on a new line with trailing newlines stripped.

    Args:
        config (AppConfig): Application configuration containing the log file path.
        message (str): The message to write to the log.
    """
    config.bootstrap_log_file.parent.mkdir(parents=True, exist_ok=True)
    with config.bootstrap_log_file.open("a", encoding="utf-8") as handle:
        handle.write(message.rstrip("\n") + "\n")


def _load_state(path: Path) -> dict:
    """
    Load the bootstrap state from a JSON file.

    If the file does not exist or cannot be parsed, an empty dictionary is returned.

    Args:
        path (Path): Path to the state file.

    Returns:
        dict: The loaded state data, or an empty dictionary on failure.
    """
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(path: Path, state: dict) -> None:
    """
    Save the bootstrap state to a JSON file.

    Ensures that the parent directory exists before writing.

    Args:
        path (Path): Path to the state file.
        state (dict): State data to persist.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


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


def _prompt_yes_no(question: str, default: bool = False) -> bool:
    """
    Ask the user a yes/no question.

    Args:
        question (str): Prompt shown to the user.
        default (bool): Default answer for empty input.

    Returns:
        bool: True for yes, False for no.
    """
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        answer = input(f"{question} {suffix} ").strip().lower()
        if not answer:
            return default
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please answer yes or no.")


def _prompt_text(question: str, default: str | None = None) -> str:
    """
    Ask the user for a text value.

    Args:
        question (str): Prompt shown to the user.
        default (str | None): Default value for empty input.

    Returns:
        str: Entered or default value.
    """
    if default:
        answer = input(f"{question} [{default}] ").strip()
        return answer or default
    return input(f"{question} ").strip()


def _configure_security_mode_interactive(config: AppConfig) -> dict[str, str]:
    """
    Interactively configure the security mode.

    This function is intended to be called only from the explicit
    initialization flow.

    Args:
        config (AppConfig): Application configuration to modify.

    Returns:
        dict[str, str]: Summary of the chosen security settings.
    """
    print()
    print("todoctl can use a higher security editing mode.")
    print("In hardened mode, decrypted editor content is only written to a RAM-backed")
    print("temporary directory. If no secure RAM-backed directory is configured,")
    print("hardened mode will refuse to edit files.")
    print()

    if not _prompt_yes_no("Enable hardened editing mode?", default=False):
        config.security_mode = "standard"
        config.secure_temp_dir = None
        write_default_config(config)
        return {
            "security_mode": config.security_mode,
            "secure_temp_dir": "",
            "security_note": "Hardened mode disabled by user.",
        }

    system = platform.system()

    if system == "Linux":
        shm_path = Path("/dev/shm")
        if _is_writable_directory(shm_path):
            print()
            print("Suggested RAM-backed directory:")
            print(f"  {shm_path}")
            print()
            if _prompt_yes_no(f"Use {shm_path} for hardened editing?", default=True):
                config.security_mode = "hardened"
                config.secure_temp_dir = shm_path
                write_default_config(config)
                return {
                    "security_mode": config.security_mode,
                    "secure_temp_dir": str(shm_path),
                    "security_note": f"Hardened mode enabled with {shm_path}.",
                }

        print()
        print("A writable /dev/shm directory was not selected or is not available.")
        print("todoctl will remain in standard mode.")
        config.security_mode = "standard"
        config.secure_temp_dir = None
        write_default_config(config)
        return {
            "security_mode": config.security_mode,
            "secure_temp_dir": "",
            "security_note": "Hardened mode not enabled because no secure RAM directory was configured.",
        }

    if system == "Darwin":
        default_mount_path = "/Volumes/todoctl-ramdisk"

        print()
        print("macOS hardened mode requires a RAM disk that you create yourself.")
        print("todoctl will not create or mount it automatically.")
        print()
        print("You can create it with:")
        print("  todo ramdisk-create")
        print()
        print("Your todoctl config file is:")
        print(f"  {config.config_path}")
        print()

        mount_path_value = _prompt_text(
            "Enter the RAM disk mount path to store in config",
            default=default_mount_path,
        )
        mount_path = Path(mount_path_value).expanduser().resolve()
        config.secure_temp_dir = mount_path

        if _is_writable_directory(mount_path):
            config.security_mode = "hardened"
            write_default_config(config)
            return {
                "security_mode": config.security_mode,
                "secure_temp_dir": str(mount_path),
                "security_note": f"Hardened mode enabled with {mount_path}.",
            }

        config.security_mode = "standard"
        write_default_config(config)

        print()
        print("The configured RAM disk path is not available or not writable yet:")
        print(f"  {mount_path}")
        print()
        print("The path was saved to your config, but todoctl remains in standard mode for now.")
        print("Create the RAM disk by running:")
        print("  todo ramdisk-create")
        print()
        print("If you want the RAM disk to be recreated automatically when a shell starts,")
        print("you can add that command to your ~/.bashrc, ~/.bash_profile, or ~/.zshrc.")
        print()
        print("After creating and mounting the RAM disk at that path, update:")
        print(f"  {config.config_path}")
        print()
        print('Set this value:')
        print('  security_mode = "hardened"')
        print()

        return {
            "security_mode": config.security_mode,
            "secure_temp_dir": str(mount_path),
            "security_note": (
                "macOS RAM disk path was saved, but hardened mode was not enabled "
                "because the path is not currently writable."
            ),
        }

    print()
    print(f"Automatic hardened mode setup is not supported on platform: {system}")
    print("todoctl will remain in standard mode.")
    print()

    config.security_mode = "standard"
    config.secure_temp_dir = None
    write_default_config(config)
    return {
        "security_mode": config.security_mode,
        "secure_temp_dir": "",
        "security_note": f"Hardened mode not enabled on unsupported platform: {system}.",
    }


def configure_security_mode_for_init(config: AppConfig) -> dict[str, str]:
    """
    Configure security mode during explicit initialization.

    Args:
        config (AppConfig): Application configuration.

    Returns:
        dict[str, str]: Summary of the chosen security settings.
    """
    return _configure_security_mode_interactive(config)


def detect_shell_name() -> str:
    """
    Detect the current user's shell name.

    Attempts to determine the shell from the parent process. If that fails,
    falls back to the SHELL environment variable. Defaults to "bash" if
    detection is unsuccessful.

    Returns:
        str: The detected shell name ("bash" or "zsh").
    """
    try:
        import subprocess

        parent = subprocess.check_output(
            ["ps", "-p", str(os.getppid()), "-o", "comm="],
            text=True,
        ).strip()
        name = Path(parent).name.lstrip("-")
        if name in {"bash", "zsh"}:
            return name
    except Exception:
        pass

    shell = os.environ.get("SHELL", "").strip()
    name = Path(shell).name
    if name in {"bash", "zsh"}:
        return name

    return "bash"


def shell_rc_file(shell_name: str) -> Path:
    """
    Get the shell configuration (rc) file path for a given shell.

    Args:
        shell_name (str): The shell name ("bash" or "zsh").

    Returns:
        Path: Path to the corresponding rc file.
    """
    return Path.home() / (".zshrc" if shell_name == "zsh" else ".bashrc")


def completion_file(shell_name: str) -> Path:
    """
    Get the completion script file path for a given shell.

    Args:
        shell_name (str): The shell name ("bash" or "zsh").

    Returns:
        Path: Path to the shell completion file.
    """
    if shell_name == "zsh":
        return Path.home() / ".zsh" / "completions" / "_todo"
    return Path.home() / ".bash_completions" / "todo.sh"


def _replace_or_append_block(path: Path, start_marker: str, end_marker: str, block: str) -> None:
    """
    Replace or append a marked block of text in a file.

    If the markers already exist, the block between them is replaced.
    Otherwise, the block is appended to the file.

    Args:
        path (Path): Target file path.
        start_marker (str): Marker indicating the start of the block.
        end_marker (str): Marker indicating the end of the block.
        block (str): The content block to insert.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if start_marker in existing and end_marker in existing:
        before = existing.split(start_marker)[0].rstrip("\n")
        after = existing.split(end_marker, 1)[1].lstrip("\n")
        content = before
        if content:
            content += "\n\n"
        content += block.rstrip("\n")
        if after:
            content += "\n\n" + after.rstrip("\n")
        content += "\n"
    else:
        content = existing.rstrip("\n")
        if content:
            content += "\n\n"
        content += block.rstrip("\n") + "\n"
    path.write_text(content, encoding="utf-8")


def _remove_block(path: Path, start_marker: str, end_marker: str) -> None:
    """
    Remove a marked block of text from a file.

    If the markers are not present, the file remains unchanged.

    Args:
        path (Path): Target file path.
        start_marker (str): Marker indicating the start of the block.
        end_marker (str): Marker indicating the end of the block.
    """
    if not path.exists():
        return
    content = path.read_text(encoding="utf-8")
    if start_marker not in content or end_marker not in content:
        return
    before = content.split(start_marker)[0].rstrip("\n")
    after = content.split(end_marker, 1)[1].lstrip("\n")
    new_content = before
    if before and after:
        new_content += "\n\n" + after
    elif after:
        new_content = after
    if new_content:
        new_content += "\n"
    path.write_text(new_content, encoding="utf-8")


def shell_integration_block() -> str:
    """
    Generate the shell integration block.

    This block initializes a session-specific environment variable
    for todoctl if not already set.

    Returns:
        str: Shell script block for integration.
    """
    return "\n".join([
        SHELL_MARKER_START,
        'if [ -z "$TODOCTL_SESSION_ID" ]; then',
        '    export TODOCTL_SESSION_ID="todoctl-$$-${RANDOM:-0}"',
        "fi",
        SHELL_MARKER_END,
    ])


def bash_completion_source_block() -> str:
    """
    Generate the bash completion source block.

    Returns:
        str: Shell script block to source the bash completion file.
    """
    return "\n".join([
        BASH_COMPLETION_SOURCE_MARKER,
        'if [ -f "$HOME/.bash_completions/todo.sh" ]; then',
        '    source "$HOME/.bash_completions/todo.sh"',
        "fi",
        BASH_COMPLETION_SOURCE_END,
    ])


def zsh_completion_source_block() -> str:
    """
    Generate the zsh completion initialization block.

    Returns:
        str: Shell script block to configure zsh completions.
    """
    return "\n".join([
        ZSH_COMPLETION_MARKER,
        'mkdir -p "$HOME/.zsh/completions"',
        'fpath=("$HOME/.zsh/completions" $fpath)',
        "autoload -Uz compinit",
        "compinit",
        ZSH_COMPLETION_END,
    ])


def bash_completion_content() -> str:
    """
    Generate the bash completion script content for todoctl.

    Returns:
        str: Bash completion function and registration.
    """
    return "\n".join([
        "_todo_completion() {",
        "    local IFS=$'\\n'",
        "    local response",
        "    local item",
        "    COMPREPLY=()",
        "",
        "    response=$( env COMP_WORDS=\"${COMP_WORDS[*]}\" \\",
        "        COMP_CWORD=$COMP_CWORD \\",
        "        _TODO_COMPLETE=complete_bash \"$1\" )",
        "",
        "    for item in $response; do",
        '        COMPREPLY+=( "${item#*,}" )',
        "    done",
        "",
        "    return 0",
        "}",
        "",
        "complete -o default -F _todo_completion todo",
        "",
    ])


def zsh_completion_content() -> str:
    """
    Generate the zsh completion script content for todoctl.

    Returns:
        str: Zsh-compatible completion function and registration.
    """
    return "\n".join([
        "autoload -U +X bashcompinit && bashcompinit",
        "_todo_completion() {",
        "    local IFS=$'\\n'",
        "    local response",
        "    local item",
        "    COMPREPLY=()",
        "",
        "    response=$( env COMP_WORDS=\"${words[*]}\" \\",
        "        COMP_CWORD=$((CURRENT-1)) \\",
        "        _TODO_COMPLETE=complete_bash todo )",
        "",
        "    for item in $response; do",
        '        COMPREPLY+=( "${item#*,}" )',
        "    done",
        "}",
        "",
        "complete -o default -F _todo_completion todo",
        "",
    ])


def vim_paths() -> dict[str, Path]:
    """
    Get the file paths for vim integration components.

    Returns:
        dict[str, Path]: Paths for ftdetect, syntax, and ftplugin files.
    """
    root = Path.home() / ".vim"
    return {
        "ftdetect": root / "ftdetect" / VIM_FTDETECT,
        "syntax": root / "syntax" / VIM_SYNTAX,
        "ftplugin": root / "ftplugin" / VIM_FTPLUGIN,
    }


def _bundled_vim_content(relative_path: str) -> str:
    """
    Load bundled vim integration content from package resources.

    Args:
        relative_path (str): Relative path below src/todoctl/vim.

    Returns:
        str: File content.
    """
    return files("todoctl").joinpath("vim", *relative_path.split("/")).read_text(encoding="utf-8")


def install_for_shell(config: AppConfig, update_vim: bool = True) -> dict:
    """
    Install shell and editor integrations for todoctl.

    Configures shell rc files with environment initialization and completion setup,
    installs completion scripts, and optionally installs vim integration files
    if vim or vi is available.

    The installation state is persisted for later removal.

    Args:
        config (AppConfig): Application configuration.
        update_vim (bool): Whether vim integration files should be written or updated.

    Returns:
        dict: Information about the installed components, including shell type,
              rc file path, completion file path, and vim installation status.
    """
    shell_name = detect_shell_name()
    rc_file = shell_rc_file(shell_name)
    comp_file = completion_file(shell_name)

    _replace_or_append_block(rc_file, SHELL_MARKER_START, SHELL_MARKER_END, shell_integration_block())

    if shell_name == "zsh":
        _replace_or_append_block(rc_file, ZSH_COMPLETION_MARKER, ZSH_COMPLETION_END, zsh_completion_source_block())
        comp_file.parent.mkdir(parents=True, exist_ok=True)
        comp_file.write_text(zsh_completion_content(), encoding="utf-8")
    else:
        _replace_or_append_block(rc_file, BASH_COMPLETION_SOURCE_MARKER, BASH_COMPLETION_SOURCE_END, bash_completion_source_block())
        comp_file.parent.mkdir(parents=True, exist_ok=True)
        comp_file.write_text(bash_completion_content(), encoding="utf-8")

    vim_installed = shutil.which("vim") is not None or shutil.which("vi") is not None
    installed_vim = False
    if vim_installed:
        paths = vim_paths()
        bundled = {
            "ftdetect": _bundled_vim_content("ftdetect/todoctl.vim"),
            "syntax": _bundled_vim_content("syntax/todoctl.vim"),
            "ftplugin": _bundled_vim_content("ftplugin/todoctl.vim"),
        }

        for path in paths.values():
            path.parent.mkdir(parents=True, exist_ok=True)

        for key, path in paths.items():
            if update_vim or not path.exists():
                path.write_text(bundled[key], encoding="utf-8")

        installed_vim = True

    state = {
        "shell": shell_name,
        "rc_file": str(rc_file),
        "completion_file": str(comp_file),
        "vim_installed": installed_vim,
    }
    _save_state(config.bootstrap_state_file, state)
    return state


def uninstall_integrations(config: AppConfig) -> dict:
    """
    Remove previously installed shell and editor integrations.

    Uses stored bootstrap state if available, otherwise falls back to
    detected defaults. Removes shell blocks, completion files, and vim
    integration files.

    Args:
        config (AppConfig): Application configuration.

    Returns:
        dict: Information about removed components.
    """
    state = _load_state(config.bootstrap_state_file)
    shell_name = state.get("shell", detect_shell_name())
    rc_file = Path(state.get("rc_file", str(shell_rc_file(shell_name))))
    comp_file = Path(state.get("completion_file", str(completion_file(shell_name))))

    _remove_block(rc_file, SHELL_MARKER_START, SHELL_MARKER_END)
    _remove_block(rc_file, BASH_COMPLETION_SOURCE_MARKER, BASH_COMPLETION_SOURCE_END)
    _remove_block(rc_file, ZSH_COMPLETION_MARKER, ZSH_COMPLETION_END)

    removed = {"rc_file": str(rc_file), "completion_file": str(comp_file), "vim_removed": False}
    if comp_file.exists():
        comp_file.unlink()

    paths = vim_paths()
    any_vim = False
    for path in paths.values():
        if path.exists():
            path.unlink()
            any_vim = True
    removed["vim_removed"] = any_vim

    if config.bootstrap_state_file.exists():
        config.bootstrap_state_file.unlink()
    return removed


def auto_bootstrap(config: AppConfig) -> dict:
    """
    Automatically perform bootstrap installation with logging.

    Calls the installation routine and logs success or failure.
    In case of an exception, the error is logged and re-raised.

    Args:
        config (AppConfig): Application configuration.

    Returns:
        dict: Installation state returned by the bootstrap process.

    Raises:
        Exception: Re-raises any exception encountered during installation.
    """
    try:
        state = install_for_shell(config, update_vim=False)
        _log(config, f"bootstrap ok: shell={state['shell']} completion={state['completion_file']}")
        return state
    except Exception:
        _log(config, "bootstrap failed")
        _log(config, traceback.format_exc())
        raise
