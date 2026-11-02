import os
import subprocess
import sys
import tempfile
import time
import pytest

from who_locked.core import collect_paths_to_check, inspect_locks, release_locks, wait_for_release


def test_collect_paths_file():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_name = f.name
    try:
        paths = collect_paths_to_check(temp_name)
        assert len(paths) == 1
        assert os.path.abspath(temp_name) == paths[0]
    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)


def test_collect_paths_dir():
    with tempfile.TemporaryDirectory() as temp_dir:
        f1 = os.path.join(temp_dir, "a.txt")
        f2 = os.path.join(temp_dir, "b.txt")
        with open(f1, "w") as f:
            f.write("1")
        with open(f2, "w") as f:
            f.write("2")

        paths = collect_paths_to_check(temp_dir, max_dir_files=5)
        assert len(paths) == 3
        assert os.path.abspath(temp_dir) in paths


def test_inspect_free_file():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_name = f.name
    try:
        report = inspect_locks(temp_name)
        assert report.is_locked is False
        assert len(report.locking_processes) == 0
        assert report.error is None
    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)


def test_inspect_locked_file_real():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_name = f.name

    try:
        # Hold file open exclusively
        with open(temp_name, "a") as handle:
            handle.write("lock test")
            handle.flush()

            report = inspect_locks(temp_name)
            assert report.is_locked is True
            assert len(report.locking_processes) >= 1
            current_pid = os.getpid()
            pids = [p.pid for p in report.locking_processes]
            assert current_pid in pids

        # Once closed, should be free
        report_freed = inspect_locks(temp_name)
        assert report_freed.is_locked is False
    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)


def test_cross_process_lock_and_release():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_name = os.path.abspath(f.name)

    # Spawn separate child process that holds the file open
    child_code = (
        "import time\n"
        f"handle = open(r'{temp_name}', 'a')\n"
        "handle.write('data')\n"
        "handle.flush()\n"
        "time.sleep(15)\n"
    )
    proc = subprocess.Popen([sys.executable, "-c", child_code])
    try:
        time.sleep(0.5)
        report = inspect_locks(temp_name)
        assert report.is_locked is True

        import psutil
        expected_pids = {proc.pid}
        try:
            for child in psutil.Process(proc.pid).children(recursive=True):
                expected_pids.add(child.pid)
        except Exception:
            pass

        locking_pids = {p.pid for p in report.locking_processes}
        assert len(expected_pids.intersection(locking_pids)) > 0

        # Release the lock by terminating locking processes
        result = release_locks(temp_name, force=True)
        assert result["success"] is True
        assert result["remaining_locks"] == 0

        # Now file should be free
        assert wait_for_release(temp_name, timeout=2.0) is True
    finally:
        try:
            import psutil
            parent = psutil.Process(proc.pid)
            for c in parent.children(recursive=True):
                c.kill()
            parent.kill()
        except Exception:
            if proc.poll() is None:
                proc.kill()
        time.sleep(0.1)
        if os.path.exists(temp_name):
            try:
                os.remove(temp_name)
            except OSError:
                pass


def test_wait_for_release_success():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_name = f.name
    try:
        # File is not locked, wait_for_release returns True immediately
        assert wait_for_release(temp_name, timeout=1.0) is True
    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)
