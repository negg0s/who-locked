import json
import os
import statistics
import time
from typing import Any, Dict, List, Optional

from .core import inspect_locks
from .models import LockReport


def record_lock_trace(
    target_path: str,
    output_path: str,
    duration: float = 10.0,
    interval: float = 0.1,
) -> Dict[str, Any]:
    """Record lock acquisition and release events to a JSONL trace file."""
    abs_target = os.path.abspath(target_path)
    abs_output = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(abs_output) or ".", exist_ok=True)

    start_time = time.time()
    events_recorded = 0
    currently_locked = False
    lock_acq_time: Optional[float] = None
    last_procs: List[Dict[str, Any]] = []

    with open(abs_output, "w", encoding="utf-8") as out_file:
        while time.time() - start_time < duration:
            report: LockReport = inspect_locks(abs_target)
            now = time.time()

            if report.is_locked and not currently_locked:
                currently_locked = True
                lock_acq_time = now
                last_procs = [p.to_dict() for p in report.locking_processes]
                record = {
                    "event": "lock_acquired",
                    "timestamp": round(now, 4),
                    "target": abs_target,
                    "process_count": len(last_procs),
                    "processes": last_procs,
                }
                out_file.write(json.dumps(record) + "\n")
                out_file.flush()
                events_recorded += 1

            elif not report.is_locked and currently_locked:
                currently_locked = False
                hold_ms = round(((now - lock_acq_time) * 1000.0), 2) if lock_acq_time else 0.0
                record = {
                    "event": "lock_released",
                    "timestamp": round(now, 4),
                    "target": abs_target,
                    "hold_duration_ms": hold_ms,
                    "previous_processes": last_procs,
                }
                out_file.write(json.dumps(record) + "\n")
                out_file.flush()
                events_recorded += 1
                lock_acq_time = None

            time.sleep(interval)

    return {
        "target": abs_target,
        "output_path": abs_output,
        "duration_sec": round(duration, 2),
        "events_recorded": events_recorded,
    }


def analyze_lock_trace(trace_path: str) -> Dict[str, Any]:
    """Parse a trace JSONL file and compute duration and process statistics."""
    abs_path = os.path.abspath(trace_path)
    if not os.path.exists(abs_path):
        return {"error": "Trace file does not exist", "path": abs_path}

    durations_ms: List[float] = []
    process_counts: Dict[str, int] = {}
    event_count = 0

    with open(abs_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                event_count += 1
                if record.get("event") == "lock_released":
                    dur = record.get("hold_duration_ms", 0.0)
                    durations_ms.append(dur)
                    for p in record.get("previous_processes", []):
                        name = p.get("name", "Unknown")
                        process_counts[name] = process_counts.get(name, 0) + 1
            except json.JSONDecodeError:
                continue

    stats = {
        "min": 0.0,
        "median": 0.0,
        "p95": 0.0,
        "max": 0.0,
        "mean": 0.0,
    }
    if durations_ms:
        sorted_d = sorted(durations_ms)
        p95_idx = int(0.95 * (len(sorted_d) - 1))
        stats = {
            "min": round(min(sorted_d), 2),
            "median": round(statistics.median(sorted_d), 2),
            "p95": round(sorted_d[p95_idx], 2),
            "max": round(max(sorted_d), 2),
            "mean": round(statistics.mean(sorted_d), 2),
        }

    top_procs = sorted(process_counts.items(), key=lambda x: x[1], reverse=True)

    return {
        "trace_file": abs_path,
        "total_events": event_count,
        "lock_cycles_count": len(durations_ms),
        "total_locked_time_ms": round(sum(durations_ms), 2),
        "hold_duration_stats_ms": stats,
        "top_locking_processes": [{"name": k, "lock_count": v} for k, v in top_procs],
    }
