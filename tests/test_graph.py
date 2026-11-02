from pathlib import Path
import pytest

from who_locked.graph import ContentionReport, build_contention_graph


def test_contention_report_rendering() -> None:
    report = ContentionReport(
        target_path="D:\\TestProject",
        file_to_processes={
            "D:\\TestProject\\shared.db": [
                {"pid": 111, "name": "service.exe"},
                {"pid": 222, "name": "client.exe"},
            ],
            "D:\\TestProject\\solo.txt": [
                {"pid": 111, "name": "service.exe"},
            ],
        },
        process_to_files={
            "service.exe (PID 111)": [
                "D:\\TestProject\\shared.db",
                "D:\\TestProject\\solo.txt",
            ],
            "client.exe (PID 222)": [
                "D:\\TestProject\\shared.db",
            ],
        },
        contended_files=["D:\\TestProject\\shared.db"],
    )

    ascii_out = report.render_ascii()
    assert "Lock Contention Graph" in ascii_out
    assert "service.exe (PID 111)" in ascii_out
    assert "[SHARED CONTENTION]" in ascii_out
    assert "Contended Files (1 files held by multiple processes)" in ascii_out

    mermaid_out = report.render_mermaid()
    assert "flowchart LR" in mermaid_out
    assert "service.exe (PID 111)" in mermaid_out
    assert "shared.db" in mermaid_out
    assert "classDef contended" in mermaid_out

    rep_dict = report.to_dict()
    assert rep_dict["contended_files_count"] == 1
    assert rep_dict["total_files"] == 2


def test_build_contention_graph_on_clean_dir(tmp_path: Path) -> None:
    f = tmp_path / "test.txt"
    f.write_text("hello")

    report = build_contention_graph(str(tmp_path))
    assert report.target_path == str(tmp_path)
    assert len(report.contended_files) == 0
    assert "No active locks detected." in report.render_ascii()
    assert "Empty[\"No active locks\"]" in report.render_mermaid()
