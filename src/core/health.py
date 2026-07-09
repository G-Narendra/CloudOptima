"""Health check module for production readiness.

Provides endpoint-like health status for the application, including
dependency checks, version info, and uptime tracking.

Usage:
    from src.core.health import HealthRegistry, health_check

    registry = HealthRegistry.get_instance()
    status = registry.check_all()
"""

from __future__ import annotations
import logging
import time
import os
from typing import Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Status of a single health check component."""
    name: str
    status: str  # "ok", "degraded", "error"
    details: str = ""
    latency_ms: float = 0.0


@dataclass
class HealthReport:
    """Complete health report for the application."""
    status: str = "healthy"  # "healthy", "degraded", "unhealthy"
    version: str = "1.0.0"
    uptime_seconds: float = 0.0
    start_time: float = 0.0
    checks: list[HealthStatus] = field(default_factory=list)
    environment: str = "unknown"
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class HealthRegistry:
    """Singleton registry for health checks.

    Components register their health checks, and check_all()
    runs them all to produce a consolidated report.
    """

    _instance: Optional[HealthRegistry] = None
    _start_time: float = time.time()

    def __init__(self):
        self._checks: dict[str, callable] = {}

    @classmethod
    def get_instance(cls) -> HealthRegistry:
        """Get or create the global health registry singleton."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def get_uptime(cls) -> float:
        """Get seconds since application start."""
        return time.time() - cls._start_time

    def register(self, name: str, check_fn: callable):
        """Register a health check function.

        The function should return a HealthStatus object.
        """
        self._checks[name] = check_fn
        logger.debug(f"Registered health check: {name}")

    def unregister(self, name: str):
        """Remove a previously registered health check."""
        self._checks.pop(name, None)

    def check_all(self) -> HealthReport:
        """Run all registered health checks and produce a consolidated report."""
        env = "production"
        if os.environ.get("DEMO_MODE", "").lower() in ("true", "1"):
            env = "demo"

        report = HealthReport(
            environment=env,
            start_time=self._start_time,
            uptime_seconds=self.get_uptime(),
        )

        for name, check_fn in self._checks.items():
            try:
                start = time.monotonic()
                status = check_fn()
                elapsed = (time.monotonic() - start) * 1000

                # Handle non-HealthStatus returns gracefully
                if status is None:
                    report.checks.append(HealthStatus(
                        name=name,
                        status="error",
                        details="Health check returned None",
                    ))
                    report.status = "unhealthy"
                    continue

                # Handle unexpected return types
                if not hasattr(status, "status"):
                    report.checks.append(HealthStatus(
                        name=name,
                        status="error",
                        details=f"Health check returned unexpected type: {type(status).__name__}",
                    ))
                    report.status = "unhealthy"
                    continue

                status.latency_ms = round(elapsed, 2)
                report.checks.append(status)

                if status.status == "error":
                    report.status = "unhealthy"
                elif status.status == "degraded" and report.status != "unhealthy":
                    report.status = "degraded"

            except Exception as e:
                report.checks.append(HealthStatus(
                    name=name,
                    status="error",
                    details=f"Health check raised exception: {e}",
                ))
                report.status = "unhealthy"

        return report

    def check_to_dict(self) -> dict:
        """Run checks and return a plain dict (for JSON serialization)."""
        report = self.check_all()
        return {
            "status": report.status,
            "version": report.version,
            "environment": report.environment,
            "uptime_seconds": round(report.uptime_seconds, 1),
            "timestamp": report.timestamp,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status,
                    "details": c.details,
                    "latency_ms": c.latency_ms,
                }
                for c in report.checks
            ],
        }
