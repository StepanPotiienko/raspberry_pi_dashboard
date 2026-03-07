from django.contrib import admin
from .models import SystemMetrics, ProcessInfo


@admin.register(SystemMetrics)
class SystemMetricsAdmin(admin.ModelAdmin):
    list_display = [
        "timestamp",
        "cpu_percent",
        "cpu_temp",
        "memory_percent",
        "disk_percent",
    ]
    list_filter = ["timestamp"]
    date_hierarchy = "timestamp"
    readonly_fields = ["timestamp"]
    ordering = ["-timestamp"]


@admin.register(ProcessInfo)
class ProcessInfoAdmin(admin.ModelAdmin):
    list_display = [
        "timestamp",
        "pid",
        "name",
        "cpu_percent",
        "memory_percent",
        "status",
    ]
    list_filter = ["status", "timestamp"]
    search_fields = ["name", "pid"]
    ordering = ["-cpu_percent"]
