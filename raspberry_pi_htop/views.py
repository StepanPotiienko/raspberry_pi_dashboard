from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
import psutil
import platform
import os
from .models import SystemMetrics, ProcessInfo


def get_cpu_temperature():
    """Get CPU temperature - works on Raspberry Pi"""
    try:
        # Try Raspberry Pi method
        if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = float(f.read()) / 1000.0
                return round(temp, 1)
    except:
        pass

    # Try psutil sensors (might work on some systems)
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for name, entries in temps.items():
                if entries:
                    return round(entries[0].current, 1)
    except:
        pass

    return None


def get_fan_speed():
    """Get fan speed if available"""
    try:
        fans = psutil.sensors_fans()
        if fans:
            for name, entries in fans.items():
                if entries:
                    return entries[0].current
    except:
        pass
    return None


def get_system_stats():
    """Collect current system statistics"""
    # CPU metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_freq = psutil.cpu_freq()
    cpu_temp = get_cpu_temperature()
    cpu_count = psutil.cpu_count()
    cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)

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

    context = {
        "stats": stats,
        "processes": top_processes,
        "recent_metrics": list(
            reversed(recent_metrics)
        ),  # Reverse for chronological order
    }

    return render(request, "dashboard/main.html", context)


def api_system_stats(request):
    """API endpoint for real-time system stats"""
    stats = get_system_stats()

    # Save to database
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

    # Clean old records (keep last 1000)
    old_metrics = SystemMetrics.objects.all()[1000:]
    if old_metrics:
        SystemMetrics.objects.filter(id__in=[m.id for m in old_metrics]).delete()

    return JsonResponse(stats)


def api_processes(request):
    """API endpoint for process information"""
    processes = get_top_processes(15)
    return JsonResponse({"processes": processes})


def api_historical_data(request):
    """API endpoint for historical metrics"""
    hours = int(request.GET.get("hours", 1))
    since = timezone.now() - timedelta(hours=hours)

    metrics = SystemMetrics.objects.filter(timestamp__gte=since).order_by("timestamp")

    data = {
        "timestamps": [m.timestamp.isoformat() for m in metrics],
        "cpu": [m.cpu_percent for m in metrics],
        "memory": [m.memory_percent for m in metrics],
        "disk": [m.disk_percent for m in metrics],
        "temp": [m.cpu_temp for m in metrics if m.cpu_temp],
    }

    return JsonResponse(data)
