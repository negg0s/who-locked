"""who-locked: Fast Windows file lock inspector and release CLI."""

from .core import inspect_locks, release_locks, scan_directory_tree, wait_for_release, watch_lock_events
from .models import LockedFileEntry, LockingProcess, LockReport, TreeReport

__version__ = "0.2.0"
__all__ = [
    "__version__",
    "inspect_locks",
    "release_locks",
    "scan_directory_tree",
    "wait_for_release",
    "watch_lock_events",
    "LockedFileEntry",
    "LockingProcess",
    "LockReport",
    "TreeReport",
]
