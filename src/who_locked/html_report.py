import html
from typing import Union
from .models import LockReport, TreeReport


def render_html_report(report: Union[LockReport, TreeReport]) -> str:
    """Render a standalone dark-themed HTML report without external assets."""
    if isinstance(report, LockReport):
        target = report.target_path
        status_badge = (
            '<span class="badge locked">LOCKED</span>'
            if report.is_locked
            else '<span class="badge free">FREE</span>'
        )
        title = f"Lock Report - {html.escape(target)}"

        rows = []
        for p in report.locking_processes:
            mem = f"{p.memory_mb:.1f} MB" if p.memory_mb is not None else "-"
            rows.append(
                f"<tr>"
                f"<td>{p.pid}</td>"
                f"<td><strong>{html.escape(p.name)}</strong></td>"
                f"<td>{html.escape(p.app_type)}</td>"
                f"<td>{mem}</td>"
                f"<td>{html.escape(p.username or '-')}</td>"
                f"<td><code>{html.escape(p.exe_path or '-')}</code></td>"
                f"</tr>"
            )
        table_html = (
            "<table><thead><tr>"
            "<th>PID</th><th>Name</th><th>Type</th><th>Memory</th><th>User</th><th>Executable Path</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
            if rows
            else "<p class='empty'>No active locks holding this target.</p>"
        )

        body_content = f"""
        <div class="card">
            <div class="header">
                <div>
                    <h1>{html.escape(target)}</h1>
                    <p class="subtitle">Type: {"Directory" if report.is_directory else "File"}</p>
                </div>
                <div>{status_badge}</div>
            </div>
            <h2>Locking Processes ({len(report.locking_processes)})</h2>
            {table_html}
        </div>
        """
    else:
        target = report.root_path
        status_badge = (
            '<span class="badge locked">LOCKED FILES FOUND</span>'
            if report.is_locked
            else '<span class="badge free">CLEAN</span>'
        )
        title = f"Tree Lock Report - {html.escape(target)}"

        rows = []
        for entry in report.locked_entries:
            procs = ", ".join(f"{p.name} (PID {p.pid})" for p in entry.locking_processes)
            rows.append(
                f"<tr>"
                f"<td><code>{html.escape(entry.relative_path)}</code></td>"
                f"<td>{html.escape(procs)}</td>"
                f"</tr>"
            )
        table_html = (
            "<table><thead><tr><th>Relative Path</th><th>Locking Processes</th></tr></thead><tbody>"
            + "".join(rows)
            + "</tbody></table>"
            if rows
            else "<p class='empty'>No locked files detected in scanned directory tree.</p>"
        )

        body_content = f"""
        <div class="card">
            <div class="header">
                <div>
                    <h1>{html.escape(target)}</h1>
                    <p class="subtitle">Scanned: {report.scanned_files_count} file(s)</p>
                </div>
                <div>{status_badge}</div>
            </div>
            <h2>Locked Files ({len(report.locked_entries)})</h2>
            {table_html}
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{
    --bg: #0f141c;
    --card-bg: #18202c;
    --border: #283548;
    --text: #e2e8f0;
    --text-dim: #94a3b8;
    --green: #22c55e;
    --red: #ef4444;
    --cyan: #06b6d4;
}}
body {{
    margin: 0;
    padding: 24px;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}}
.card {{
    max-width: 1000px;
    margin: 0 auto;
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 24px;
}}
.header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border);
    padding-bottom: 16px;
    margin-bottom: 24px;
}}
h1 {{ margin: 0 0 6px 0; font-size: 1.4rem; word-break: break-all; }}
h2 {{ font-size: 1.1rem; color: var(--text-dim); margin-top: 24px; }}
.subtitle {{ margin: 0; color: var(--text-dim); font-size: 0.9rem; }}
.badge {{
    display: inline-block;
    padding: 6px 12px;
    border-radius: 4px;
    font-weight: 700;
    font-size: 0.85rem;
    letter-spacing: 0.05em;
}}
.badge.free {{ background: rgba(34, 197, 94, 0.15); color: var(--green); }}
.badge.locked {{ background: rgba(239, 68, 68, 0.15); color: var(--red); }}
table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 12px;
    font-size: 0.9rem;
}}
th, td {{
    text-align: left;
    padding: 10px 12px;
    border-bottom: 1px solid var(--border);
}}
th {{ color: var(--text-dim); font-weight: 600; text-transform: uppercase; font-size: 0.75rem; }}
code {{ font-family: Consolas, monospace; color: var(--cyan); }}
.empty {{ color: var(--text-dim); font-style: italic; }}
</style>
</head>
<body>
{body_content}
</body>
</html>
"""
