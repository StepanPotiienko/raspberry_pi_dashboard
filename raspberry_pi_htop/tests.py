from django.test import TestCase, Client
from django.utils import timezone
from django.urls import reverse

from .models import SystemMetrics, ProcessInfo
from . import views


def make_metric(**overrides):
    """Build a SystemMetrics row with all required fields defaulted."""
    defaults = dict(
        cpu_percent=12.5,
        cpu_temp=65.2,
        cpu_freq=1800.0,
        memory_percent=35.6,
        memory_used=2915401728,
        memory_total=8199643136,
        swap_percent=0.0,
        swap_used=0,
        swap_total=6442442752,
        disk_percent=80.0,
        disk_used=22496681984,
        disk_total=29346742272,
        network_bytes_sent=1000,
        network_bytes_recv=500,
        packets_dropped_in=0,
        packets_dropped_out=1,
        fan_speed=None,
    )
    defaults.update(overrides)
    return SystemMetrics.objects.create(**defaults)


class SystemMetricsModelTests(TestCase):
    def test_str_representation(self):
        self.assertIn("Metrics at", str(make_metric()))

    def test_default_timestamp(self):
        before = timezone.now() - timezone.timedelta(seconds=1)
        m = make_metric()
        after = timezone.now() + timezone.timedelta(seconds=1)
        self.assertTrue(before <= m.timestamp <= after)

    def test_ordering_most_recent_first(self):
        now = timezone.now()
        first = make_metric()
        older = make_metric(cpu_percent=5.0,
                            timestamp=now - timezone.timedelta(minutes=5))
        qs = SystemMetrics.objects.all()
        self.assertEqual(qs.first().pk, first.pk)
        self.assertEqual(qs.last().pk, older.pk)

    def test_optional_fields_nullable(self):
        m = make_metric(cpu_temp=None, cpu_freq=None, fan_speed=None)
        m.refresh_from_db()
        self.assertIsNone(m.cpu_temp)
        self.assertIsNone(m.cpu_freq)
        self.assertIsNone(m.fan_speed)


class ProcessInfoModelTests(TestCase):
    def test_str(self):
        p = ProcessInfo.objects.create(
            pid=1234,
            name="nginx",
            cpu_percent=12.3,
            memory_percent=4.5,
            status="running",
        )
        self.assertIn("nginx", str(p))
        self.assertIn("1234", str(p))


class DashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_dashboard_page_loads(self):
        resp = self.client.get(reverse("dashboard:main"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Raspberry Pi Dashboard")
        self.assertContains(resp, "systemChart")
        self.assertContains(resp, "process-table")

    def test_dashboard_has_auto_refresh_interval(self):
        """Poll at 3000ms (was 1000ms causing API queueing)."""
        content = self.client.get(reverse("dashboard:main")).content.decode()
        self.assertIn("}, 3000);", content)
        self.assertNotIn("}, 1000);", content)

    def test_dashboard_render_charts_from_recent_metrics(self):
        for _ in range(3):
            make_metric(cpu_percent=50.0, cpu_temp=30.0)
        resp = self.client.get(reverse("dashboard:main"))
        self.assertContains(resp, "50.0")


class APITests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_api_stats_returns_valid_json(self):
        resp = self.client.get(reverse("dashboard:api_stats"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/json")
        data = resp.json()
        for key in ["cpu", "memory", "swap", "disk", "network", "uptime"]:
            self.assertIn(key, data)
        self.assertIn("percent", data["cpu"])
        self.assertIn("percent", data["memory"])

    def test_api_stats_is_read_only(self):
        """The stats API must not write to the DB; persistence is the
        collect_metrics command's job (systemd timer)."""
        before = SystemMetrics.objects.count()
        self.client.get(reverse("dashboard:api_stats"))
        self.assertEqual(SystemMetrics.objects.count(), before)

    def test_api_processes_returns_list(self):
        resp = self.client.get(reverse("dashboard:api_processes"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("processes", data)
        self.assertIsInstance(data["processes"], list)

    def test_api_historical_data(self):
        now = timezone.now()
        make_metric(cpu_percent=10.0, memory_percent=20.0,
                    timestamp=now - timezone.timedelta(minutes=10))
        make_metric(cpu_percent=80.0, memory_percent=90.0,
                    timestamp=now - timezone.timedelta(hours=10))
        data = self.client.get(reverse("dashboard:api_historical")).json()
        self.assertEqual(data["cpu"], [10.0])
        self.assertEqual(data["memory"], [20.0])

    def test_api_historical_respects_hours_param(self):
        make_metric(cpu_percent=5.0,
                    timestamp=timezone.now() - timezone.timedelta(hours=3))
        data = self.client.get(
            reverse("dashboard:api_historical"), {"hours": 24}).json()
        self.assertEqual(data["cpu"], [5.0])


class ViewsUnitTests(TestCase):
    def test_get_top_processes_sorts_and_limits(self):
        procs = views.get_top_processes(limit=5)
        self.assertIsInstance(procs, list)
        self.assertLessEqual(len(procs), 5)
        cpu_vals = [p.get("cpu_percent") or 0 for p in procs]
        self.assertEqual(cpu_vals, sorted(cpu_vals, reverse=True))

    def test_get_system_stats_shape(self):
        stats = views.get_system_stats()
        self.assertIn("cpu", stats)
        self.assertIn("memory", stats)
        self.assertIn("disk", stats)
        self.assertIn("network", stats)
        self.assertIn("per_core", stats["cpu"])
        self.assertEqual(len(stats["cpu"]["per_core"]), stats["cpu"]["count"])


class GetTempSummaryTests(TestCase):
    def test_no_data_returns_nulls(self):
        summary = views.get_temp_summary(hours=24)
        self.assertEqual(summary, {"avg": None, "peak": None, "min": None, "count": 0})

    def test_all_null_temps_returns_count_zero(self):
        make_metric(cpu_temp=None)
        summary = views.get_temp_summary(hours=24)
        self.assertEqual(summary["count"], 0)
        self.assertIsNone(summary["avg"])

    def test_excludes_null_temps(self):
        make_metric(cpu_temp=60.0)
        make_metric(cpu_temp=None)
        summary = views.get_temp_summary(hours=24)
        self.assertEqual(summary["count"], 1)
        self.assertEqual(summary["avg"], 60.0)

    def test_computes_avg_peak_min(self):
        make_metric(cpu_temp=30.0)
        make_metric(cpu_temp=50.0)
        make_metric(cpu_temp=70.0)
        summary = views.get_temp_summary(hours=24)
        self.assertEqual(summary["count"], 3)
        self.assertEqual(summary["avg"], 50.0)
        self.assertEqual(summary["peak"], 70.0)
        self.assertEqual(summary["min"], 30.0)

    def test_excludes_rows_outside_window(self):
        make_metric(cpu_temp=40.0,
                    timestamp=timezone.now() - timezone.timedelta(hours=48))
        make_metric(cpu_temp=80.0)
        summary = views.get_temp_summary(hours=24)
        self.assertEqual(summary["count"], 1)
        self.assertEqual(summary["avg"], 80.0)


class CollectMetricsCommandTests(TestCase):
    def test_command_creates_metric_row(self):
        from django.core.management import call_command
        before = SystemMetrics.objects.count()
        call_command("collect_metrics", verbosity=0)
        self.assertEqual(SystemMetrics.objects.count(), before + 1)


class ApiHistoricalDataTests(TestCase):
    def test_invalid_hours_clamped_to_default(self):
        make_metric(cpu_percent=10.0)
        data = self.client.get(
            reverse("dashboard:api_historical"), {"hours": "abc"}).json()
        self.assertIn("cpu", data)

    def test_temp_preserves_nulls(self):
        make_metric(cpu_temp=None, cpu_percent=5.0)
        make_metric(cpu_temp=0.0, cpu_percent=6.0)
        data = self.client.get(
            reverse("dashboard:api_historical"), {"hours": 1}).json()
        self.assertEqual(len(data["temp"]), len(data["timestamps"]))
        # A legitimate 0.0 reading must survive, not be dropped.
        self.assertIn(0.0, data["temp"])

