import json
import os
import sys
from typing import Optional
import click

from .context_menu import install_context_menu, is_context_menu_installed, uninstall_context_menu
from .core import inspect_locks, release_locks, wait_for_release
from .doctor import run_diagnostics
from .models import LockReport


def format_report_text(report: LockReport, verbose: bool = False) -> str:
    lines = []
    lines.append(f"Target: {report.target_path}")
    type_label = "Directory" if report.is_directory else "File"
    lines.append(f"Type:   {type_label}")

    if report.error:
        lines.append(f"Status: ERROR ({report.error})")
        return "\n".join(lines)

    if not report.is_locked:
        lines.append("Status: FREE (no active locks detected)")
        return "\n".join(lines)

    count = len(report.locking_processes)
    lines.append(f"Status: LOCKED by {count} process(es)\n")
    lines.append(f"{'PID':<8} {'NAME':<24} {'TYPE':<14} {'MEMORY':<12} {'USER'}")
    lines.append("-" * 75)

    for proc in report.locking_processes:
        mem_str = f"{proc.memory_mb:.1f} MB" if proc.memory_mb is not None else "-"
        user_str = proc.username or "-"
        lines.append(f"{proc.pid:<8} {proc.name[:23]:<24} {proc.app_type:<14} {mem_str:<12} {user_str}")
        if verbose and proc.exe_path:
            lines.append(f"         Path: {proc.exe_path}")

    if verbose and report.queried_paths:
        lines.append(f"\nQueried resources: {len(report.queried_paths)} file(s)/handle(s)")

    return "\n".join(lines)


@click.group()
@click.version_option()
def cli() -> None:
    """Fast Windows file lock inspector and release tool."""
    pass


@cli.command("inspect")
@click.argument("path", type=click.Path())
@click.option("--json", "json_mode", is_flag=True, help="Output machine-readable JSON.")
@click.option("-v", "--verbose", is_flag=True, help="Show executable paths and details.")
@click.option("--max-files", default=100, show_default=True, help="Max files to scan inside directory.")
def inspect_cmd(path: str, json_mode: bool, verbose: bool, max_files: int = 100) -> None:
    """Inspect active locks holding a file or directory."""
    report = inspect_locks(path, max_dir_files=max_files)
    if json_mode:
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        click.echo(format_report_text(report, verbose=verbose))

    if report.error:
        sys.exit(2)
    elif report.is_locked:
        sys.exit(1)
    else:
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
