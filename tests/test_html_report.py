from who_locked.html_report import render_html_report
from who_locked.models import LockedFileEntry, LockingProcess, LockReport, TreeReport


def test_render_html_lock_report():
    proc = LockingProcess(pid=123, name="test.exe", app_type="Console", memory_mb=12.5)
    report = LockReport(target_path="C:\\test.txt", is_directory=False, is_locked=True, locking_processes=[proc])
    out = render_html_report(report)
    assert "<!DOCTYPE html>" in out
    assert "test.exe" in out
    assert "123" in out
    assert "LOCKED" in out


def test_render_html_tree_report():
    proc = LockingProcess(pid=456, name="worker.exe")
    entry = LockedFileEntry(path="C:\\dir\\sub.txt", relative_path="sub.txt", locking_processes=[proc])
    report = TreeReport(root_path="C:\\dir", scanned_files_count=10, locked_entries=[entry])
    out = render_html_report(report)
    assert "<!DOCTYPE html>" in out
    assert "sub.txt" in out
    assert "worker.exe" in out
