from __future__ import annotations
import json, os, shutil, traceback
from pathlib import Path
from .config import AppConfig

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
    config.bootstrap_log_file.parent.mkdir(parents=True, exist_ok=True)
    with config.bootstrap_log_file.open("a", encoding="utf-8") as handle:
        handle.write(message.rstrip("\n") + "\n")

def _load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")

def detect_shell_name() -> str:
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
    return Path.home() / (".zshrc" if shell_name == "zsh" else ".bashrc")

def completion_file(shell_name: str) -> Path:
    if shell_name == "zsh":
        return Path.home() / ".zsh" / "completions" / "_todo"
    return Path.home() / ".bash_completions" / "todo.sh"

def _replace_or_append_block(path: Path, start_marker: str, end_marker: str, block: str) -> None:
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
    return "\n".join([
        SHELL_MARKER_START,
        'if [ -z "$TODOCTL_SESSION_ID" ]; then',
        '    export TODOCTL_SESSION_ID="todoctl-$$-${RANDOM:-0}"',
        "fi",
        SHELL_MARKER_END,
    ])

def bash_completion_source_block() -> str:
    return "\n".join([
        BASH_COMPLETION_SOURCE_MARKER,
        'if [ -f "$HOME/.bash_completions/todo.sh" ]; then',
        '    source "$HOME/.bash_completions/todo.sh"',
        "fi",
        BASH_COMPLETION_SOURCE_END,
    ])

def zsh_completion_source_block() -> str:
    return "\n".join([
        ZSH_COMPLETION_MARKER,
        'mkdir -p "$HOME/.zsh/completions"',
        'fpath=("$HOME/.zsh/completions" $fpath)',
        "autoload -Uz compinit",
        "compinit",
        ZSH_COMPLETION_END,
    ])

def bash_completion_content() -> str:
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
    root = Path.home() / ".vim"
    return {
        "ftdetect": root / "ftdetect" / VIM_FTDETECT,
        "syntax": root / "syntax" / VIM_SYNTAX,
        "ftplugin": root / "after" / "ftplugin" / VIM_FTPLUGIN,
    }

def vim_ftdetect_content() -> str:
    return 'augroup todoctl_filetype\n    autocmd!\n    autocmd BufRead,BufNewFile *.todo set filetype=todoctl\naugroup END\n'

def vim_syntax_content() -> str:
    return "\n".join([
        'if exists("b:current_syntax")',
        "  finish",
        "endif",
        r'syntax match todoctlHeader "^# todoctl month: .*$"',
        r'syntax match todoctlId "^\[[0-9]\+\]"',
        r'syntax match todoctlStatus "\[OPEN\]\|\[DOING\]\|\[SIDE\]\|\[DONE\]"',
        r'syntax match todoctlComment "^#.*$"',
        "highlight default link todoctlHeader Title",
        "highlight default link todoctlId Identifier",
        "highlight default link todoctlStatus Statement",
        "highlight default link todoctlComment Comment",
        'let b:current_syntax = "todoctl"',
        "",
    ])

def vim_ftplugin_content() -> str:
    return "\n".join(["setlocal nowrap", "setlocal nospell", "setlocal commentstring=#\\ %s", ""])

def install_for_shell(config: AppConfig) -> dict:
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
        for p in paths.values():
            p.parent.mkdir(parents=True, exist_ok=True)
        paths["ftdetect"].write_text(vim_ftdetect_content(), encoding="utf-8")
        paths["syntax"].write_text(vim_syntax_content(), encoding="utf-8")
        paths["ftplugin"].write_text(vim_ftplugin_content(), encoding="utf-8")
        installed_vim = True

    state = {"shell": shell_name, "rc_file": str(rc_file), "completion_file": str(comp_file), "vim_installed": installed_vim}
    _save_state(config.bootstrap_state_file, state)
    return state

def uninstall_integrations(config: AppConfig) -> dict:
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
    try:
        state = install_for_shell(config)
        _log(config, f"bootstrap ok: shell={state['shell']} completion={state['completion_file']}")
        return state
    except Exception:
        _log(config, "bootstrap failed")
        _log(config, traceback.format_exc())
        raise
