from who_locked.models import LockedFileEntry, LockingProcess, LockReport, TreeReport


def test_locking_process_dict():
    proc = LockingProcess(
        pid=1234,
        name="test.exe",
        app_type="MainWindow",
        app_status="Running",
        service_name=None,
        restartable=True,
        exe_path="C:\\test\\test.exe",
        username="DOMAIN\\user",
        memory_mb=42.5,
    )
    d = proc.to_dict()
    assert d["pid"] == 1234
    assert d["name"] == "test.exe"
    assert d["memory_mb"] == 42.5
    assert d["restartable"] is True


def test_lock_report_dict():
    proc = LockingProcess(pid=999, name="app.exe")
    report = LockReport(
        target_path="D:\\temp\\file.txt",
        is_directory=False,
        is_locked=True,
        locking_processes=[proc],
        queried_paths=["D:\\temp\\file.txt"],
    )
    d = report.to_dict()
    assert d["target_path"] == "D:\\temp\\file.txt"
    assert d["is_locked"] is True
    assert d["process_count"] == 1
    assert len(d["locking_processes"]) == 1
    assert d["locking_processes"][0]["pid"] == 999


def test_tree_report_summary():
    p1 = LockingProcess(pid=100, name="node.exe")
    p2 = LockingProcess(pid=200, name="python.exe")
    e1 = LockedFileEntry(path="a.txt", relative_path="a.txt", locking_processes=[p1])
    e2 = LockedFileEntry(path="b.txt", relative_path="b.txt", locking_processes=[p1, p2])
    report = TreeReport(root_path=".", scanned_files_count=2, locked_entries=[e1, e2])

    summary = report.process_summary()
    assert len(summary) == 2
    assert summary[0]["pid"] == 100
    assert summary[0]["locked_files_count"] == 2
    assert summary[1]["pid"] == 200
    assert summary[1]["locked_files_count"] == 1
