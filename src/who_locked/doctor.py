import ctypes
import platform
import sys
from typing import Any, Dict

from .context_menu import is_context_menu_installed


def check_is_admin() -> bool:
    """Check whether the current process has administrator privileges."""
    if sys.platform != "win32":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def check_restart_manager() -> bool:
    """Verify that rstrtmgr.dll can be loaded."""
    if sys.platform != "win32":
        return False
    try:
        dll = ctypes.WinDLL("rstrtmgr.dll")
        return hasattr(dll, "RmStartSession") and hasattr(dll, "RmGetList")
    except Exception:
        return False


def run_diagnostics() -> Dict[str, Any]:
    """Run diagnostic checks on the environment."""
    is_win = sys.platform == "win32"
    rm_ok = check_restart_manager()
    admin = check_is_admin()
    menu_active = is_context_menu_installed()

    win_ver = platform.version()
    win_release = platform.release()

    checks = {
        "platform": {
            "name": "Operating System",
            "ok": is_win,
            "details": f"{platform.system()} {win_release} (Build {win_ver})",
        },
        "restart_manager": {
            "name": "Restart Manager API",
            "ok": rm_ok,
            "details": "rstrtmgr.dll loaded" if rm_ok else "Unavailable",
        },
        "privileges": {
            "name": "Administrator Privileges",
            "ok": True,
            "details": "Admin" if admin else "Standard User",
        },
        "context_menu": {
            "name": "Explorer Context Menu",
            "ok": True,
            "details": "Installed" if menu_active else "Not installed (use 'who-locked menu install')",
        },
    }

    all_critical_ok = is_win and rm_ok
    return {
        "ready": all_critical_ok,
        "is_admin": admin,
        "checks": checks,
    }
