import json
import os
from typing import Any, Dict, List, Optional


def render_ascii_timeline(trace_path: str, width: int = 50) -> str:
    """Render an ASCII Gantt chart timeline from a lock trace JSONL file."""
    abs_path = os.path.abspath(trace_path)
    if not os.path.exists(abs_path):
        return f"Error: Trace file '{abs_path}' does not exist."

    intervals: List[Dict[str, Any]] = []
    pending_acquisitions: List[Dict[str, Any]] = []

    with open(abs_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                ev = rec.get("event")
                ts = rec.get("timestamp", 0.0)

                if ev == "lock_acquired":
                    pending_acquisitions.append(rec)
                elif ev == "lock_released":
                    dur_ms = rec.get("hold_duration_ms", 0.0)
                    dur_s = dur_ms / 1000.0
                    start_ts = ts - dur_s
                    procs = rec.get("previous_processes", [])
                    label = procs[0].get("name", "Unknown") if procs else "Unknown"
                    pid = procs[0].get("pid", 0) if procs else 0

                    intervals.append({
                        "label": f"PID {pid} ({label})",
                        "start": start_ts,
                        "end": ts,
                        "duration_s": dur_s,
                    })
                    if pending_acquisitions:
                        pending_acquisitions.pop(0)
            except json.JSONDecodeError:
                continue

    if not intervals:
        return f"No completed lock cycles found in '{os.path.basename(abs_path)}'."

    min_t = min(i["start"] for i in intervals)
    max_t = max(i["end"] for i in intervals)
    span = max_t - min_t

    if span <= 0:
        span = 1.0

    lines = []
    lines.append(f"Lock Timeline: {os.path.basename(abs_path)} (Window: {span:.2f}s, {len(intervals)} cycles)")
    time_header = f"0.0s{' ' * (width - 8)}{span:.2f}s"
    lines.append(f"Time: {time_header}")
    lines.append(f"      |{'-' * (width - 2)}|")

    for item in intervals:
        start_ratio = max(0.0, min(1.0, (item["start"] - min_t) / span))
        end_ratio = max(0.0, min(1.0, (item["end"] - min_t) / span))

        bar_len = width - 2
        start_col = int(start_ratio * bar_len)
        end_col = max(start_col + 1, int(end_ratio * bar_len))

        bar_chars = [" "] * bar_len
        for col in range(start_col, min(end_col, bar_len)):
            bar_chars[col] = "="

        if start_col < bar_len:
            bar_chars[start_col] = "["
        if end_col - 1 < bar_len:
            bar_chars[min(end_col - 1, bar_len - 1)] = "]"

        bar_str = "".join(bar_chars)
        dur_label = f"{item['duration_s'] * 1000.0:.1f}ms"
        lines.append(f"{item['label'][:25]:<26}")
        lines.append(f"      |{bar_str}|  {dur_label}")

    return "\n".join(lines)
