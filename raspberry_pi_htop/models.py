from django.db import models
from django.utils import timezone


class SystemMetrics(models.Model):
    """Store historical system metrics for trending"""

    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    # CPU metrics
    cpu_percent = models.FloatField(help_text="Overall CPU usage percentage")
    cpu_temp = models.FloatField(
        null=True, blank=True, help_text="CPU temperature in Celsius"
    )
    cpu_freq = models.FloatField(
        null=True, blank=True, help_text="CPU frequency in MHz"
    )

    # Memory metrics
    memory_percent = models.FloatField(help_text="RAM usage percentage")
    memory_used = models.BigIntegerField(help_text="Used memory in bytes")
    memory_total = models.BigIntegerField(help_text="Total memory in bytes")

    # Swap metrics
    swap_percent = models.FloatField(help_text="Swap usage percentage")
    swap_used = models.BigIntegerField(help_text="Used swap in bytes")
    swap_total = models.BigIntegerField(help_text="Total swap in bytes")

    # Disk metrics
    disk_percent = models.FloatField(help_text="Disk usage percentage")
    disk_used = models.BigIntegerField(help_text="Used disk space in bytes")
    disk_total = models.BigIntegerField(help_text="Total disk space in bytes")

    # Network metrics
    network_bytes_sent = models.BigIntegerField(help_text="Total bytes sent")
    network_bytes_recv = models.BigIntegerField(help_text="Total bytes received")

    # Fan speed (if available)
    fan_speed = models.IntegerField(null=True, blank=True, help_text="Fan speed in RPM")

    class Meta:
        ordering = ["-timestamp"]
        verbose_name_plural = "System Metrics"
        indexes = [
            models.Index(fields=["-timestamp"]),
        ]

    def __str__(self):
        return f"Metrics at {self.timestamp}"


class ProcessInfo(models.Model):
    """Store information about running processes"""

    timestamp = models.DateTimeField(default=timezone.now)
    pid = models.IntegerField(help_text="Process ID")
    name = models.CharField(max_length=255, help_text="Process name")
    cpu_percent = models.FloatField(help_text="CPU usage percentage")
    memory_percent = models.FloatField(help_text="Memory usage percentage")
    status = models.CharField(max_length=50, help_text="Process status")

    class Meta:
        ordering = ["-cpu_percent"]
        verbose_name_plural = "Process Information"

    def __str__(self):
        return f"{self.name} (PID: {self.pid})"
