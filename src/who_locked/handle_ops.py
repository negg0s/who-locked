import ctypes
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

if sys.platform == "win32":
    from ctypes import wintypes
else:
    class _WinTypesFallback:
        DWORD = ctypes.c_uint32
        ULONG = ctypes.c_uint32
        USHORT = ctypes.c_uint16
        BOOL = ctypes.c_int
        HANDLE = ctypes.c_void_p

    wintypes = _WinTypesFallback()  # type: ignore

PROCESS_DUP_HANDLE = 0x0040
DUPLICATE_CLOSE_SOURCE = 0x00000001
DUPLICATE_SAME_ACCESS = 0x00000002
STATUS_INFO_LENGTH_MISMATCH = 0xC0000004
SystemExtendedHandleInformation = 64


class SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX(ctypes.Structure):
    _fields_ = [
        ("Object", ctypes.c_void_p),
        ("UniqueProcessId", ctypes.c_size_t),
        ("HandleValue", ctypes.c_size_t),
        ("GrantedAccess", wintypes.ULONG),
        ("CreatorBackTraceIndex", wintypes.USHORT),
        ("ObjectTypeIndex", wintypes.USHORT),
        ("HandleAttributes", wintypes.ULONG),
        ("Reserved", wintypes.ULONG),
    ]


def _setup_apis():
    if sys.platform != "win32":
        return None, None

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    ntdll = ctypes.WinDLL("ntdll", use_last_error=True)

    kernel32.GetCurrentProcess.restype = wintypes.HANDLE

    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE

    kernel32.DuplicateHandle.argtypes = [
        wintypes.HANDLE,
        wintypes.HANDLE,
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.HANDLE),
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.DWORD,
    ]
    kernel32.DuplicateHandle.restype = wintypes.BOOL

    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    kernel32.GetFinalPathNameByHandleW.argtypes = [
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    kernel32.GetFinalPathNameByHandleW.restype = wintypes.DWORD

    return kernel32, ntdll


def get_all_system_handles() -> Tuple[Optional[ctypes.Array], int]:
    """Retrieve raw table of all system handles via NtQuerySystemInformation."""
    if sys.platform != "win32":
        return None, 0

    _, ntdll = _setup_apis()
    if not ntdll:
        return None, 0

    size = wintypes.ULONG(8 * 1024 * 1024)
    buf = ctypes.create_string_buffer(size.value)

    while True:
        status = ntdll.NtQuerySystemInformation(
            SystemExtendedHandleInformation,
            buf,
            size,
            ctypes.byref(size),
        )
        if status == 0:
            break
        if (status & 0xFFFFFFFF) == STATUS_INFO_LENGTH_MISMATCH:
            new_size = max(size.value + 2 * 1024 * 1024, int(size.value * 1.5))
            size = wintypes.ULONG(new_size)
            buf = ctypes.create_string_buffer(size.value)
        else:
            return None, 0

    num_handles = ctypes.c_size_t.from_buffer_copy(buf[:8]).value
    return buf, num_handles


def find_file_handles_in_process(pid: int, target_path: str) -> List[int]:
    """Find handle values in a target process that reference the target file path."""
    if sys.platform != "win32":
        return []

    kernel32, _ = _setup_apis()
    if not kernel32:
        return []

    buf, num_handles = get_all_system_handles()
    if not buf or num_handles == 0:
        return []

    h_proc = kernel32.OpenProcess(PROCESS_DUP_HANDLE, False, pid)
    if not h_proc:
        return []

    cur_proc = kernel32.GetCurrentProcess()
    norm_target = os.path.normcase(os.path.abspath(target_path))
    entry_size = ctypes.sizeof(SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX)
    path_buf = (ctypes.c_wchar * 1024)()
    matching_handles: List[int] = []

    try:
        for i in range(num_handles):
            offset = 16 + i * entry_size
            entry = SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX.from_buffer_copy(buf[offset : offset + entry_size])
            if entry.UniqueProcessId == pid:
                dup = wintypes.HANDLE()
                res = kernel32.DuplicateHandle(
                    h_proc,
                    wintypes.HANDLE(entry.HandleValue),
                    cur_proc,
                    ctypes.byref(dup),
                    0,
                    False,
                    DUPLICATE_SAME_ACCESS,
                )
                if res and dup:
                    n = kernel32.GetFinalPathNameByHandleW(dup, path_buf, 1024, 0)
                    if n > 0:
                        path_str = path_buf.value
                        if path_str.startswith("\\\\?\\"):
                            path_str = path_str[4:]
                        if os.path.normcase(path_str) == norm_target:
                            matching_handles.append(entry.HandleValue)
                    kernel32.CloseHandle(dup)
    finally:
        kernel32.CloseHandle(h_proc)

    return matching_handles


def close_process_handle(pid: int, handle_value: int) -> bool:
    """Close a specific handle inside another process without terminating it."""
    if sys.platform != "win32":
        return False

    kernel32, _ = _setup_apis()
    if not kernel32:
        return False

    h_proc = kernel32.OpenProcess(PROCESS_DUP_HANDLE, False, pid)
    if not h_proc:
        return False

    try:
        # Calling DuplicateHandle with DUPLICATE_CLOSE_SOURCE closes handle in source process
        res = kernel32.DuplicateHandle(
            h_proc,
            wintypes.HANDLE(handle_value),
            0,
            None,
            0,
            False,
            DUPLICATE_CLOSE_SOURCE,
        )
        return bool(res)
    finally:
        kernel32.CloseHandle(h_proc)


def close_target_file_handles(target_path: str, pids: List[int]) -> Dict[str, Any]:
    """Locate and close handles for target_path across specified processes."""
    abs_target = os.path.abspath(target_path)
    closed_items = []
    total_closed = 0

    for pid in pids:
        handles = find_file_handles_in_process(pid, abs_target)
        proc_closed = 0
        for h in handles:
            if close_process_handle(pid, h):
                proc_closed += 1
                total_closed += 1
        if handles:
            closed_items.append({
                "pid": pid,
                "handles_found": len(handles),
                "handles_closed": proc_closed,
            })

    return {
        "target_path": abs_target,
        "total_closed": total_closed,
        "details": closed_items,
        "success": total_closed > 0,
    }
