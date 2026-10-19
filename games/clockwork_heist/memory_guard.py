"""Keeps simulation runs inside a share of system RAM (default 80%).

- `workers_within_budget` sizes a worker pool so the estimated total fits the budget.
- `MemoryWatchdog` checks system memory while a run is going; past the limit it stops
  every child process and exits with code 3 instead of letting the machine swap.
"""

import ctypes
import os
import sys
import threading
import time
from multiprocessing import active_children

DEFAULT_LIMIT = 0.80
EXIT_MEMORY = 3


def system_memory() -> tuple:
    """(total, available) physical memory in bytes."""
    if sys.platform == "win32":

        class MemoryStatusEx(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatusEx()
        status.dwLength = ctypes.sizeof(MemoryStatusEx)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise OSError("GlobalMemoryStatusEx failed")
        return status.ullTotalPhys, status.ullAvailPhys

    if os.path.exists("/proc/meminfo"):
        info = {}
        with open("/proc/meminfo", "r", encoding="UTF-8") as file:
            for line in file:
                key, value = line.split(":", 1)
                info[key] = int(value.split()[0]) * 1024
        return info["MemTotal"], info.get("MemAvailable", info["MemFree"])

    page = os.sysconf("SC_PAGE_SIZE")
    return os.sysconf("SC_PHYS_PAGES") * page, os.sysconf("SC_AVPHYS_PAGES") * page


def memory_load() -> float:
    """Share of physical memory in use, 0..1."""
    total, available = system_memory()
    return 1 - available / total


def workers_within_budget(requested: int, per_worker_bytes: int, limit: float = DEFAULT_LIMIT) -> int:
    """Largest worker count <= `requested` whose estimated memory keeps total use under `limit`."""
    total, available = system_memory()
    headroom = limit * total - (total - available)
    if headroom < per_worker_bytes:
        raise MemoryError(
            f"Memory already at {memory_load():.0%}; one worker needs {per_worker_bytes / 2**20:.0f} MB "
            f"and the limit is {limit:.0%}"
        )
    return max(1, min(requested, int(headroom // per_worker_bytes)))


class MemoryWatchdog:
    """Context manager: stops the run if system memory use passes `limit`."""

    def __init__(self, limit: float = DEFAULT_LIMIT, interval: float = 2.0):
        self.limit = limit
        self.interval = interval
        self.peak = memory_load()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._watch, name="memory-watchdog", daemon=True)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._thread.join()
        return False

    def _watch(self) -> None:
        while not self._stop.wait(self.interval):
            load = memory_load()
            self.peak = max(self.peak, load)
            if load > self.limit:
                print(f"\nMemory use {load:.0%} passed the {self.limit:.0%} limit; stopping the run.", flush=True)
                for child in active_children():
                    child.terminate()
                time.sleep(0.5)
                os._exit(EXIT_MEMORY)
