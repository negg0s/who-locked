from datetime import datetime
import json
import sys
import time
from typing import Optional
import click

from .context_menu import install_context_menu, is_context_menu_installed, uninstall_context_menu
from .core import inspect_locks, release_locks, scan_directory_tree, wait_for_release, watch_lock_events
from .doctor import run_diagnostics
from .models import LockReport, TreeReport


def format_report_text(report: LockReport, verbose: bool = False, color: bool = True) -> str:
    lines = []
    lines.append(f"Target: {report.target_path}")
    type_label = "Directory" if report.is_directory else "File"
    lines.append(f"Type:   {type_label}")

    if report.error:
        err_msg = click.style(f"ERROR ({report.error})", fg="red", bold=True) if color else f"ERROR ({report.error})"
        lines.append(f"Status: {err_msg}")
        return "\n".join(lines)

    if not report.is_locked:
        status_msg = click.style("FREE (no active locks detected)", fg="green", bold=True) if color else "FREE (no active locks detected)"
        lines.append(f"Status: {status_msg}")
        return "\n".join(lines)

    count = len(report.locking_processes)
    status_msg = click.style(f"LOCKED by {count} process(es)", fg="red", bold=True) if color else f"LOCKED by {count} process(es)"
    lines.append(f"Status: {status_msg}\n")

    header = f"{'PID':<8} {'NAME':<24} {'TYPE':<14} {'MEMORY':<12} {'USER'}"
    lines.append(click.style(header, bold=True) if color else header)
    lines.append("-" * 75)

    for proc in report.locking_processes:
        mem_str = f"{proc.memory_mb:.1f} MB" if proc.memory_mb is not None else "-"
        user_str = proc.username or "-"
        pid_str = click.style(f"{proc.pid:<8}", fg="cyan") if color else f"{proc.pid:<8}"
        lines.append(f"{pid_str} {proc.name[:23]:<24} {proc.app_type:<14} {mem_str:<12} {user_str}")
        if verbose:
            if proc.exe_path:
                lines.append(f"         Path:   {proc.exe_path}")
            if proc.parent_pid:
                p_name = proc.parent_name or "Unknown"
                lines.append(f"         Parent: {p_name} (PID {proc.parent_pid})")
            if proc.cmdline:
                lines.append(f"         Cmd:    {proc.cmdline}")

    if verbose and report.queried_paths:
        lines.append(f"\nQueried resources: {len(report.queried_paths)} file(s)/handle(s)")

    return "\n".join(lines)


def format_tree_text(report: TreeReport, color: bool = True) -> str:
    lines = []
    lines.append(f"Root:    {report.root_path}")
    lines.append(f"Scanned: {report.scanned_files_count} file(s)")

    if report.error:
        err_msg = click.style(f"ERROR ({report.error})", fg="red") if color else f"ERROR ({report.error})"
        lines.append(f"Status:  {err_msg}")
        return "\n".join(lines)

    if not report.is_locked:
        status_msg = click.style("CLEAN (no locked files in tree)", fg="green", bold=True) if color else "CLEAN (no locked files in tree)"
        lines.append(f"Status:  {status_msg}")
        return "\n".join(lines)

    count_str = click.style(f"Found {len(report.locked_entries)} locked item(s):", fg="red", bold=True) if color else f"Found {len(report.locked_entries)} locked item(s):"
    lines.append(f"\n{count_str}\n")

    for entry in report.locked_entries:
        rel_label = entry.relative_path
        lines.append(f"  * {click.style(rel_label, bold=True) if color else rel_label}")
        for p in entry.locking_processes:
            mem_str = f", {p.memory_mb:.1f} MB" if p.memory_mb is not None else ""
            parent_str = f", parent: {p.parent_name}" if p.parent_name else ""
            p_line = f"      -> PID {p.pid} ({p.name}, {p.app_type}{mem_str}{parent_str})"
            lines.append(click.style(p_line, fg="yellow") if color else p_line)

    return "\n".join(lines)


@click.group()
@click.version_option()
def cli() -> None:
    """Fast Windows file lock inspector and release tool."""
    pass


