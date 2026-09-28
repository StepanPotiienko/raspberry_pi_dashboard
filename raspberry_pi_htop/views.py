from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Avg, Max, Min, Count
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import psutil
import platform
import os
import logging
from .models import SystemMetrics, ProcessInfo

logger = logging.getLogger(__name__)


def get_cpu_temperature():
    """Get CPU temperature - works on Raspberry Pi"""
    try:
        # Try Raspberry Pi method
        if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = float(f.read()) / 1000.0
                return round(temp, 1)
    except (OSError, ValueError):
        logger.warning("Failed to read CPU temperature from sysfs", exc_info=True)

    # Try psutil sensors (might work on some systems)
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for name, entries in temps.items():
                if entries:
                    return round(entries[0].current, 1)
    except (OSError, AttributeError, RuntimeError):
        logger.warning("Failed to read CPU temperature via psutil", exc_info=True)

    return None


def get_fan_speed():
    """Get fan speed if available"""
    try:
        fans = psutil.sensors_fans()
        if fans:
            for name, entries in fans.items():
                if entries:
                    return entries[0].current
    except (OSError, AttributeError, RuntimeError):
        logger.warning("Failed to read fan speed via psutil", exc_info=True)
    return None


def get_system_stats():
    """Collect current system statistics"""
    # CPU metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_freq = psutil.cpu_freq()
    cpu_temp = get_cpu_temperature()
    cpu_count = psutil.cpu_count()
    cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)

    # Memory metrics
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()

    # Disk metrics
    disk = psutil.disk_usage("/")

    # Network metrics
    network = psutil.net_io_counters()

    # Fan speed
    fan_speed = get_fan_speed()

    # System info
    boot_time = psutil.boot_time()
    uptime = timezone.now().timestamp() - boot_time

    return {
        "cpu": {
            "percent": cpu_percent,
            "temp": cpu_temp,
            "freq": cpu_freq.current if cpu_freq else None,
            "count": cpu_count,
            "per_core": cpu_per_core,
        },
        "memory": {
            "percent": memory.percent,
            "used": memory.used,
            "total": memory.total,
            "available": memory.available,
        },
        "swap": {
            "percent": swap.percent,
            "used": swap.used,
            "total": swap.total,
        },
        "disk": {
            "percent": disk.percent,
            "used": disk.used,
            "total": disk.total,
            "free": disk.free,
        },
        "network": {
            "bytes_sent": network.bytes_sent,
            "bytes_recv": network.bytes_recv,
            "packets_sent": network.packets_sent,
            "packets_recv": network.packets_recv,
            "packets_dropped_in": network.dropin,
            "packets_dropped_out": network.dropout,
        },
        "fan_speed": fan_speed,
        "uptime": uptime,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
    }


def get_top_processes(limit=10):
    """Get top processes by CPU usage"""
    processes = []
    for proc in psutil.process_iter(
        ["pid", "name", "cpu_percent", "memory_percent", "status"]
    ):
        try:
            pinfo = proc.info
            processes.append(pinfo)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # Sort by CPU usage (handle None values)
    processes.sort(key=lambda x: x.get("cpu_percent") or 0, reverse=True)
    return processes[:limit]


def dashboard(request):
    """Main dashboard view"""
    stats = get_system_stats()
    top_processes = get_top_processes(10)

    # Get recent metrics for charts (last 20 entries)
    recent_metrics = SystemMetrics.objects.all()[:20]

    # Temperature summary over the last 24h (avg / peak / min)
    temp_summary = get_temp_summary(hours=24)

    context = {
        "stats": stats,
        "processes": top_processes,
        "recent_metrics": list(
            reversed(recent_metrics)
        ),  # Reverse for chronological order
        "temp_summary": temp_summary,
    }

    return render(request, "dashboard/main.html", context)


def get_temp_summary(hours=24):
    """Compute avg / peak / min CPU temperature over the last N hours."""
    since = timezone.now() - timedelta(hours=hours)
    summary = SystemMetrics.objects.filter(
        timestamp__gte=since,
        cpu_temp__isnull=False,
    ).aggregate(
        avg=Avg("cpu_temp"),
        peak=Max("cpu_temp"),
        min=Min("cpu_temp"),
        count=Count("cpu_temp"),
    )
    count = summary["count"] or 0
    if not count:
        return {"avg": None, "peak": None, "min": None, "count": 0}
    return {
        "avg": round(summary["avg"], 1),
        "peak": round(summary["peak"], 1),
        "min": round(summary["min"], 1),
        "count": count,
    }


def save_metrics(stats, keep=5000):
    """Persist a stats dict to a SystemMetrics row and prune old rows.

    Keeps the most recent `keep` rows. Pruning uses a pk-only slice so it
    never materializes full model instances for the stale rows.
    """
    SystemMetrics.objects.create(
        cpu_percent=stats["cpu"]["percent"],
        cpu_temp=stats["cpu"]["temp"],
        cpu_freq=stats["cpu"]["freq"],
        memory_percent=stats["memory"]["percent"],
        memory_used=stats["memory"]["used"],
        memory_total=stats["memory"]["total"],
        swap_percent=stats["swap"]["percent"],
        swap_used=stats["swap"]["used"],
        swap_total=stats["swap"]["total"],
        disk_percent=stats["disk"]["percent"],
        disk_used=stats["disk"]["used"],
        disk_total=stats["disk"]["total"],
        network_bytes_sent=stats["network"]["bytes_sent"],
        network_bytes_recv=stats["network"]["bytes_recv"],
        packets_dropped_in=stats["network"]["packets_dropped_in"],
        packets_dropped_out=stats["network"]["packets_dropped_out"],
        fan_speed=stats["fan_speed"],
    )

    stale_pks = list(
        SystemMetrics.objects.order_by("-timestamp")
        .values_list("pk", flat=True)[keep:]
    )
    if stale_pks:
        with transaction.atomic():
            SystemMetrics.objects.filter(pk__in=stale_pks).delete()


def api_system_stats(request):
    """API endpoint for real-time system stats (read-only).

    Persistence is handled by the `collect_metrics` management command on a
    systemd timer, so this endpoint must not write on every poll.
    """
    return JsonResponse(get_system_stats())


def api_processes(request):
    """API endpoint for process information"""
    processes = get_top_processes(15)
    return JsonResponse({"processes": processes})


def api_historical_data(request):
    """API endpoint for historical metrics."""
    try:
        hours = int(request.GET.get("hours", 1))
    except (TypeError, ValueError):
        hours = 1
    hours = max(1, min(hours, 168))  # clamp to 1..168 (1 week)
    since = timezone.now() - timedelta(hours=hours)

    rows = list(
        SystemMetrics.objects.filter(timestamp__gte=since)
        .order_by("timestamp")
        .values_list(
            "timestamp", "cpu_percent", "memory_percent", "disk_percent", "cpu_temp"
        )
    )

    data = {
        "timestamps": [r[0].isoformat() for r in rows],
        "cpu": [r[1] for r in rows],
        "memory": [r[2] for r in rows],
        "disk": [r[3] for r in rows],
        # Preserve nulls for alignment; do not drop legitimate 0.0 readings.
        "temp": [r[4] for r in rows],
    }

    return JsonResponse(data)
