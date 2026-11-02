import json
import os
import tempfile
from click.testing import CliRunner

from who_locked.cli import cli


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Fast Windows file lock inspector" in result.output


def test_cli_doctor():
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0
    assert "Environment Diagnostics" in result.output


def test_cli_doctor_json():
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "ready" in data
    assert "checks" in data


def test_cli_inspect_free_file():
    runner = CliRunner()
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_name = f.name
    try:
        result = runner.invoke(cli, ["inspect", temp_name])
        assert result.exit_code == 0
        assert "Status: FREE" in result.output
    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)


def test_cli_inspect_quiet():
    runner = CliRunner()
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_name = f.name
    try:
        result = runner.invoke(cli, ["inspect", temp_name, "-q"])
        assert result.exit_code == 0
        assert result.output.strip() == ""
    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)


def test_cli_inspect_json():
    runner = CliRunner()
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_name = f.name
    try:
        result = runner.invoke(cli, ["inspect", temp_name, "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["is_locked"] is False
        assert data["process_count"] == 0
    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)


def test_cli_inspect_formats():
    runner = CliRunner()
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_name = f.name
    try:
        # pids format
        res_pids = runner.invoke(cli, ["inspect", temp_name, "--format", "pids"])
        assert res_pids.exit_code == 0

        # csv format
        res_csv = runner.invoke(cli, ["inspect", temp_name, "--format", "csv"])
        assert res_csv.exit_code == 0
        assert "pid,name,type" in res_csv.output
    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)


def test_cli_tree():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as temp_dir:
        result = runner.invoke(cli, ["tree", temp_dir])
        assert result.exit_code == 0
        assert "CLEAN" in result.output


def test_cli_tree_json():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as temp_dir:
        result = runner.invoke(cli, ["tree", temp_dir, "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["is_locked"] is False
        assert data["locked_count"] == 0


def test_cli_clean_dry_run():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as temp_dir:
        result = runner.invoke(cli, ["clean", temp_dir, "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run for directory:" in result.output


def test_cli_clean_actual():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as base_dir:
        target = os.path.join(base_dir, "del_me")
        os.makedirs(target)
        result = runner.invoke(cli, ["clean", target, "--yes"])
        assert result.exit_code == 0
        assert "Successfully deleted" in result.output
        assert not os.path.exists(target)


def test_cli_inspect_html():
    runner = CliRunner()
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_name = f.name
    try:
        result = runner.invoke(cli, ["inspect", temp_name, "--format", "html"])
        assert result.exit_code == 0
        assert "<!DOCTYPE html>" in result.output
    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)


def test_cli_inspect_markdown():
    runner = CliRunner()
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_name = f.name
    try:
        result = runner.invoke(cli, ["inspect", temp_name, "--format", "markdown"])
        assert result.exit_code == 0
        assert "# Lock Report:" in result.output
        assert "**FREE**" in result.output
    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)


def test_cli_bench():
    runner = CliRunner()
    result = runner.invoke(cli, ["bench", "--samples", "2"])
    assert result.exit_code == 0
    assert "Benchmark Results:" in result.output


def test_cli_bench_json():
    runner = CliRunner()
    result = runner.invoke(cli, ["bench", "--samples", "2", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "restart_manager_ms" in data


def test_cli_find_empty():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as temp_dir:
        result = runner.invoke(cli, ["find", temp_dir, "-p", "nonexistent"])
        assert result.exit_code == 0
        assert "Files in" in result.output


def test_cli_completion():
    runner = CliRunner()
    res_ps = runner.invoke(cli, ["completion", "powershell"])
    assert res_ps.exit_code == 0
    assert "Register-ArgumentCompleter" in res_ps.output

    res_bash = runner.invoke(cli, ["completion", "bash"])
    assert res_bash.exit_code == 0
    assert "complete -F" in res_bash.output


def test_cli_trace_and_stats():
    runner = CliRunner()
    with tempfile.NamedTemporaryFile(delete=False) as target_f:
        target_path = target_f.name

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl") as trace_f:
        trace_path = trace_f.name

    try:
        res = runner.invoke(cli, ["trace", target_path, "-o", trace_path, "-d", "0.2", "-i", "0.05", "--json"])
        assert res.exit_code == 0
        data = json.loads(res.output)
        assert data["duration_sec"] == 0.2

        res_stats = runner.invoke(cli, ["stats", trace_path, "--json"])
        assert res_stats.exit_code == 0
        stats_data = json.loads(res_stats.output)
        assert "total_events" in stats_data
    finally:
        if os.path.exists(target_path):
            os.remove(target_path)
        if os.path.exists(trace_path):
            os.remove(trace_path)


def test_cli_plot():
    runner = CliRunner()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl", mode="w", encoding="utf-8") as f:
        f.write(json.dumps({
            "event": "lock_released",
            "timestamp": 10.0,
            "hold_duration_ms": 500.0,
            "previous_processes": [{"name": "app.exe", "pid": 111}],
        }) + "\n")
        path = f.name
    try:
        res = runner.invoke(cli, ["plot", path])
        assert res.exit_code == 0
        assert "app.exe" in res.output
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_cli_dll_nonexistent():
    runner = CliRunner()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dll") as f:
        path = f.name
    try:
        res = runner.invoke(cli, ["dll", path])
        assert res.exit_code == 0
        assert "No running processes" in res.output
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_cli_close_handle_free_file():
    runner = CliRunner()
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_name = f.name
    try:
        result = runner.invoke(cli, ["close-handle", temp_name, "--yes"])
        assert result.exit_code == 0
        assert "No active locks found" in result.output
    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)


def test_cli_menu_status():
    runner = CliRunner()
    result = runner.invoke(cli, ["menu", "status"])
    assert result.exit_code == 0
    assert "Explorer context menu item:" in result.output


def test_cli_snapshot_and_diff():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "sample.txt")
        with open(test_file, "w") as f:
            f.write("test")

        snap1 = os.path.join(temp_dir, "snap1.json")
        res1 = runner.invoke(cli, ["snapshot", temp_dir, "-o", snap1])
        assert res1.exit_code == 0
        assert "Saved lock snapshot" in res1.output
        assert os.path.exists(snap1)

        res_diff = runner.invoke(cli, ["diff", snap1, temp_dir])
        assert res_diff.exit_code == 0
        assert "Lock Diff Summary" in res_diff.output

        res_diff_json = runner.invoke(cli, ["diff", snap1, temp_dir, "--format", "json"])
        assert res_diff_json.exit_code == 0
        data = json.loads(res_diff_json.output)
        assert "has_changes" in data

        res_diff_md = runner.invoke(cli, ["diff", snap1, temp_dir, "--format", "markdown"])
        assert res_diff_md.exit_code == 0
        assert "# File Lock Diff Report" in res_diff_md.output


def test_cli_graph():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as temp_dir:
        res = runner.invoke(cli, ["graph", temp_dir])
        assert res.exit_code == 0
        assert "Lock Contention Graph" in res.output

        res_m = runner.invoke(cli, ["graph", temp_dir, "--format", "mermaid"])
        assert res_m.exit_code == 0
        assert "flowchart LR" in res_m.output

        res_j = runner.invoke(cli, ["graph", temp_dir, "--format", "json"])
        assert res_j.exit_code == 0
        data = json.loads(res_j.output)
        assert "contended_files_count" in data


def test_cli_run_clean_command():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as temp_dir:
        res = runner.invoke(cli, ["run", "--dir", temp_dir, "--", "python", "-c", "print('hello')"])
        assert res.exit_code == 0
        assert "0 file locks leaked by command." in res.output

