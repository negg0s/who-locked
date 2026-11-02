import os
from typing import Optional, Tuple

PROTECTED_PIDS = frozenset({0, 4})

CRITICAL_NAMES = frozenset(
    {
        "system",
        "system idle process",
        "registry",
        "smss.exe",
        "csrss.exe",
        "wininit.exe",
        "winlogon.exe",
        "services.exe",
        "lsass.exe",
    }
)


def is_safe_to_terminate(pid: int, name: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """Determine whether a process is safe to terminate."""
    if pid in PROTECTED_PIDS:
        return False, f"PID {pid} is a protected system kernel process."

    current_pid = os.getpid()
    if pid == current_pid:
        return False, f"PID {pid} is the current who-locked process."

    if name:
        base_name = name.lower().strip()
        if base_name in CRITICAL_NAMES:
            return False, f"'{name}' (PID {pid}) is a critical Windows system component."

    return True, None
