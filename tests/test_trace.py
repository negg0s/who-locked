import json
import os
import tempfile
from who_locked.trace import analyze_lock_trace, record_lock_trace


def test_record_and_analyze_trace():
    with tempfile.NamedTemporaryFile(delete=False) as target_f:
        target_path = target_f.name

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl") as trace_f:
        trace_path = trace_f.name

    try:
        # Run short trace
        res = record_lock_trace(target_path, output_path=trace_path, duration=0.2, interval=0.05)
        assert res["duration_sec"] == 0.2
        assert os.path.exists(trace_path)

        # Analyze trace
        analysis = analyze_lock_trace(trace_path)
        assert "total_events" in analysis
        assert "hold_duration_stats_ms" in analysis
    finally:
        if os.path.exists(target_path):
            os.remove(target_path)
        if os.path.exists(trace_path):
            os.remove(trace_path)


def test_analyze_synthetic_trace():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl", mode="w", encoding="utf-8") as f:
        f.write(json.dumps({
            "event": "lock_acquired",
            "timestamp": 1000.0,
            "target": "C:\\test.txt",
            "process_count": 1,
            "processes": [{"name": "node.exe", "pid": 123}],
        }) + "\n")
        f.write(json.dumps({
            "event": "lock_released",
            "timestamp": 1000.25,
            "target": "C:\\test.txt",
            "hold_duration_ms": 250.0,
            "previous_processes": [{"name": "node.exe", "pid": 123}],
        }) + "\n")
        trace_path = f.name

    try:
        analysis = analyze_lock_trace(trace_path)
        assert analysis["total_events"] == 2
        assert analysis["lock_cycles_count"] == 1
        assert analysis["total_locked_time_ms"] == 250.0
        assert analysis["hold_duration_stats_ms"]["median"] == 250.0
        assert len(analysis["top_locking_processes"]) == 1
        assert analysis["top_locking_processes"][0]["name"] == "node.exe"
    finally:
        if os.path.exists(trace_path):
            os.remove(trace_path)