@cli.command("inspect")
@click.argument("path", type=click.Path())
@click.option("--format", "output_format", type=click.Choice(["text", "json", "pids", "csv"]), default="text", show_default=True, help="Output format.")
@click.option("--json", "json_flag", is_flag=True, help="Shortcut for --format json.")
@click.option("-v", "--verbose", is_flag=True, help="Show executable paths, parents, and arguments.")
@click.option("--no-color", is_flag=True, help="Disable ANSI colors.")
@click.option("--max-files", default=100, show_default=True, help="Max files to scan inside directory.")
def inspect_cmd(path: str, output_format: str, json_flag: bool, verbose: bool, no_color: bool, max_files: int = 100) -> None:
    """Inspect active locks holding a file or directory."""
    if json_flag:
        output_format = "json"

    report = inspect_locks(path, max_dir_files=max_files)

    if output_format == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
    elif output_format == "pids":
        pids = [str(p.pid) for p in report.locking_processes]
        if pids:
            click.echo(" ".join(pids))
    elif output_format == "csv":
        click.echo("pid,name,type,status,memory_mb,username")
        for p in report.locking_processes:
            mem = f"{p.memory_mb:.1f}" if p.memory_mb is not None else ""
            click.echo(f'{p.pid},"{p.name}","{p.app_type}","{p.app_status}",{mem},"{p.username or ""}"')
    else:
        click.echo(format_report_text(report, verbose=verbose, color=not no_color))

    if report.error:
        sys.exit(2)
    elif report.is_locked:
        sys.exit(1)
    else:
        sys.exit(0)


@cli.command("tree")
@click.argument("path", type=click.Path())
@click.option("--max-files", default=1000, show_default=True, help="Maximum files to scan.")
@click.option("--json", "json_mode", is_flag=True, help="Output machine-readable JSON.")
@click.option("--no-color", is_flag=True, help="Disable ANSI colors.")
def tree_cmd(path: str, max_files: int, json_mode: bool, no_color: bool) -> None:
    """Scan a directory tree and list every individual locked file."""
    report = scan_directory_tree(path, max_files=max_files)
    if json_mode:
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        click.echo(format_tree_text(report, color=not no_color))

    if report.error:
        sys.exit(2)
    elif report.is_locked:
        sys.exit(1)
    else:
        sys.exit(0)


@cli.command("watch")
@click.argument("path", type=click.Path())
@click.option("-i", "--interval", default=0.5, show_default=True, help="Polling interval in seconds.")
@click.option("--exit-on-free", is_flag=True, help="Exit when target is confirmed free.")
@click.option("--exit-on-lock", is_flag=True, help="Exit when a lock is first detected.")
@click.option("--beep", is_flag=True, help="Sound console bell on lock change.")
@click.option("--no-color", is_flag=True, help="Disable ANSI colors.")
def watch_cmd(path: str, interval: float, exit_on_free: bool, exit_on_lock: bool, beep: bool, no_color: bool) -> None:
    """Monitor a file or folder in real time for lock state changes."""
    click.echo(f"Watching {path} for lock changes (interval: {interval}s, press Ctrl+C to stop)...")

    try:
        for event_data in watch_lock_events(path, interval=interval):
            event = event_data["event"]
            ts_str = datetime.fromtimestamp(event_data["timestamp"]).strftime("%H:%M:%S.%f")[:-3]
            report: LockReport = event_data["report"]

            if beep:
                sys.stdout.write("\a")
                sys.stdout.flush()

            if event in ("INITIAL_LOCKED", "LOCK_ACQUIRED"):
                p_names = ", ".join(f"{p.name} (PID {p.pid})" for p in report.locking_processes)
                tag = click.style("[LOCKED]", fg="red", bold=True) if not no_color else "[LOCKED]"
                click.echo(f"[{ts_str}] {tag} Locked by: {p_names}")
                if exit_on_lock:
                    sys.exit(1)
            elif event in ("INITIAL_FREE", "LOCK_RELEASED"):
                tag = click.style("[FREE]  ", fg="green", bold=True) if not no_color else "[FREE]  "
                dur_str = f" after {event_data['duration_sec']}s" if event_data["duration_sec"] > 0 else ""
                click.echo(f"[{ts_str}] {tag} Target is free{dur_str}")
                if exit_on_free:
                    sys.exit(0)
    except KeyboardInterrupt:
        click.echo("\nStopped monitoring.")
        sys.exit(0)


