import ctypes
import os
import sys
from typing import List, Optional

if sys.platform == "win32":
    from ctypes import wintypes
else:
    # Dummy types for linting or running on non-Windows test environments
    class _WinTypesFallback:
        DWORD = ctypes.c_uint32
        UINT = ctypes.c_uint32
        BOOL = ctypes.c_int
        FILETIME = ctypes.c_uint64

    wintypes = _WinTypesFallback()  # type: ignore

CCH_RM_SESSION_KEY = 32
CCH_RM_MAX_APP_NAME = 255
CCH_RM_MAX_SVC_NAME = 63

RM_APP_TYPES = {
    0: "Unknown",
    1: "MainWindow",
    2: "OtherWindow",
    3: "Service",
    4: "Explorer",
    5: "Console",
    1000: "Critical",
}

RM_APP_STATUSES = {
    0: "Unknown",
    1: "Running",
    2: "Stopped",
    4: "Restarted",
    8: "ErrorOnStop",
    16: "ErrorOnRestart",
    32: "ShutdownMasked",
}


class RM_UNIQUE_PROCESS(ctypes.Structure):
    _fields_ = [
        ("dwProcessId", wintypes.DWORD),
        ("ProcessStartTime", wintypes.FILETIME),
    ]


class RM_PROCESS_INFO(ctypes.Structure):
    _fields_ = [
        ("Process", RM_UNIQUE_PROCESS),
        ("strAppName", ctypes.c_wchar * (CCH_RM_MAX_APP_NAME + 1)),
        ("strServiceShortName", ctypes.c_wchar * (CCH_RM_MAX_SVC_NAME + 1)),
        ("ApplicationType", wintypes.DWORD),
        ("AppStatus", wintypes.DWORD),
        ("TSSessionId", wintypes.DWORD),
        ("bRestartable", wintypes.BOOL),
    ]


class RestartManagerSession:
    """Wrapper around Windows Restart Manager API session."""

    def __init__(self, rstrtmgr_dll: Optional[object] = None):
        self._dll = rstrtmgr_dll
        self._handle = wintypes.DWORD(0)
        self._key = (ctypes.c_wchar * (CCH_RM_SESSION_KEY + 1))()
        self._is_open = False

        if self._dll is None and sys.platform == "win32":
            try:
                self._dll = ctypes.WinDLL("rstrtmgr.dll")
            except OSError:
                self._dll = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def start(self) -> None:
        """Start a new Restart Manager session."""
        if not self._dll:
            raise RuntimeError("Restart Manager DLL is unavailable on this platform.")
        res = self._dll.RmStartSession(ctypes.byref(self._handle), 0, self._key)
        if res != 0:
            raise OSError(res, f"RmStartSession failed with error code {res}")
        self._is_open = True

    def register_resources(self, file_paths: List[str]) -> None:
        """Register file paths to inspect for active locks."""
        if not self._is_open:
            raise RuntimeError("Session is not open.")
        if not file_paths:
            return

        normalized = [os.path.abspath(p) for p in file_paths]
        arr_type = ctypes.c_wchar_p * len(normalized)
        file_arr = arr_type(*normalized)

        res = self._dll.RmRegisterResources(
            self._handle,
            len(normalized),
            file_arr,
            0,
            None,
            0,
            None,
        )
        if res != 0:
            raise OSError(res, f"RmRegisterResources failed with error code {res}")

    def get_locking_processes(self) -> List[RM_PROCESS_INFO]:
        """Fetch list of processes holding registered resources."""
        if not self._is_open:
            raise RuntimeError("Session is not open.")

        proc_needed = wintypes.UINT(0)
        proc_count = wintypes.UINT(0)
        reboot_reasons = wintypes.DWORD(0)

        # First call retrieves the required buffer size
        res = self._dll.RmGetList(
            self._handle,
            ctypes.byref(proc_needed),
            ctypes.byref(proc_count),
            None,
            ctypes.byref(reboot_reasons),
        )

        ERROR_MORE_DATA = 234
        if res == 0 or proc_needed.value == 0:
            return []

        if res != ERROR_MORE_DATA:
            raise OSError(res, f"RmGetList size query failed with error code {res}")

        buffer_size = proc_needed.value
        proc_array = (RM_PROCESS_INFO * buffer_size)()
        proc_count.value = buffer_size

        res2 = self._dll.RmGetList(
            self._handle,
            ctypes.byref(proc_needed),
            ctypes.byref(proc_count),
            proc_array,
            ctypes.byref(reboot_reasons),
        )
        if res2 != 0:
            raise OSError(res2, f"RmGetList failed with error code {res2}")

        return list(proc_array[: proc_count.value])

    def close(self) -> None:
        """End the Restart Manager session."""
        if self._is_open and self._dll:
            try:
                self._dll.RmEndSession(self._handle)
            finally:
                self._is_open = False
