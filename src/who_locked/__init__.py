"""who-locked: Fast Windows file lock inspector and release CLI."""

from .core import inspect_locks, release_locks, wait_for_release
from .models import LockingProcess, LockReport

__version__ = "0.1.0"
__all__ = [
    "__version__",
    "inspect_locks",
    "release_locks",
    "wait_for_release",
    "LockingProcess",
    "LockReport",
]
