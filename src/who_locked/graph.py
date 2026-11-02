"""Lock contention graph and visualization."""

from collections import defaultdict
from dataclasses import dataclass, field
import os
from typing import Any, Dict, List, Set

from .core import inspect_locks, scan_directory_tree
from .models import LockingProcess


@dataclass
class ContentionReport:
    """Report of shared file locks and process relationships."""

    target_path: str
    file_to_processes: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    process_to_files: Dict[str, List[str]] = field(default_factory=dict)
    contended_files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_path": self.target_path,
            "total_files": len(self.file_to_processes),
            "total_processes": len(self.process_to_files),
            "contended_files_count": len(self.contended_files),
            "contended_files": self.contended_files,
            "file_to_processes": self.file_to_processes,
            "process_to_files": self.process_to_files,
        }

    def render_ascii(self) -> str:
        """Render a readable text chart showing processes and file relationships."""
        lines = []
        lines.append(f"Lock Contention Graph: {self.target_path}")
        lines.append("=" * 60)

        if not self.file_to_processes:
            lines.append("No active locks detected.")
            return "\n".join(lines)

        lines.append(f"Processes holding locks ({len(self.process_to_files)}):")
        for proc_key, files in sorted(self.process_to_files.items()):
            lines.append(f"  [P] {proc_key}")
            for f in sorted(files):
                is_shared = f in self.contended_files
                tag = " [SHARED CONTENTION]" if is_shared else ""
                lines.append(f"      -> {os.path.basename(f)}{tag}")

        lines.append("")
        if self.contended_files:
            lines.append(f"Contended Files ({len(self.contended_files)} files held by multiple processes):")
            for f in sorted(self.contended_files):
                procs = self.file_to_processes.get(f, [])
                names = [f"{p['name']} (PID {p['pid']})" for p in procs]
                lines.append(f"  * {os.path.basename(f)} ({f})")
                lines.append(f"      <- shared by: {', '.join(names)}")
        else:
            lines.append("Contended Files: None (all locks held by distinct individual processes).")

        return "\n".join(lines)

    def render_mermaid(self) -> str:
        """Render a Mermaid flowchart diagram for markdown display."""
        lines = ["flowchart LR"]
        if not self.file_to_processes:
            lines.append("  Empty[\"No active locks\"]")
            return "\n".join(lines)

        file_ids: Dict[str, str] = {}
        proc_ids: Dict[str, str] = {}

        for idx, (path_key, procs) in enumerate(sorted(self.file_to_processes.items())):
            fid = f"F{idx}"
            file_ids[path_key] = fid
            base_name = os.path.basename(path_key)
            is_shared = path_key in self.contended_files
            style = ":::contended" if is_shared else ""
            lines.append(f"  {fid}[\"{base_name}\"]{style}")

        for p_idx, proc_key in enumerate(sorted(self.process_to_files.keys())):
            pid = f"P{p_idx}"
            proc_ids[proc_key] = pid
            lines.append(f"  {pid}(\"{proc_key}\")")

        for proc_key, files in sorted(self.process_to_files.items()):
            pid = proc_ids[proc_key]
            for f in sorted(files):
                fid = file_ids[f]
                lines.append(f"  {pid} --> {fid}")

        lines.append("  classDef contended fill:#f96,stroke:#333,stroke-width:2px;")
        return "\n".join(lines)


def build_contention_graph(target_path: str) -> ContentionReport:
    """Analyze file locks in target_path and produce a contention report."""
    norm_path = os.path.abspath(target_path)
    file_to_procs: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    proc_to_files: Dict[str, List[str]] = defaultdict(list)

    if os.path.isdir(norm_path):
        tree = scan_directory_tree(norm_path)
        for entry in tree.locked_entries:
            fpath = os.path.abspath(entry.path)
            for p in entry.locking_processes:
                proc_dict = p.to_dict()
                file_to_procs[fpath].append(proc_dict)
                pkey = f"{p.name} (PID {p.pid})"
                if fpath not in proc_to_files[pkey]:
                    proc_to_files[pkey].append(fpath)
    else:
        rep = inspect_locks([norm_path])
        if rep.is_locked:
            for p in rep.locking_processes:
                proc_dict = p.to_dict()
                file_to_procs[norm_path].append(proc_dict)
                pkey = f"{p.name} (PID {p.pid})"
                if norm_path not in proc_to_files[pkey]:
                    proc_to_files[pkey].append(norm_path)

    contended = [f for f, procs in file_to_procs.items() if len(procs) > 1]

    return ContentionReport(
        target_path=norm_path,
        file_to_processes=dict(file_to_procs),
        process_to_files=dict(proc_to_files),
        contended_files=contended,
    )
