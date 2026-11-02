"""File lock snapshot creation, serialisation, and differential comparison."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .core import inspect_locks, scan_directory_tree
from .models import LockingProcess


@dataclass
class ProcessRef:
    """Compact process entry in a snapshot."""

    pid: int
    name: str
    exe_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pid": self.pid,
            "name": self.name,
            "exe_path": self.exe_path,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessRef":
        return cls(
            pid=int(data["pid"]),
            name=str(data["name"]),
            exe_path=data.get("exe_path"),
        )


@dataclass
class LockSnapshot:
    """Point-in-time record of file locks across target paths."""

    timestamp: str
    root_path: str
    locks: Dict[str, List[ProcessRef]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "root_path": self.root_path,
            "lock_count": len(self.locks),
            "locks": {
                path_key: [proc.to_dict() for proc in procs]
                for path_key, procs in self.locks.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LockSnapshot":
        locks = {}
        for path_key, proc_list in data.get("locks", {}).items():
            locks[path_key] = [ProcessRef.from_dict(p) for p in proc_list]
        return cls(
            timestamp=data.get("timestamp", ""),
            root_path=data.get("root_path", ""),
            locks=locks,
        )

    def save(self, filepath: str | Path) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2)

    @classmethod
    def load(cls, filepath: str | Path) -> "LockSnapshot":
        with open(filepath, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return cls.from_dict(data)


@dataclass
class SnapshotDiff:
    """Differences between two file lock snapshots."""

    before_timestamp: str
    after_timestamp: str
    added_locks: Dict[str, List[ProcessRef]] = field(default_factory=dict)
    released_locks: Dict[str, List[ProcessRef]] = field(default_factory=dict)
    persisting_locks: Dict[str, List[ProcessRef]] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        return bool(self.added_locks or self.released_locks)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "before_timestamp": self.before_timestamp,
            "after_timestamp": self.after_timestamp,
            "has_changes": self.has_changes,
            "added_count": len(self.added_locks),
            "released_count": len(self.released_locks),
            "persisting_count": len(self.persisting_locks),
            "added_locks": {
                path_key: [proc.to_dict() for proc in procs]
                for path_key, procs in self.added_locks.items()
            },
            "released_locks": {
                path_key: [proc.to_dict() for proc in procs]
                for path_key, procs in self.released_locks.items()
            },
            "persisting_locks": {
                path_key: [proc.to_dict() for proc in procs]
                for path_key, procs in self.persisting_locks.items()
            },
        }


def _process_to_ref(proc: LockingProcess) -> ProcessRef:
    return ProcessRef(pid=proc.pid, name=proc.name, exe_path=proc.exe_path)


def take_snapshot(target_path: str) -> LockSnapshot:
    """Inspect the target file or directory tree and return a point-in-time snapshot."""
    norm_path = os.path.abspath(target_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    locks: Dict[str, List[ProcessRef]] = {}

    if os.path.isdir(norm_path):
        tree_report = scan_directory_tree(norm_path)
        for entry in tree_report.locked_entries:
            key = os.path.abspath(entry.path)
            locks[key] = [_process_to_ref(p) for p in entry.locking_processes]
    else:
        report = inspect_locks([norm_path])
        if report.is_locked:
            locks[norm_path] = [_process_to_ref(p) for p in report.locking_processes]

    return LockSnapshot(timestamp=now_iso, root_path=norm_path, locks=locks)


def compare_snapshots(before: LockSnapshot, after: LockSnapshot) -> SnapshotDiff:
    """Compare two lock snapshots and identify added, released, and persisting locks."""
    added: Dict[str, List[ProcessRef]] = {}
    released: Dict[str, List[ProcessRef]] = {}
    persisting: Dict[str, List[ProcessRef]] = {}

    all_keys = set(before.locks.keys()) | set(after.locks.keys())

    for key in sorted(all_keys):
        in_before = key in before.locks
        in_after = key in after.locks

        if in_before and not in_after:
            released[key] = before.locks[key]
        elif in_after and not in_before:
            added[key] = after.locks[key]
        else:
            before_pids = {p.pid for p in before.locks[key]}
            after_pids = {p.pid for p in after.locks[key]}

            if before_pids == after_pids:
                persisting[key] = after.locks[key]
            else:
                new_procs = [p for p in after.locks[key] if p.pid not in before_pids]
                freed_procs = [p for p in before.locks[key] if p.pid not in after_pids]
                kept_procs = [p for p in after.locks[key] if p.pid in before_pids]

                if new_procs:
                    added[key] = new_procs
                if freed_procs:
                    released[key] = freed_procs
                if kept_procs:
                    persisting[key] = kept_procs

    return SnapshotDiff(
        before_timestamp=before.timestamp,
        after_timestamp=after.timestamp,
        added_locks=added,
        released_locks=released,
        persisting_locks=persisting,
    )
