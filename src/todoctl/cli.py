"""
Command-line interface for todoctl.

This module defines the public CLI commands, user interaction flow,
error handling, and startup bootstrap behavior. It is the main entry
point for daily usage of todoctl.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .backup import create_backup
from .bootstrap import auto_bootstrap, configure_security_mode_for_init, uninstall_integrations
from .config import load_config, write_default_config
from .crypto import get_passphrase
from .doctor import collect_doctor_report
from .editor import edit_month
from .models import Status
from .resolver import resolve_month
from .shell_session_cache import clear_all_sessions, clear_current_session
from .store import (
    add_task,
    init_store,
    list_months,
    load_month,
    remove_task,
    save_month,
    set_status,
)

app = typer.Typer(help="Encrypted monthly todo manager", add_completion=False)
console = Console()


def _cfg():
    """
    Load and return the application configuration.

    Returns:
        AppConfig: The loaded todoctl application configuration.
    """
    return load_config()


def handle_error(exc: Exception) -> None:
    """
    Display an error message and terminate the CLI command with exit code 1.

    Args:
        exc (Exception): The exception or error to display.

    Raises:
        typer.Exit: Always raised with status code 1 after printing the error.
    """
    console.print(f"[red]{exc}[/red]")
    raise typer.Exit(1)


def _completion_mode() -> bool:
    """
    Check whether the CLI is running in shell completion mode.

    Returns:
        bool: True if a completion-related environment variable is present,
        otherwise False.
    """
    return any(key.endswith("_COMPLETE") for key in os.environ)


@app.command()
def init() -> None:
    """
    Initialize todoctl storage and default configuration.

    This command ensures that all required directories exist, writes the
    default configuration file, initializes the encrypted data store, and
    asks once whether hardened editing mode should be configured.

    Raises:
        typer.Exit: If initialization fails.
    """
    cfg = _cfg()
    cfg.ensure_directories()
    write_default_config(cfg)

    try:
        init_store(cfg)
        security_state = configure_security_mode_for_init(cfg)
    except Exception as exc:
        handle_error(exc)
        return

    console.print("[green]todoctl initialized.[/green]")
    console.print(f"[green]Configuration written to {cfg.config_path}[/green]")
    console.print(f"[green]Security mode: {security_state['security_mode']}[/green]")

    if security_state["secure_temp_dir"]:
        console.print(f"[green]Secure temp dir: {security_state['secure_temp_dir']}[/green]")

    if security_state["security_note"]:
        console.print(f"[yellow]{security_state['security_note']}[/yellow]")


@app.command("list")
@app.command("l")
def list_cmd(
    month: str | None = typer.Argument(None),
    all_months: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="List tasks from all available months.",
    ),
    show_done: bool = typer.Option(
        False,
        "--done",
        help="Include tasks with status DONE in the monthly list.",
    ),
) -> None:
    """
    List tasks for a given month or across all months.

    By default, monthly listing hides tasks with status DONE.
    With --done, completed tasks are included as well.
    With --all, all available month documents are loaded and printed
    regardless of task status.

    Args:
        month (str | None): Optional month identifier to display.
        all_months (bool): Whether to list tasks from all available months.
        show_done (bool): Whether to include DONE tasks in monthly output.

    Raises:
        typer.Exit: If the month data cannot be loaded.
    """
    cfg = _cfg()

    if all_months and month is not None:
        handle_error(ValueError("Please use either MONTH or --all, not both."))
        return

    if all_months:
        try:
            months = list_months(cfg)
        except Exception as exc:
            handle_error(exc)
            return

        if not months:
            console.print("[yellow]No month documents found.[/yellow]")
            return

        console.print("[bold]todoctl all months[/bold]")
        table = Table()
        table.add_column("Month")
        table.add_column("ID", justify="right")
        table.add_column("Status")
        table.add_column("Title")

        has_tasks = False
        for month_name in months:
            try:
                doc = load_month(cfg, month_name)
            except Exception as exc:
                handle_error(exc)
                return

            for task in doc.tasks:
                has_tasks = True
                table.add_row(doc.month, str(task.id), task.status.value, task.title)

        if has_tasks:
            console.print(table)
        else:
            console.print("[yellow]No tasks found in available month documents.[/yellow]")
        return

    resolved_month = resolve_month(month)
    try:
        doc = load_month(cfg, resolved_month)
    except Exception as exc:
        handle_error(exc)
        return

    console.print(f"[bold]todoctl {resolved_month}[/bold]")
    table = Table()
    table.add_column("ID", justify="right")
    table.add_column("Status")
    table.add_column("Title")

    visible_tasks = doc.tasks if show_done else [
        task for task in doc.tasks if task.status != Status.DONE
    ]

    for task in visible_tasks:
        table.add_row(str(task.id), task.status.value, task.title)

    console.print(table)


@app.command("edit")
@app.command("e")
def edit_cmd(month: str | None = typer.Argument(None)) -> None:
    """
    Open the task file for a given month in the configured editor.

    If no month is provided, the current month is resolved automatically.
    The command ensures a passphrase is available before launching the editor.

    Args:
        month (str | None): Optional month identifier to edit.

    Raises:
        typer.Exit: If the editor fails or the month cannot be edited.
    """
    cfg = _cfg()
    resolved_month = resolve_month(month)
    try:
        get_passphrase(
            confirm=False,
            ttl_hours=cfg.passphrase_cache_hours,
            index_file=cfg.session_index_file,
        )
        changed = edit_month(cfg, resolved_month)
    except subprocess.CalledProcessError as exc:
        handle_error(RuntimeError(f"Editor exited with status {exc.returncode}"))
    except Exception as exc:
        handle_error(exc)
        return

    if changed:
        console.print(f"[green]Saved {resolved_month}.[/green]")


@app.command()
def add(
    title: str | None = typer.Argument(
        None,
        help="Task title. If omitted, the title is read from stdin.",
    ),
    month: str | None = typer.Option(None, "--month", "-m"),
) -> None:
    """
    Add a new task to a month.

    If no month is provided, the current month is resolved automatically.
    If no title argument is provided, the command reads the title from stdin.

    Args:
        title (str | None): Title of the new task or None.
        month (str | None): Optional month identifier to add the task to.

    Raises:
        typer.Exit: If the task cannot be added.
    """
    cfg = _cfg()
    resolved_month = resolve_month(month)

    if title is None:
        if sys.stdin.isatty():
            handle_error(ValueError("Missing task title. Pass TITLE or pipe it via stdin."))
            return
        title = sys.stdin.read().strip()

    title = title.strip()
    if not title:
        handle_error(ValueError("Task title must not be empty."))
        return

    try:
        add_task(cfg, resolved_month, title)
    except Exception as exc:
        handle_error(exc)
        return

    console.print(f"[green]Added task to {resolved_month}.[/green]")


@app.command()
def done(task_id: int, month: str | None = typer.Option(None, "--month", "-m")) -> None:
    """
    Mark a task as DONE.

    Args:
        task_id (int): Identifier of the task to update.
        month (str | None): Optional month identifier containing the task.
    """
    _set_status_cmd(task_id, Status.DONE, month)


@app.command()
def doing(task_id: int, month: str | None = typer.Option(None, "--month", "-m")) -> None:
    """
    Mark a task as DOING.

    Args:
        task_id (int): Identifier of the task to update.
        month (str | None): Optional month identifier containing the task.
    """
    _set_status_cmd(task_id, Status.DOING, month)


@app.command(name="open")
def open_cmd(task_id: int, month: str | None = typer.Option(None, "--month", "-m")) -> None:
    """
    Mark a task as OPEN.

    Args:
        task_id (int): Identifier of the task to update.
        month (str | None): Optional month identifier containing the task.
    """
    _set_status_cmd(task_id, Status.OPEN, month)


@app.command()
def side(task_id: int, month: str | None = typer.Option(None, "--month", "-m")) -> None:
    """
    Mark a task as SIDE.

    Args:
        task_id (int): Identifier of the task to update.
        month (str | None): Optional month identifier containing the task.
    """
    _set_status_cmd(task_id, Status.SIDE, month)


def _set_status_cmd(task_id: int, status: Status, month: str | None) -> None:
    """
    Update the status of a task for a given month.

    If no month is provided, the current month is resolved automatically.

    Args:
        task_id (int): Identifier of the task to update.
        status (Status): New status to assign to the task.
        month (str | None): Optional month identifier containing the task.

    Raises:
        typer.Exit: If the task status cannot be updated.
    """
    cfg = _cfg()
    resolved_month = resolve_month(month)
    try:
        set_status(cfg, resolved_month, task_id, status)
    except Exception as exc:
        handle_error(exc)
        return
    console.print(f"[green]Task {task_id} set to {status.value} in {resolved_month}.[/green]")


@app.command()
def remove(task_id: int, month: str | None = typer.Option(None, "--month", "-m")) -> None:
    """
    Remove a task from a month.

    If no month is provided, the current month is resolved automatically.

    Args:
        task_id (int): Identifier of the task to remove.
        month (str | None): Optional month identifier containing the task.

    Raises:
        typer.Exit: If the task cannot be removed.
    """
    cfg = _cfg()
    resolved_month = resolve_month(month)
    try:
        remove_task(cfg, resolved_month, task_id)
    except Exception as exc:
        handle_error(exc)
        return
    console.print(f"[green]Removed task {task_id} from {resolved_month}.[/green]")


@app.command()
def rollover(source: str, target: str) -> None:
    """
    Copy unfinished tasks from one month into another month.

    Tasks with status DONE are skipped. Tasks already present in the target
    month with the same title and status are not duplicated. New task IDs are
    assigned sequentially in the target month.

    Args:
        source (str): Source month identifier.
        target (str): Target month identifier.

    Raises:
        typer.Exit: If the rollover operation fails.
    """
    cfg = _cfg()
    src = resolve_month(source)
    dst = resolve_month(target)
    try:
        src_doc = load_month(cfg, src)
        dst_doc = load_month(cfg, dst)
        existing = {(task.title, task.status.value) for task in dst_doc.tasks}
        next_id = dst_doc.next_id()
        for task in src_doc.tasks:
            if task.status == Status.DONE:
                continue
            if (task.title, task.status.value) in existing:
                continue
            task_copy = type(task)(id=next_id, title=task.title, status=task.status)
            dst_doc.tasks.append(task_copy)
            next_id += 1
        save_month(cfg, dst_doc)
    except Exception as exc:
        handle_error(exc)
        return
    console.print(f"[green]Rolled over open tasks from {src} to {dst}.[/green]")


@app.command()
def doctor(verify_password: bool = typer.Option(False, "--verify-password")) -> None:
    """
    Run diagnostic checks and display the results.

    The command collects a doctor report and prints each check, status,
    and detail in a table.

    Args:
        verify_password (bool): Whether to verify the stored password setup.
    """
    cfg = _cfg()
    rows = collect_doctor_report(cfg, verify_password=verify_password)
    table = Table()
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Details")
    for name, status, details in rows:
        style = "green" if status == "OK" else ("yellow" if status == "WARN" else "cyan")
        table.add_row(name, f"[{style}]{status}[/{style}]", details)
    console.print(table)


@app.command()
def backup(output: Path | None = typer.Option(None, "--output", "-o")) -> None:
    """
    Create a backup archive of local todoctl data.

    Args:
        output (Path | None): Optional output path for the backup archive.

    Raises:
        typer.Exit: If backup creation fails.
    """
    cfg = _cfg()
    try:
        target = create_backup(cfg, output)
    except Exception as exc:
        handle_error(exc)
        return
    console.print(f"[green]Backup written to {target}[/green]")


@app.command()
def purge(
    yes: bool = typer.Option(False, "--yes", help="Do not ask for confirmation."),
    uninstall: bool = typer.Option(
        False,
        "--uninstall",
        help=(
            "Remove shell/vim integrations and uninstall "
            "the Python package."
        ),
    ),
) -> None:
    """
    Remove local todoctl data, configuration, and cached session information.

    By default, the command asks for confirmation before deleting data.
    Optionally, it can also remove installed shell and vim integrations and
    uninstall the todoctl Python package.

    Args:
        yes (bool): Whether to skip the confirmation prompt.
        uninstall (bool): Whether to remove integrations and uninstall todoctl.

    Raises:
        typer.Exit: If the user aborts the purge operation.
    """
    cfg = _cfg()
    if not yes:
        proceed = typer.confirm("Delete local todoctl data, config and caches?")
        if not proceed:
            console.print("Aborted.")
            raise typer.Exit(0)
    clear_current_session()
    cleared = clear_all_sessions(cfg.session_index_file)
    removed_integrations = uninstall_integrations(cfg) if uninstall else None
    if cfg.data_dir.exists():
        shutil.rmtree(cfg.data_dir, ignore_errors=True)
    if cfg.config_path.parent.exists():
        shutil.rmtree(cfg.config_path.parent, ignore_errors=True)
    console.print(
        "[green]Purged local data. "
        f"Removed {cleared} shell-session cache entry or entries.[/green]"
    )
    if uninstall and removed_integrations is not None:
        console.print(
            "[green]Removed shell completion from "
            f"{removed_integrations['completion_file']}.[/green]"
        )
        if removed_integrations["vim_removed"]:
            console.print("[green]Removed vim integration.[/green]")
        console.print("[yellow]Restart the shell after uninstall for a clean environment.[/yellow]")
        subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "todoctl"], check=False)


def main() -> None:
    """
    Run the todoctl command-line application.

    This function ensures required directories exist, performs automatic
    bootstrap setup when not running in shell completion mode, and then
    starts the Typer application.
    """
    cfg = _cfg()
    cfg.ensure_directories()
    if not _completion_mode():
        try:
            auto_bootstrap(cfg)
        except Exception as exc:
            console.print(f"[yellow]todoctl bootstrap warning: {exc}[/yellow]")
            console.print(f"[yellow]See {cfg.bootstrap_log_file} for details.[/yellow]")
    app()


if __name__ == "__main__":
    main()
