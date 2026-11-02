from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LockingProcess:
    """Information about a process holding a file handle."""

    pid: int
    name: str
    app_type: str = "Unknown"
    app_status: str = "Running"
    service_name: Optional[str] = None
    restartable: bool = False
    exe_path: Optional[str] = None
    username: Optional[str] = None
    memory_mb: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pid": self.pid,
            "name": self.name,
            "app_type": self.app_type,
            "app_status": self.app_status,
            "service_name": self.service_name,
            "restartable": self.restartable,
            "exe_path": self.exe_path,
            "username": self.username,
            "memory_mb": self.memory_mb,
        }


@dataclass
class LockReport:
    """Result of inspecting file locks for a target path."""

    target_path: str
    is_directory: bool
    is_locked: bool
    locking_processes: List[LockingProcess] = field(default_factory=list)
    queried_paths: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_path": self.target_path,
            "is_directory": self.is_directory,
            "is_locked": self.is_locked,
            "process_count": len(self.locking_processes),
            "locking_processes": [proc.to_dict() for proc in self.locking_processes],
            "queried_paths": self.queried_paths,
            "error": self.error,
        }
