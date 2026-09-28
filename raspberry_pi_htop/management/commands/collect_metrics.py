from django.core.management.base import BaseCommand
from raspberry_pi_htop.views import get_system_stats, save_metrics


class Command(BaseCommand):
    help = "Collect current system metrics and store them in the database. Run on a schedule."

    def handle(self, *args, **options):
        stats = get_system_stats()
        save_metrics(stats, keep=5000)

        self.stdout.write(
            self.style.SUCCESS(
                f"Collected metrics: CPU {stats['cpu']['percent']}%, "
                f"temp {stats['cpu']['temp']}°C"
            )
        )
