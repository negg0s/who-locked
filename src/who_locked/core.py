import os
import time
from typing import Any, Dict, List, Optional

from .models import LockingProcess, LockReport
from .process_ops import enrich_process_info, terminate_pid
from .restart_manager import RestartManagerSession


def collect_paths_to_check(target_path: str, max_dir_files: int = 100) -> List[str]:
    """Gather paths to register with Restart Manager."""
    abs_path = os.path.abspath(target_path)
    if not os.path.exists(abs_path):
        return [abs_path]

    if os.path.isfile(abs_path):
        return [abs_path]

    # Target is a directory: register directory handle and files inside
    paths = [abs_path]
    try:
        count = 0
        for root, dirs, files in os.walk(abs_path):
            for file_name in files:
                paths.append(os.path.join(root, file_name))
                count += 1
                if count >= max_dir_files:
                    break
            if count >= max_dir_files:
                break
    except OSError:
        pass

    return paths


def inspect_locks(target_path: str, max_dir_files: int = 100) -> LockReport:
    """Check which processes hold active locks on a file or directory."""
    abs_path = os.path.abspath(target_path)
    is_dir = os.path.isdir(abs_path)

    paths_to_query = collect_paths_to_check(abs_path, max_dir_files=max_dir_files)

    try:
        with RestartManagerSession() as session:
            session.register_resources(paths_to_query)
            raw_procs = session.get_locking_processes()

        seen_pids = set()
        processes: List[LockingProcess] = []

        for raw in raw_procs:
            pid = int(raw.Process.dwProcessId)
            if pid in seen_pids:
                continue
            seen_pids.add(pid)
            processes.append(enrich_process_info(raw))

        return LockReport(
            target_path=abs_path,
            is_directory=is_dir,
            is_locked=len(processes) > 0,
            locking_processes=processes,
            queried_paths=paths_to_query,
        )
    except Exception as exc:
        return LockReport(
            target_path=abs_path,
            is_directory=is_dir,
            is_locked=False,
            locking_processes=[],
            queried_paths=paths_to_query,
            error=str(exc),
        )


def release_locks(target_path: str, force: bool = False, timeout: float = 3.0) -> Dict[str, Any]:
    """Terminate all processes locking the specified target."""
    initial_report = inspect_locks(target_path)
    if not initial_report.is_locked:
        return {
            "target_path": initial_report.target_path,
            "was_locked": False,
            "success": True,
            "results": [],
            "remaining_locks": 0,
        }

    results = []
    for proc in initial_report.locking_processes:
        success, msg = terminate_pid(proc.pid, force=force, timeout=timeout)
        results.append({
            "pid": proc.pid,
            "name": proc.name,
            "success": success,
            "message": msg,
        })

    # Verify if any locks remain
    time.sleep(0.1)
    final_report = inspect_locks(target_path)

    return {
        "target_path": initial_report.target_path,
        "was_locked": True,
        "success": not final_report.is_locked,
        "results": results,
        "remaining_locks": len(final_report.locking_processes),
    }


def wait_for_release(
    target_path: str,
    timeout: float = 10.0,
    interval: float = 0.25,
) -> bool:
    """Wait until the target path has no active locks, or until timeout."""
    start_time = time.time()
    while True:
        report = inspect_locks(target_path)
        if not report.is_locked:
            return True
        if time.time() - start_time >= timeout:
            return False
        time.sleep(interval)
