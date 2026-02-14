"""Real system stats via psutil."""

import psutil
from dataclasses import dataclass


@dataclass
class SystemStats:
    cpu_percent: float
    ram_used_gb: float
    ram_total_gb: float
    ram_percent: float
    disk_used_gb: float
    disk_total_gb: float
    disk_percent: float
    cpu_count: int


def get_system_stats() -> SystemStats:
    """Collect current system statistics. Non-blocking."""
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return SystemStats(
        cpu_percent=psutil.cpu_percent(interval=None),
        ram_used_gb=round(mem.used / (1024**3), 1),
        ram_total_gb=round(mem.total / (1024**3), 1),
        ram_percent=mem.percent,
        disk_used_gb=round(disk.used / (1024**3), 0),
        disk_total_gb=round(disk.total / (1024**3), 0),
        disk_percent=round(disk.percent, 1),
        cpu_count=psutil.cpu_count() or 1,
    )
