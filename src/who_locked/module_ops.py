import os
from typing import Any, Dict, List, Optional
import psutil

from .process_ops import LockingProcess


def find_processes_with_loaded_module(
    module_path: str,
    max_processes: Optional[int] = None,
) -> List[LockingProcess]:
    """Find running processes that have a specific DLL or binary mapped into memory."""
    norm_target = os.path.normcase(os.path.abspath(module_path))
    target_basename = os.path.normcase(os.path.basename(norm_target))
    matches: List[LockingProcess] = []

    count = 0
    for proc in psutil.process_iter(["pid", "name", "username"]):
        if max_processes and count >= max_processes:
            break
        count += 1

        try:
            maps = proc.memory_maps()
            found = False
            for m in maps:
                if not m.path:
                    continue
                norm_m = os.path.normcase(m.path)
                if norm_m == norm_target or (target_basename and os.path.normcase(os.path.basename(norm_m)) == target_basename):
                    found = True
                    break

            if found:
                pid = proc.info["pid"]
                name = proc.info["name"] or f"PID {pid}"
                exe_path: Optional[str] = None
                mem_mb: Optional[float] = None

                try:
                    exe_path = proc.exe()
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass

                try:
                    mem_info = proc.memory_info()
                    mem_mb = round(mem_info.rss / (1024 * 1024), 2)
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass

                matches.append(
                    LockingProcess(
                        pid=pid,
                        name=name,
                        app_type="LoadedModule",
                        app_status="Running",
                        exe_path=exe_path,
                        username=proc.info.get("username"),
                        memory_mb=mem_mb,
                    )
                )
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue

    return matches
