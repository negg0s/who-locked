import sys
import pytest
from who_locked.bench import run_benchmark


def test_run_benchmark():
    if sys.platform != "win32":
        pytest.skip("Windows only")

    res = run_benchmark(samples=3)
    assert res["samples_rm"] == 3
    assert "restart_manager_ms" in res
    assert "nt_handle_scan_ms" in res
    assert res["restart_manager_ms"]["median"] >= 0.0
    assert "p99" in res["restart_manager_ms"]
    assert "stddev" in res["restart_manager_ms"]
