"""who-locked: Fast Windows file lock inspector and release CLI."""

from .core import (
    clean_directory,
    find_locks_by_process,
    inspect_locks,
    release_locks,
    release_selected_processes,
    scan_directory_tree,
    wait_for_release,
    watch_lock_events,
)
from .html_report import render_html_report
from .models import LockedFileEntry, LockingProcess, LockReport, TreeReport
from .safety import CRITICAL_NAMES, PROTECTED_PIDS, is_safe_to_terminate
from .tui import run_tui

__version__ = "0.3.0"
__all__ = [
    "__version__",
    "clean_directory",
    "find_locks_by_process",
    "inspect_locks",
    "release_locks",
    "release_selected_processes",
    "render_html_report",
    "run_tui",
    "scan_directory_tree",
    "wait_for_release",
    "watch_lock_events",
    "is_safe_to_terminate",
    "CRITICAL_NAMES",
    "PROTECTED_PIDS",
    "LockedFileEntry",
    "LockingProcess",
    "LockReport",
    "TreeReport",
]
