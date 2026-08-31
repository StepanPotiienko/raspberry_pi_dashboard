from django.core.management.base import BaseCommand
from raspberry_pi_htop.views import get_system_stats
from raspberry_pi_htop.models import SystemMetrics


class Command(BaseCommand):
    help = "Collect current system metrics and store them in the database. Run on a schedule."

    def handle(self, *args, **options):
        stats = get_system_stats()

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

        # Keep only the most recent 5000 records (~3.5 days at 1/min) to bound DB growth
        old_metrics = SystemMetrics.objects.all()[5000:]
        if old_metrics:
            SystemMetrics.objects.filter(id__in=[m.id for m in old_metrics]).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Collected metrics: CPU {stats['cpu']['percent']}%, "
                f"temp {stats['cpu']['temp']}°C"
            )
        )
