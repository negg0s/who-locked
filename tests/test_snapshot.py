from pathlib import Path
import pytest

from who_locked.snapshot import (
    LockSnapshot,
    ProcessRef,
    SnapshotDiff,
    compare_snapshots,
    take_snapshot,
)


def test_lock_snapshot_serialization(tmp_path: Path) -> None:
    snap_file = tmp_path / "snap.json"
    p1 = ProcessRef(pid=100, name="app.exe", exe_path="C:\\app.exe")
    p2 = ProcessRef(pid=200, name="worker.exe")

    snap = LockSnapshot(
        timestamp="2026-11-02T12:00:00Z",
        root_path=str(tmp_path),
        locks={
            str(tmp_path / "file1.txt"): [p1],
            str(tmp_path / "file2.txt"): [p1, p2],
        },
    )

    snap.save(snap_file)
    loaded = LockSnapshot.load(snap_file)

    assert loaded.timestamp == "2026-11-02T12:00:00Z"
    assert loaded.root_path == str(tmp_path)
    assert len(loaded.locks) == 2
    assert loaded.locks[str(tmp_path / "file1.txt")][0].pid == 100
    assert loaded.locks[str(tmp_path / "file2.txt")][1].name == "worker.exe"


def test_compare_snapshots_added_and_released(tmp_path: Path) -> None:
    f1 = str(tmp_path / "a.txt")
    f2 = str(tmp_path / "b.txt")
    f3 = str(tmp_path / "c.txt")

    p1 = ProcessRef(pid=101, name="node.exe")
    p2 = ProcessRef(pid=102, name="python.exe")
    p3 = ProcessRef(pid=103, name="git.exe")

    before = LockSnapshot(
        timestamp="2026-11-02T10:00:00Z",
        root_path=str(tmp_path),
        locks={
            f1: [p1],
            f2: [p2],
        },
    )

    after = LockSnapshot(
        timestamp="2026-11-02T10:05:00Z",
        root_path=str(tmp_path),
        locks={
            f2: [p2],       # persisting
            f3: [p3],       # added
        },
    )

    diff = compare_snapshots(before, after)
    assert diff.has_changes is True
    assert f3 in diff.added_locks
    assert f1 in diff.released_locks
    assert f2 in diff.persisting_locks
    assert len(diff.added_locks[f3]) == 1
    assert diff.added_locks[f3][0].name == "git.exe"

    d_dict = diff.to_dict()
    assert d_dict["added_count"] == 1
    assert d_dict["released_count"] == 1
    assert d_dict["persisting_count"] == 1


def test_take_snapshot_on_clean_dir(tmp_path: Path) -> None:
    test_file = tmp_path / "free_file.txt"
    test_file.write_text("sample content")

    snap = take_snapshot(str(tmp_path))
    assert snap.root_path == str(tmp_path)
    # On a clean directory, no locks should exist
    assert isinstance(snap.locks, dict)
