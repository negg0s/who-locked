import json
import os
import tempfile
from who_locked.plot import render_ascii_timeline


def test_render_ascii_timeline_empty():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        path = f.name
    try:
        out = render_ascii_timeline(path)
        assert "No completed lock cycles" in out
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_render_ascii_timeline_synthetic():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl", mode="w", encoding="utf-8") as f:
        f.write(json.dumps({
            "event": "lock_acquired",
            "timestamp": 100.0,
            "target": "C:\\build.bin",
        }) + "\n")
        f.write(json.dumps({
            "event": "lock_released",
            "timestamp": 102.5,
            "target": "C:\\build.bin",
            "hold_duration_ms": 2500.0,
            "previous_processes": [{"name": "cl.exe", "pid": 4120}],
        }) + "\n")
        path = f.name

    try:
        out = render_ascii_timeline(path, width=40)
        assert "cl.exe" in out
        assert "4120" in out
        assert "2500.0ms" in out
        assert "[" in out and "]" in out
    finally:
        if os.path.exists(path):
            os.remove(path)
