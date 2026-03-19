from __future__ import annotations
import os, shutil, subprocess, sys
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from .backup import create_backup
from .bootstrap import auto_bootstrap, uninstall_integrations
from .config import load_config, write_default_config
from .crypto import get_passphrase
from .doctor import collect_doctor_report
from .editor import edit_month
from .models import Status
from .resolver import resolve_month
from .shell_session_cache import clear_all_sessions, clear_current_session
from .store import add_task, init_store, load_month, remove_task, save_month, set_status

app = typer.Typer(help="Encrypted monthly todo manager", add_completion=False)
console = Console()

def _cfg():
    return load_config()

def handle_error(exc: Exception) -> None:
    console.print(f"[red]{exc}[/red]")
    raise typer.Exit(1)

def _completion_mode() -> bool:
    return any(key.endswith("_COMPLETE") for key in os.environ)

@app.command()
def init() -> None:
    cfg = _cfg()
    cfg.ensure_directories()
    write_default_config(cfg)
    try:
        init_store(cfg)
    except Exception as exc:
        handle_error(exc)
        return
    console.print("[green]todoctl initialized.[/green]")

@app.command()
def list(month: str | None = typer.Argument(None)) -> None:
    cfg = _cfg()
    m = resolve_month(month)
    try:
        doc = load_month(cfg, m)
    except Exception as exc:
        handle_error(exc)
        return
    console.print(f"[bold]todoctl {m}[/bold]")
    table = Table()
    table.add_column("ID", justify="right")
    table.add_column("Status")
    table.add_column("Title")
    for task in doc.tasks:
        table.add_row(str(task.id), task.status.value, task.title)
    console.print(table)

@app.command()
def edit(month: str | None = typer.Argument(None)) -> None:
    cfg = _cfg()
    m = resolve_month(month)
    try:
        get_passphrase(confirm=False, ttl_hours=cfg.passphrase_cache_hours, index_file=cfg.session_index_file)
        edit_month(cfg, m)
    except subprocess.CalledProcessError as exc:
        handle_error(RuntimeError(f"Editor exited with status {exc.returncode}"))
    except Exception as exc:
        handle_error(exc)
        return
    console.print(f"[green]Saved {m}.[/green]")

@app.command()
def add(title: str, month: str | None = typer.Option(None, "--month", "-m")) -> None:
    cfg = _cfg()
    m = resolve_month(month)
    try:
        add_task(cfg, m, title)
    except Exception as exc:
        handle_error(exc)
        return
    console.print(f"[green]Added task to {m}.[/green]")

@app.command()
def done(task_id: int, month: str | None = typer.Option(None, "--month", "-m")) -> None:
    _set_status_cmd(task_id, Status.DONE, month)

@app.command()
def doing(task_id: int, month: str | None = typer.Option(None, "--month", "-m")) -> None:
    _set_status_cmd(task_id, Status.DOING, month)

@app.command(name="open")
def open_cmd(task_id: int, month: str | None = typer.Option(None, "--month", "-m")) -> None:
    _set_status_cmd(task_id, Status.OPEN, month)

@app.command()
def side(task_id: int, month: str | None = typer.Option(None, "--month", "-m")) -> None:
    _set_status_cmd(task_id, Status.SIDE, month)

def _set_status_cmd(task_id: int, status: Status, month: str | None) -> None:
    cfg = _cfg()
    m = resolve_month(month)
    try:
        set_status(cfg, m, task_id, status)
    except Exception as exc:
        handle_error(exc)
        return
    console.print(f"[green]Task {task_id} set to {status.value} in {m}.[/green]")

@app.command()
def remove(task_id: int, month: str | None = typer.Option(None, "--month", "-m")) -> None:
    cfg = _cfg()
    m = resolve_month(month)
    try:
        remove_task(cfg, m, task_id)
    except Exception as exc:
        handle_error(exc)
        return
    console.print(f"[green]Removed task {task_id} from {m}.[/green]")

@app.command()
def rollover(source: str, target: str) -> None:
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
    uninstall: bool = typer.Option(False, "--uninstall", help="Remove shell/vim integrations and uninstall the Python package."),
) -> None:
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
    console.print(f"[green]Purged local data. Removed {cleared} shell-session cache entry or entries.[/green]")
    if uninstall and removed_integrations is not None:
        console.print(f"[green]Removed shell completion from {removed_integrations['completion_file']}.[/green]")
        if removed_integrations["vim_removed"]:
            console.print("[green]Removed vim integration.[/green]")
        console.print("[yellow]Restart the shell after uninstall for a clean environment.[/yellow]")
        subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "todoctl"], check=False)

def main() -> None:
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
