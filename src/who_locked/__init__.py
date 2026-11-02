"""who-locked: Fast Windows file lock inspector and release CLI."""

from .core import (
    clean_directory,
    inspect_locks,
    release_locks,
    scan_directory_tree,
    wait_for_release,
    watch_lock_events,
)
from .models import LockedFileEntry, LockingProcess, LockReport, TreeReport
from .safety import CRITICAL_NAMES, PROTECTED_PIDS, is_safe_to_terminate

__version__ = "0.2.0"
__all__ = [
    "__version__",
    "clean_directory",
    "inspect_locks",
    "release_locks",
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
