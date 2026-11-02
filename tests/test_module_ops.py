import sys
import pytest
from who_locked.module_ops import find_processes_with_loaded_module


def test_find_processes_with_loaded_module():
    if sys.platform != "win32":
        pytest.skip("Windows only")

    # Python process always loads python3.dll or ntdll.dll
    matches = find_processes_with_loaded_module("ntdll.dll", max_processes=10)
    assert isinstance(matches, list)
    if matches:
        assert matches[0].app_type == "LoadedModule"
        assert matches[0].pid > 0


def test_find_processes_with_loaded_module_nonexistent():
    matches = find_processes_with_loaded_module("definitely_nonexistent_dll_12345.dll", max_processes=5)
    assert matches == []