@cli.command("release")
@click.argument("path", type=click.Path())
@click.option("-f", "--force", is_flag=True, help="Force kill processes if graceful close fails.")
@click.option("-t", "--timeout", default=3.0, show_default=True, help="Timeout in seconds for termination.")
@click.option("-y", "--yes", is_flag=True, help="Bypass confirmation prompt.")
@click.option("--json", "json_mode", is_flag=True, help="Output machine-readable JSON.")
def release_cmd(path: str, force: bool, timeout: float, yes: bool, json_mode: bool) -> None:
    """Terminate processes holding locks on the target path."""
    report = inspect_locks(path)
    if not report.is_locked:
        if json_mode:
            click.echo(json.dumps({"target": path, "was_locked": False, "success": True}))
        else:
            click.echo(f"No active locks found on {path}.")
        sys.exit(0)

    if not yes and not json_mode:
        click.echo(format_report_text(report))
        click.echo()
        if not click.confirm("Do you want to terminate these processes?"):
            click.echo("Aborted.")
            sys.exit(1)

    result = release_locks(path, force=force, timeout=timeout)
    if json_mode:
        click.echo(json.dumps(result, indent=2))
    else:
        for item in result["results"]:
            status = "OK" if item["success"] else "FAILED"
            click.echo(f"[{status}] {item['message']}")

        if result["success"]:
            click.echo("\nAll locks cleared.")
            sys.exit(0)
        else:
            click.echo(f"\nWarning: {result['remaining_locks']} lock(s) still remain.")
            sys.exit(1)


@cli.command("wait")
@click.argument("path", type=click.Path())
@click.option("-t", "--timeout", default=10.0, show_default=True, help="Max seconds to wait.")
@click.option("-i", "--interval", default=0.25, show_default=True, help="Poll interval in seconds.")
def wait_cmd(path: str, timeout: float, interval: float) -> None:
    """Poll until the target is freed or timeout expires."""
    click.echo(f"Waiting for {path} to be freed (timeout: {timeout}s)...")
    freed = wait_for_release(path, timeout=timeout, interval=interval)
    if freed:
        click.echo("Target is now free.")
        sys.exit(0)
    else:
        click.echo("Timeout expired while waiting for target to be freed.", err=True)
        sys.exit(1)


@cli.group("menu")
def menu_group() -> None:
    """Manage Windows Explorer context menu integration."""
    pass


@menu_group.command("install")
def menu_install_cmd() -> None:
    """Add 'Who is locking this?' to Explorer right-click menu."""
    success, message = install_context_menu()
    click.echo(message)
    sys.exit(0 if success else 1)


@menu_group.command("uninstall")
def menu_uninstall_cmd() -> None:
    """Remove 'Who is locking this?' from Explorer right-click menu."""
    success, message = uninstall_context_menu()
    click.echo(message)
    sys.exit(0 if success else 1)


@menu_group.command("status")
def menu_status_cmd() -> None:
    """Check Explorer context menu integration status."""
    installed = is_context_menu_installed()
    if installed:
        click.echo("Explorer context menu item: INSTALLED")
    else:
        click.echo("Explorer context menu item: NOT INSTALLED")


@cli.command("doctor")
@click.option("--json", "json_mode", is_flag=True, help="Output machine-readable JSON.")
def doctor_cmd(json_mode: bool) -> None:
    """Check environment, Windows Restart Manager, and permissions."""
    data = run_diagnostics()
    if json_mode:
        click.echo(json.dumps(data, indent=2))
        sys.exit(0 if data["ready"] else 1)

    click.echo("Environment Diagnostics:")
    for key, item in data["checks"].items():
        tag = "[OK]  " if item["ok"] else "[FAIL]"
        click.echo(f"  {tag} {item['name']:<28} {item['details']}")

    click.echo()
    if data["ready"]:
        click.echo("System is ready for lock inspection.")
        sys.exit(0)
    else:
        click.echo("System does not satisfy requirements (Windows Restart Manager is required).", err=True)
        sys.exit(1)
