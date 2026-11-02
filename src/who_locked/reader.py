"""Read and dump exclusively locked files by duplicating kernel handles."""

import ctypes
import os
import sys
from typing import List, Optional, Tuple

if sys.platform == "win32":
    from ctypes import wintypes
else:
    class _WinTypesFallback:
        DWORD = ctypes.c_uint32
        LONG = ctypes.c_int32
        BOOL = ctypes.c_int
        HANDLE = ctypes.c_void_p
        LPWSTR = ctypes.c_wchar_p

    wintypes = _WinTypesFallback()  # type: ignore

from .core import inspect_locks
from .handle_ops import (
    DUPLICATE_SAME_ACCESS,
    PROCESS_DUP_HANDLE,
    _setup_apis,
    get_process_file_handle_details,
)


def _read_from_duplicated_handle(dup_handle: wintypes.HANDLE, max_bytes: Optional[int] = None) -> bytes:
    """Read byte content from a duplicated Win32 file handle."""
    kernel32, _ = _setup_apis()
    if not kernel32:
        return b""

    kernel32.ReadFile.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    kernel32.ReadFile.restype = wintypes.BOOL

    kernel32.SetFilePointer.argtypes = [
        wintypes.HANDLE,
        wintypes.LONG,
        ctypes.POINTER(wintypes.LONG),
        wintypes.DWORD,
    ]
    kernel32.SetFilePointer.restype = wintypes.DWORD

    # Seek to beginning of file
    kernel32.SetFilePointer(dup_handle, 0, None, 0)

    chunks: List[bytes] = []
    chunk_size = 64 * 1024
    total_read = 0
    buf = ctypes.create_string_buffer(chunk_size)
    bytes_read = wintypes.DWORD()

    while True:
        to_read = chunk_size
        if max_bytes is not None:
            remaining = max_bytes - total_read
            if remaining <= 0:
                break
            to_read = min(chunk_size, remaining)

        success = kernel32.ReadFile(dup_handle, buf, to_read, ctypes.byref(bytes_read), None)
        if not success or bytes_read.value == 0:
            break

        chunks.append(buf.raw[: bytes_read.value])
        total_read += bytes_read.value

    return b"".join(chunks)


def read_locked_file(target_path: str, max_bytes: Optional[int] = None) -> bytes:
    """Read content of a file, using kernel handle duplication if locked exclusively."""
    abs_path = os.path.abspath(target_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"File not found: {abs_path}")

    # Step 1: try direct read first
    try:
        with open(abs_path, "rb") as handle:
            if max_bytes is not None:
                return handle.read(max_bytes)
            return handle.read()
    except (PermissionError, OSError):
        # File is locked exclusively or sharing violation occurred
        if sys.platform != "win32":
            raise

    # Step 2: identify locking processes and duplicate their open handle
    kernel32, _ = _setup_apis()
    if not kernel32:
        raise PermissionError(f"Cannot duplicate handle on non-Windows platform for {abs_path}")

    report = inspect_locks([abs_path])
    candidate_pids = [p.pid for p in report.locking_processes]

    cur_proc = kernel32.GetCurrentProcess()

    for pid in candidate_pids:
        handles = get_process_file_handle_details(pid, abs_path)
        if not handles:
            continue

        h_proc = kernel32.OpenProcess(PROCESS_DUP_HANDLE, False, pid)
        if not h_proc:
            continue

        try:
            for h_info in handles:
                dup = wintypes.HANDLE()
                ok = kernel32.DuplicateHandle(
                    h_proc,
                    wintypes.HANDLE(h_info.handle_value),
                    cur_proc,
                    ctypes.byref(dup),
                    0,
                    False,
                    DUPLICATE_SAME_ACCESS,
                )
                if ok and dup.value:
                    try:
                        data = _read_from_duplicated_handle(dup, max_bytes=max_bytes)
                        if data or os.path.getsize(abs_path) == 0:
                            return data
                    finally:
                        kernel32.CloseHandle(dup)
        finally:
            kernel32.CloseHandle(h_proc)

    raise PermissionError(f"Could not read {abs_path}: file is locked and readable handles could not be duplicated.")


def dump_locked_file(target_path: str, output_path: str, max_bytes: Optional[int] = None) -> int:
    """Read locked file content and save a copy to output_path."""
    data = read_locked_file(target_path, max_bytes=max_bytes)
    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(data)
    return len(data)


def format_hex_dump(data: bytes, bytes_per_line: int = 16) -> str:
    """Format raw binary bytes into a standard hex dump."""
    lines = []
    for offset in range(0, len(data), bytes_per_line):
        chunk = data[offset : offset + bytes_per_line]
        hex_parts = [f"{b:02x}" for b in chunk]
        hex_str = " ".join(hex_parts)
        ascii_parts = [chr(b) if 32 <= b < 127 else "." for b in chunk]
        ascii_str = "".join(ascii_parts)
        lines.append(f"{offset:08x}:  {hex_str:<48}  |{ascii_str}|")
    return "\n".join(lines)
