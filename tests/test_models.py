from who_locked.models import LockingProcess, LockReport


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
