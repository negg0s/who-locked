import os
import sys
import time
from typing import List, Optional

from .core import inspect_locks, scan_directory_tree
from .models import LockingProcess
from .process_ops import terminate_pid


def _read_key() -> str:
    """Read a single keypress or escape sequence on Windows."""
    if sys.platform != "win32":
        return "q"

    import msvcrt

    ch = msvcrt.getch()
    if ch in (b"\x00", b"\xe0"):  # Special keys prefix
        ch2 = msvcrt.getch()
        if ch2 == b"H":
            return "UP"
        elif ch2 == b"P":
            return "DOWN"
        elif ch2 == b"S":
            return "DELETE"
        return "SPECIAL"
    elif ch == b"\x1b":  # ESC
        return "ESC"
    elif ch in (b"\r", b"\n"):
        return "ENTER"
    try:
        return ch.decode("utf-8", errors="ignore").lower()
    except Exception:
        return ""


def run_tui(target_path: str) -> None:
    """Run interactive terminal UI to inspect and manage locks."""
    abs_path = os.path.abspath(target_path)
    if not os.path.exists(abs_path):
        print(f"Error: Path '{abs_path}' does not exist.")
        return

    is_dir = os.path.isdir(abs_path)
    status_msg = "Ready. Use Up/Down to navigate, [x] to terminate process, [r] to refresh, [q] to quit."
    selected_idx = 0

    # Enter alternate buffer
    sys.stdout.write("\033[?1049h\033[H")
    sys.stdout.flush()

    try:
        while True:
            # Refresh data
            procs: List[LockingProcess] = []
            if is_dir:
                report = scan_directory_tree(abs_path, max_files=1000)
                seen_pids = set()
                for entry in report.locked_entries:
                    for p in entry.locking_processes:
                        if p.pid not in seen_pids:
                            seen_pids.add(p.pid)
                            procs.append(p)
            else:
                rep = inspect_locks(abs_path)
                procs = rep.locking_processes

            if selected_idx >= len(procs):
                selected_idx = max(0, len(procs) - 1)

            # Render screen
            lines = []
            lines.append(f"\033[1;36mWHO-LOCKED TUI\033[0m | Target: \033[1m{abs_path}\033[0m")
            lines.append("=" * 78)

            if not procs:
                lines.append("\033[1;32m[FREE] No active locking processes detected.\033[0m")
            else:
                lines.append(f"Active locking processes: {len(procs)}\n")
                lines.append(f"    {'PID':<8} {'NAME':<24} {'TYPE':<14} {'MEMORY':<12} {'USER'}")
                lines.append("-" * 78)

                for i, p in enumerate(procs):
                    prefix = "-> " if i == selected_idx else "   "
                    mem = f"{p.memory_mb:.1f} MB" if p.memory_mb is not None else "-"
                    row = f"{prefix}{p.pid:<8} {p.name[:23]:<24} {p.app_type:<14} {mem:<12} {p.username or '-'}"
                    if i == selected_idx:
                        lines.append(f"\033[1;33m{row}\033[0m")
                        if p.cmdline:
                            lines.append(f"       \033[90mCmd: {p.cmdline[:65]}\033[0m")
                    else:
                        lines.append(row)

            lines.append("\n" + "=" * 78)
            lines.append(f"Status: {status_msg}")
            lines.append("Keys:   [\033[1mUp/Down\033[0m] Select  [\033[1mx\033[0m] Terminate PID  [\033[1mr\033[0m] Refresh  [\033[1mq\033[0m] Quit")

            # Draw
            sys.stdout.write("\033[2J\033[H" + "\n".join(lines))
            sys.stdout.flush()

            # Handle input
            key = _read_key()
            if key in ("q", "esc"):
                break
            elif key in ("up", "w"):
                if selected_idx > 0:
                    selected_idx -= 1
            elif key in ("down", "s"):
                if selected_idx < len(procs) - 1:
                    selected_idx += 1
            elif key in ("x", "delete"):
                if procs:
                    target_proc = procs[selected_idx]
                    success, msg = terminate_pid(target_proc.pid, force=True, timeout=2.0)
                    status_msg = msg
                else:
                    status_msg = "No processes to terminate."
            elif key == "r":
                status_msg = f"Refreshed at {time.strftime('%H:%M:%S')}."
    finally:
        # Exit alternate buffer and clear
        sys.stdout.write("\033[?1049l")
        sys.stdout.flush()
