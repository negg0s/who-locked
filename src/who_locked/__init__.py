"""who-locked: Fast Windows file lock inspector and release CLI."""

from .bench import run_benchmark
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
from .graph import ContentionReport, build_contention_graph
from .handle_ops import (
    HandleInfo,
    close_process_handle,
    close_target_file_handles,
    decode_access_mask,
    find_file_handles_in_process,
    get_all_system_handles,
    get_process_file_handle_details,
)
from .html_report import render_html_report
from .models import LockedFileEntry, LockingProcess, LockReport, TreeReport
from .module_ops import find_processes_with_loaded_module
from .plot import render_ascii_timeline
from .safety import CRITICAL_NAMES, PROTECTED_PIDS, is_safe_to_terminate
from .snapshot import LockSnapshot, ProcessRef, SnapshotDiff, compare_snapshots, take_snapshot
from .trace import analyze_lock_trace, record_lock_trace
from .tui import run_tui

__version__ = "0.8.0"
__all__ = [
    "__version__",
    "analyze_lock_trace",
    "build_contention_graph",
    "clean_directory",
    "close_process_handle",
    "close_target_file_handles",
    "compare_snapshots",
    "ContentionReport",
    "decode_access_mask",
    "find_file_handles_in_process",
    "find_locks_by_process",
    "find_processes_with_loaded_module",
    "get_all_system_handles",
    "get_process_file_handle_details",
    "inspect_locks",
    "is_safe_to_terminate",
    "LockedFileEntry",
    "LockingProcess",
    "LockReport",
    "LockSnapshot",
    "ProcessRef",
    "record_lock_trace",
    "release_locks",
    "release_selected_processes",
    "render_ascii_timeline",
    "render_html_report",
    "run_benchmark",
    "run_tui",
    "scan_directory_tree",
    "SnapshotDiff",
    "take_snapshot",
    "TreeReport",
    "wait_for_release",
    "watch_lock_events",
    "CRITICAL_NAMES",
    "HandleInfo",
    "PROTECTED_PIDS",
]
