import os
import sys
import tempfile
import pytest

from who_locked.handle_ops import (
    close_process_handle,
    close_target_file_handles,
    find_file_handles_in_process,
    get_all_system_handles,
)


def test_get_all_system_handles():
    if sys.platform != "win32":
        pytest.skip("Windows only")

    buf, count = get_all_system_handles()
    assert buf is not None
    assert count > 0


def test_find_and_close_own_handle():
    if sys.platform != "win32":
        pytest.skip("Windows only")

    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_name = os.path.abspath(f.name)

    # Open file exclusively
    handle = open(temp_name, "a")
    handle.write("test data")
    handle.flush()

    try:
        my_pid = os.getpid()
        found_handles = find_file_handles_in_process(my_pid, temp_name)
        assert len(found_handles) >= 1

        # Close handle directly through OS API
        target_h = found_handles[0]
        res = close_process_handle(my_pid, target_h)
        assert res is True

        # File can now be removed even though handle object is still held
        os.remove(temp_name)
        assert not os.path.exists(temp_name)
    finally:
        try:
            handle.close()
        except OSError:
            pass
        if os.path.exists(temp_name):
            try:
                os.remove(temp_name)
            except OSError:
                pass


def test_close_target_file_handles():
    if sys.platform != "win32":
        pytest.skip("Windows only")

    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_name = os.path.abspath(f.name)

    handle = open(temp_name, "a")
    handle.write("sample")
    handle.flush()

    try:
        my_pid = os.getpid()
        result = close_target_file_handles(temp_name, pids=[my_pid])
        assert result["success"] is True
        assert result["total_closed"] >= 1
    finally:
        try:
            handle.close()
        except OSError:
            pass
        if os.path.exists(temp_name):
            try:
                os.remove(temp_name)
            except OSError:
                pass
