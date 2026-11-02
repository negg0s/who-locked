import os
from pathlib import Path
import pytest

from who_locked.reader import dump_locked_file, format_hex_dump, read_locked_file


def test_format_hex_dump() -> None:
    data = b"Hello, Windows!\x00\x01\x02"
    result = format_hex_dump(data)
    assert "00000000:" in result
    assert "48 65 6c 6c 6f" in result
    assert "|Hello, Windows!.|" in result
    assert "|..|" in result


def test_read_and_dump_free_file(tmp_path: Path) -> None:
    test_file = tmp_path / "hello.txt"
    test_file.write_text("Plain unblocked text content.")

    data = read_locked_file(str(test_file))
    assert data == b"Plain unblocked text content."

    partial = read_locked_file(str(test_file), max_bytes=5)
    assert partial == b"Plain"

    out_file = tmp_path / "dumped.txt"
    count = dump_locked_file(str(test_file), str(out_file))
    assert count == len(b"Plain unblocked text content.")
    assert out_file.read_bytes() == b"Plain unblocked text content."


def test_read_nonexistent_file(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.bin"
    with pytest.raises(FileNotFoundError):
        read_locked_file(str(missing))
