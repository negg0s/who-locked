from typing import Optional, Tuple
import psutil

from .models import LockingProcess
from .restart_manager import RM_APP_STATUSES, RM_APP_TYPES, RM_PROCESS_INFO


def enrich_process_info(raw: RM_PROCESS_INFO) -> LockingProcess:
    """Enrich raw Restart Manager process info with system details."""
    pid = int(raw.Process.dwProcessId)
    app_name = str(raw.strAppName).strip()
    svc_name = str(raw.strServiceShortName).strip() or None
    app_type = RM_APP_TYPES.get(int(raw.ApplicationType), "Unknown")
    app_status = RM_APP_STATUSES.get(int(raw.AppStatus), "Running")
    restartable = bool(raw.bRestartable)

    exe_path: Optional[str] = None
    username: Optional[str] = None
    memory_mb: Optional[float] = None
    resolved_name = app_name

    try:
        proc = psutil.Process(pid)
        if not resolved_name or resolved_name.lower() == "unknown":
            resolved_name = proc.name()

        try:
            exe_path = proc.exe()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass

        try:
            username = proc.username()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass

        try:
            mem = proc.memory_info()
            memory_mb = round(mem.rss / (1024 * 1024), 2)
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    if not resolved_name:
        resolved_name = f"PID {pid}"

    return LockingProcess(
        pid=pid,
        name=resolved_name,
        app_type=app_type,
        app_status=app_status,
        service_name=svc_name,
        restartable=restartable,
        exe_path=exe_path,
        username=username,
        memory_mb=memory_mb,
    )


def terminate_pid(pid: int, force: bool = False, timeout: float = 3.0) -> Tuple[bool, str]:
    """Terminate a process by PID.

    Returns a tuple of (success, message).
    """
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return True, f"Process {pid} already exited."
    except psutil.AccessDenied:
        return False, f"Access denied for PID {pid}. Administrator rights may be needed."

    proc_name = proc.name()

    try:
        if force:
            proc.kill()
        else:
            proc.terminate()

        try:
            proc.wait(timeout=timeout)
            return True, f"Terminated {proc_name} (PID {pid})."
        except psutil.TimeoutExpired:
            if force:
                proc.kill()
                proc.wait(timeout=1.0)
                return True, f"Force-killed {proc_name} (PID {pid})."
            return False, f"Process {proc_name} (PID {pid}) did not exit within {timeout}s. Use --force to kill."
    except psutil.NoSuchProcess:
        return True, f"Process {pid} exited."
    except psutil.AccessDenied:
        return False, f"Access denied when attempting to terminate PID {pid}."
    except Exception as exc:
        return False, f"Failed to terminate PID {pid}: {exc}"
