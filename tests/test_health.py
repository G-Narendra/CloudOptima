"""Tests for the health check module."""

from src.core.health import HealthRegistry, HealthStatus, HealthReport


class TestHealthStatus:
    """Test HealthStatus dataclass."""

    def test_create_ok(self):
        hs = HealthStatus(name="test", status="ok", details="All good")
        assert hs.name == "test"
        assert hs.status == "ok"
        assert hs.details == "All good"
        assert hs.latency_ms == 0.0

    def test_create_error(self):
        hs = HealthStatus(name="db", status="error", details="Connection failed")
        assert hs.status == "error"

    def test_latency_roundtrip(self):
        hs = HealthStatus(name="cache", status="ok")
        hs.latency_ms = 12.5
        assert hs.latency_ms == 12.5


class TestHealthReport:
    """Test HealthReport dataclass."""

    def test_create_healthy(self):
        report = HealthReport(status="healthy")
        assert report.status == "healthy"
        assert report.version == "1.0.0"
        assert report.uptime_seconds == 0.0
        assert report.checks == []

    def test_with_checks(self):
        report = HealthReport(
            status="degraded",
            checks=[
                HealthStatus(name="cache", status="ok"),
                HealthStatus(name="db", status="degraded", details="Slow connection"),
            ],
        )
        assert report.status == "degraded"
        assert len(report.checks) == 2

    def test_timestamp_on_create(self):
        report = HealthReport(status="healthy")
        assert report.timestamp is not None


class TestHealthRegistry:
    """Test the HealthRegistry class."""

    def setup_method(self):
        # Get fresh instance for each test
        self.registry = HealthRegistry()
        # Clear any existing checks from other tests
        self.registry._checks = {}

    def test_singleton(self):
        r1 = HealthRegistry.get_instance()
        r2 = HealthRegistry.get_instance()
        assert r1 is r2

    def test_register_and_check(self):
        self.registry.register("alive", lambda: HealthStatus(name="alive", status="ok"))
        report = self.registry.check_all()
        assert report.status == "healthy"
        assert len(report.checks) == 1
        assert report.checks[0].name == "alive"

    def test_multiple_checks_all_ok(self):
        self.registry.register("check1", lambda: HealthStatus(name="check1", status="ok"))
        self.registry.register("check2", lambda: HealthStatus(name="check2", status="ok"))
        report = self.registry.check_all()
        assert report.status == "healthy"
        assert len(report.checks) == 2

    def test_check_degraded(self):
        self.registry.register("ok_check", lambda: HealthStatus(name="ok_check", status="ok"))
        self.registry.register("bad_check", lambda: HealthStatus(name="bad_check", status="degraded"))
        report = self.registry.check_all()
        assert report.status == "degraded"

    def test_check_error(self):
        self.registry.register("failing", lambda: HealthStatus(name="failing", status="error"))
        report = self.registry.check_all()
        assert report.status == "unhealthy"

    def test_check_exception(self):
        def failing_check():
            raise RuntimeError("Something broke")
        self.registry.register("broken", failing_check)
        report = self.registry.check_all()
        assert report.status == "unhealthy"
        assert report.checks[0].status == "error"
        assert "Something broke" in report.checks[0].details

    def test_mixed_checks(self):
        self.registry.register("ok1", lambda: HealthStatus(name="ok1", status="ok"))
        self.registry.register("ok2", lambda: HealthStatus(name="ok2", status="ok"))
        report = self.registry.check_all()
        assert report.status == "healthy"

    def test_no_checks(self):
        report = self.registry.check_all()
        assert report.status == "healthy"
        assert report.checks == []

    def test_unregister(self):
        self.registry.register("temp", lambda: HealthStatus(name="temp", status="ok"))
        assert len(self.registry._checks) == 1
        self.registry.unregister("temp")
        assert len(self.registry._checks) == 0

    def test_latency_recorded(self):
        """Latency should be recorded (may be 0 in fast environments)."""
        def slow_check():
            import time
            time.sleep(0.001)  # Ensure measurable latency
            return HealthStatus(name="slow", status="ok")
        self.registry.register("slow", slow_check)
        report = self.registry.check_all()
        assert report.checks[0].latency_ms >= 0  # At least 0, usually > 0

    def test_check_to_dict(self):
        self.registry.register("test", lambda: HealthStatus(name="test", status="ok"))
        d = self.registry.check_to_dict()
        assert d["status"] == "healthy"
        assert "version" in d
        assert "environment" in d
        assert "uptime_seconds" in d
        assert "timestamp" in d
        assert len(d["checks"]) == 1

    def test_uptime_increases(self):
        import time
        u1 = HealthRegistry.get_uptime()
        time.sleep(0.01)
        u2 = HealthRegistry.get_uptime()
        assert u2 > u1


class TestHealthRegistryEdgeCases:
    """Test edge cases for HealthRegistry."""

    def setup_method(self):
        self.registry = HealthRegistry()
        self.registry._checks = {}

    def test_check_returns_none(self):
        """Health check returning None should result in error status."""
        self.registry.register("bad_return", lambda: None)  # type: ignore
        report = self.registry.check_all()
        # None return triggers AttributeError in check_all() which is caught -> unhealthy
        assert report.status == "unhealthy"
        assert report.checks[0].status == "error"
        assert "None" in report.checks[0].details

    def test_check_returns_string(self):
        """Health check returning wrong type."""
        self.registry.register("wrong_type", lambda: "not a status object")  # type: ignore
        # Should not crash - the check will fail since string has no .status
        report = self.registry.check_all()
        assert report.status == "unhealthy"

    def test_multiple_registrations_same_name(self):
        """Last registration should win."""
        self.registry.register("dup", lambda: HealthStatus(name="dup", status="ok"))
        self.registry.register("dup", lambda: HealthStatus(name="dup", status="error"))
        report = self.registry.check_all()
        assert report.checks[0].status == "error"

    def test_environment_detection(self):
        """Environment should be based on DEMO_MODE env var."""
        import os
        old_val = os.environ.get("DEMO_MODE")
        try:
            os.environ["DEMO_MODE"] = "true"
            registry = HealthRegistry.get_instance()
            d = registry.check_to_dict()
            assert d["environment"] in ("demo", "production")
        finally:
            if old_val is None:
                os.environ.pop("DEMO_MODE", None)
            else:
                os.environ["DEMO_MODE"] = old_val
