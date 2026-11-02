import os
import time
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

from .models import LockedFileEntry, LockingProcess, LockReport, TreeReport
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


def _query_restart_manager(file_paths: List[str]) -> List[LockingProcess]:
    """Register paths and return unique enriched locking processes."""
    if not file_paths:
        return []

    with RestartManagerSession() as session:
        session.register_resources(file_paths)
        raw_procs = session.get_locking_processes()

    seen_pids = set()
    processes: List[LockingProcess] = []

    for raw in raw_procs:
        pid = int(raw.Process.dwProcessId)
        if pid in seen_pids:
            continue
        seen_pids.add(pid)
        processes.append(enrich_process_info(raw))

    return processes


def inspect_locks(target_path: str, max_dir_files: int = 100) -> LockReport:
    """Check which processes hold active locks on a file or directory."""
    abs_path = os.path.abspath(target_path)
    is_dir = os.path.isdir(abs_path)
    paths_to_query = collect_paths_to_check(abs_path, max_dir_files=max_dir_files)

    try:
        processes = _query_restart_manager(paths_to_query)
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


def scan_directory_tree(root_dir: str, max_files: int = 1000, batch_size: int = 32) -> TreeReport:
    """Scan a directory tree and identify each specific locked file."""
    abs_root = os.path.abspath(root_dir)
    if not os.path.exists(abs_root):
        return TreeReport(root_path=abs_root, scanned_files_count=0, error="Path does not exist")
    if not os.path.isdir(abs_root):
        return TreeReport(root_path=abs_root, scanned_files_count=0, error="Target is not a directory")

    all_files: List[str] = []
    try:
        for cur_root, _, files in os.walk(abs_root):
            for f in files:
                all_files.append(os.path.join(cur_root, f))
                if len(all_files) >= max_files:
                    break
            if len(all_files) >= max_files:
                break
    except OSError as exc:
        return TreeReport(root_path=abs_root, scanned_files_count=len(all_files), error=str(exc))

    locked_entries: List[LockedFileEntry] = []

    # Process in batches for speed
    for i in range(0, len(all_files), batch_size):
        batch = all_files[i : i + batch_size]
        try:
            batch_procs = _query_restart_manager(batch)
            if not batch_procs:
                continue

            # Batch has at least one lock, test each file individually
            for file_path in batch:
                file_procs = _query_restart_manager([file_path])
                if file_procs:
                    rel = os.path.relpath(file_path, abs_root)
                    locked_entries.append(
                        LockedFileEntry(
                            path=file_path,
                            relative_path=rel,
                            locking_processes=file_procs,
                        )
                    )
        except Exception:
            continue

    # Also check the root directory handle itself
    try:
        dir_procs = _query_restart_manager([abs_root])
        if dir_procs:
            locked_entries.insert(
                0,
                LockedFileEntry(
                    path=abs_root,
                    relative_path=".",
                    locking_processes=dir_procs,
                ),
            )
    except Exception:
        pass

    return TreeReport(
        root_path=abs_root,
        scanned_files_count=len(all_files),
        locked_entries=locked_entries,
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


def watch_lock_events(
    target_path: str,
    interval: float = 0.5,
) -> Generator[Dict[str, Any], None, None]:
    """Yield status events when lock state changes on a target path."""
    last_locked: Optional[bool] = None
    lock_start_time: Optional[float] = None

    while True:
        report = inspect_locks(target_path)
        now = time.time()

        if last_locked is None:
            last_locked = report.is_locked
            if report.is_locked:
                lock_start_time = now
                yield {
                    "event": "INITIAL_LOCKED",
                    "timestamp": now,
                    "report": report,
                    "duration_sec": 0.0,
                }
            else:
                yield {
                    "event": "INITIAL_FREE",
                    "timestamp": now,
                    "report": report,
                    "duration_sec": 0.0,
                }
        elif report.is_locked and not last_locked:
            last_locked = True
            lock_start_time = now
            yield {
                "event": "LOCK_ACQUIRED",
                "timestamp": now,
                "report": report,
                "duration_sec": 0.0,
            }
        elif not report.is_locked and last_locked:
            last_locked = False
            duration = (now - lock_start_time) if lock_start_time else 0.0
            lock_start_time = None
            yield {
                "event": "LOCK_RELEASED",
                "timestamp": now,
                "report": report,
                "duration_sec": round(duration, 3),
            }

        time.sleep(interval)
