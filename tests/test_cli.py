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


def test_cli_menu_status():
    runner = CliRunner()
    result = runner.invoke(cli, ["menu", "status"])
    assert result.exit_code == 0
    assert "Explorer context menu item:" in result.output
