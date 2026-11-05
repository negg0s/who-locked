import os
import statistics
import tempfile
import time
from typing import Any, Dict, List

from .handle_ops import get_all_system_handles
from .restart_manager import RestartManagerSession


def _compute_stats(values: List[float]) -> Dict[str, float]:
    if not values:
        return {
            "min": 0.0,
            "median": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "stddev": 0.0,
        }
    sorted_v = sorted(values)
    p95_idx = int(0.95 * (len(sorted_v) - 1))
    p99_idx = int(0.99 * (len(sorted_v) - 1))
    stddev = round(statistics.stdev(values), 3) if len(values) > 1 else 0.0
    return {
        "min": round(min(sorted_v), 3),
        "median": round(statistics.median(sorted_v), 3),
        "p95": round(sorted_v[p95_idx], 3),
        "p99": round(sorted_v[p99_idx], 3),
        "max": round(max(sorted_v), 3),
        "mean": round(statistics.mean(sorted_v), 3),
        "stddev": stddev,
    }


def run_benchmark(samples: int = 30) -> Dict[str, Any]:
    """Measure latency and throughput of lock inspection APIs."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_path = os.path.abspath(f.name)

    rm_times_ms: List[float] = []
    nt_times_ms: List[float] = []
    handle_counts: List[int] = []

    try:
        # Measure Restart Manager session latency
        for _ in range(samples):
            t0 = time.perf_counter()
            with RestartManagerSession() as session:
                session.register_resources([temp_path])
                session.get_locking_processes()
            t1 = time.perf_counter()
            rm_times_ms.append((t1 - t0) * 1000.0)

        # Measure NT handle table scan latency
        for _ in range(max(5, samples // 3)):
            t0 = time.perf_counter()
            _, count = get_all_system_handles()
            t1 = time.perf_counter()
            nt_times_ms.append((t1 - t0) * 1000.0)
            if count > 0:
                handle_counts.append(count)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

    total_handles = handle_counts[0] if handle_counts else 0
    nt_median_ms = statistics.median(nt_times_ms) if nt_times_ms else 1.0
    handles_per_sec = int((total_handles / (nt_median_ms / 1000.0))) if nt_median_ms > 0 else 0

    return {
        "samples_rm": len(rm_times_ms),
        "samples_nt": len(nt_times_ms),
        "total_system_handles": total_handles,
        "handles_per_second": handles_per_sec,
        "restart_manager_ms": _compute_stats(rm_times_ms),
        "nt_handle_scan_ms": _compute_stats(nt_times_ms),
    }
