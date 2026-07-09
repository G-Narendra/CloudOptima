"""Observability, Tracing & Audit Trail System.

Provides structured logging, workflow tracing, performance tracking,
and audit logging across all agent interactions.

Error handling philosophy:
- External failures (Sentry, disk I/O) are caught and logged — never crash the main flow
- Log messages include context (function name, session_id, event type) for debugging
- Breadcrumb/logging failures are logged at DEBUG level (they're non-critical)
"""

from __future__ import annotations
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Any
from pathlib import Path


logger = logging.getLogger(__name__)

# ─── Trace Event Types ──────────────────────────────────────────────────


class TraceEventType(str, Enum):
    SESSION_START = "session.start"
    SESSION_END = "session.end"
    AGENT_START = "agent.start"
    AGENT_END = "agent.end"
    AGENT_ERROR = "agent.error"
    LLM_CALL_START = "llm.call.start"
    LLM_CALL_END = "llm.call.end"
    LLM_CALL_ERROR = "llm.call.error"
    CONFLICT_DETECTED = "conflict.detected"
    ARBITRATION_START = "arbitration.start"
    ARBITRATION_END = "arbitration.end"
    ARTIFACT_GENERATED = "artifact.generated"
    HUMAN_APPROVAL = "human.approval"
    API_CALL = "api.call"
    ERROR = "error"


@dataclass
class TraceEvent:
    """A single trace event in the workflow."""
    event_type: TraceEventType
    session_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    parent_trace_id: Optional[str] = None
    agent_type: Optional[str] = None
    duration_ms: Optional[float] = None
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


# ─── Tracer ─────────────────────────────────────────────────────────────


class WorkflowTracer:
    """Records and exports trace events for the entire agent workflow.

    Supports in-memory buffering and optional file export.
    Compatible with OpenTelemetry-style span export.
    """

    def __init__(self, export_path: Optional[str] = None):
        self.events: list[TraceEvent] = []
        self._call_stack: dict[str, float] = {}  # trace_id -> start_time
        self.export_path = export_path
        if export_path:
            Path(export_path).mkdir(parents=True, exist_ok=True)

    def record(self, event: TraceEvent) -> str:
        """Record a trace event and return its trace_id.

        Also emits a Sentry breadcrumb for production error context.
        Sentry failures are logged at DEBUG level — they never crash the main flow.
        """
        self.events.append(event)
        logger.debug(f"[TRACE] {event.event_type.value} | session={event.session_id[:12]} | "
                      f"agent={event.agent_type or '-'} | duration={event.duration_ms or '-'}ms")

        # Emit Sentry breadcrumb for production error context (best-effort)
        try:
            from src.core.sentry import add_breadcrumb
            breadcrumb_data: dict[str, Any] = {
                "session_id": event.session_id[:12],
                "trace_id": event.trace_id[:8],
            }
            if event.duration_ms is not None:
                breadcrumb_data["duration_ms"] = event.duration_ms
            if event.metadata:
                breadcrumb_data.update({k: str(v)[:50] for k, v in event.metadata.items()})

            level = "info"
            if event.event_type in (TraceEventType.ERROR, TraceEventType.AGENT_ERROR, TraceEventType.LLM_CALL_ERROR):
                level = "error"

            add_breadcrumb(
                message=f"{event.event_type.value}: {event.agent_type or 'system'}",
                category="trace",
                level=level,
                data=breadcrumb_data,
            )
        except ImportError as e:
            logger.debug(f"Sentry module not available for breadcrumb: {e}")
        except Exception as e:
            logger.debug(f"Failed to emit Sentry breadcrumb (non-critical): {e}")

        return event.trace_id

    def start_span(self, event_type: TraceEventType, session_id: str,
                   agent_type: Optional[str] = None, **metadata) -> str:
        """Start a timed span. Returns trace_id."""
        event = TraceEvent(
            event_type=event_type,
            session_id=session_id,
            agent_type=agent_type,
            metadata=metadata,
        )
        self._call_stack[event.trace_id] = time.monotonic()
        self.record(event)
        return event.trace_id

    def end_span(self, trace_id: str, output_summary: Optional[str] = None,
                 error: Optional[str] = None):
        """End a timed span. Calculates duration."""
        start_time = self._call_stack.pop(trace_id, None)
        if start_time is None:
            logger.warning(f"Attempted to end unknown span: {trace_id}")
            return

        duration_ms = (time.monotonic() - start_time) * 1000

        for event in self.events:
            if event.trace_id == trace_id:
                event.duration_ms = duration_ms
                event.output_summary = output_summary
                event.error = error
                break

    def get_session_trace(self, session_id: str) -> list[dict]:
        """Get all trace events for a session, ordered by time."""
        return [
            e.to_dict() for e in self.events
            if e.session_id == session_id
        ]

    def export_to_file(self, session_id: str):
        """Export session trace to JSON file.

        Creates a timestamped file in the export directory.
        Best-effort — failures are logged but never crash.
        """
        if not self.export_path:
            logger.debug("No export path configured — skipping trace file export")
            return

        try:
            trace = self.get_session_trace(session_id)
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            filename = f"{self.export_path}/trace_{session_id}_{timestamp}.json"
            with open(filename, "w") as f:
                json.dump(trace, f, indent=2, default=str)
            logger.info(f"Trace exported to {filename}")
        except PermissionError as e:
            logger.warning(f"Permission denied writing trace file: {e}")
        except OSError as e:
            logger.warning(f"OS error writing trace file: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error exporting trace: {e}")

    def get_session_summary(self, session_id: str) -> dict:
        """Get a human-readable summary of the session trace."""
        events = self.get_session_trace(session_id)
        if not events:
            return {"session_id": session_id, "events": 0}

        agent_events = [e for e in events if e.get("agent_type")]
        llm_calls = [e for e in events if e["event_type"] == TraceEventType.LLM_CALL_END.value]
        conflicts = [e for e in events if e["event_type"] == TraceEventType.CONFLICT_DETECTED.value]
        errors = [e for e in events if e.get("error")]

        total_duration = sum(e.get("duration_ms", 0) or 0 for e in events)

        return {
            "session_id": session_id,
            "total_events": len(events),
            "agent_interactions": len(agent_events),
            "llm_calls": len(llm_calls),
            "conflicts_detected": len(conflicts),
            "errors": len(errors),
            "total_duration_ms": total_duration,
            "agents_involved": list(set(e["agent_type"] for e in agent_events if e.get("agent_type"))),
            "first_event": events[0].get("timestamp") if events else None,
            "last_event": events[-1].get("timestamp") if events else None,
        }

    def export_opentelemetry(self, session_id: str) -> list[dict]:
        """Export traces in OpenTelemetry-compatible format."""
        events = self.get_session_trace(session_id)
        otel_spans = []
        for e in events:
            span = {
                "traceId": e["trace_id"],
                "spanId": uuid.uuid4().hex[:16],
                "parentSpanId": e.get("parent_trace_id", ""),
                "name": e["event_type"],
                "startTime": e["timestamp"],
                "endTime": e["timestamp"],
                "attributes": {
                    "session.id": e["session_id"],
                    "agent.type": e.get("agent_type", ""),
                    "duration.ms": e.get("duration_ms", 0),
                    "error": e.get("error", ""),
                },
            }
            otel_spans.append(span)
        return {"resourceSpans": [{"scopeSpans": [{"spans": otel_spans}]}]}


# ─── Global Tracer Instance ──────────────────────────────────────────────

_tracer: Optional[WorkflowTracer] = None


def get_tracer() -> WorkflowTracer:
    """Get or create the global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = WorkflowTracer(export_path=".freebuff/traces")
    return _tracer


def reset_tracer():
    """Reset the global tracer (useful for testing)."""
    global _tracer
    _tracer = None


# ─── Session Audit Logger ───────────────────────────────────────────────


class AuditLogger:
    """Structured audit log for compliance and review purposes.

    Logs every significant decision with supporting evidence.
    Immutable after writing (append-only).
    """

    def __init__(self, log_dir: str = ".freebuff/audit"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_decision(self, session_id: str, decision_type: str,
                     agent: str, rationale: str,
                     evidence: Optional[dict] = None):
        """Log a decision with supporting evidence.

        Also emits a Sentry breadcrumb for audit trail context.
        Both disk I/O and Sentry failures are caught and logged.
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "decision_type": decision_type,
            "agent": agent,
            "rationale": rationale,
            "evidence": evidence or {},
            "log_id": uuid.uuid4().hex[:16],
        }

        try:
            filename = self.log_dir / f"{session_id}.audit.jsonl"
            with open(filename, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except (PermissionError, OSError) as e:
            logger.warning(f"Failed to write audit log entry: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error writing audit log: {e}")

        logger.info(f"[AUDIT] {decision_type} | session={session_id[:12]} | agent={agent}")

        # Emit Sentry breadcrumb for audit trail context (best-effort)
        try:
            from src.core.sentry import add_breadcrumb

            level = "info"
            if "error" in decision_type.lower() or "reject" in decision_type.lower():
                level = "warning"

            breadcrumb_data: dict[str, Any] = {
                "session_id": session_id[:12],
                "decision_type": decision_type,
                "agent": agent,
                "rationale": rationale[:200],
            }
            if evidence:
                breadcrumb_data.update({k: str(v)[:50] for k, v in evidence.items()})

            add_breadcrumb(
                message=f"audit.{decision_type}: {agent}",
                category="audit",
                level=level,
                data=breadcrumb_data,
            )
        except ImportError as e:
            logger.debug(f"Sentry module not available for audit breadcrumb: {e}")
        except Exception as e:
            logger.debug(f"Failed to emit Sentry audit breadcrumb (non-critical): {e}")

        return entry["log_id"]

    def get_session_log(self, session_id: str) -> list[dict]:
        """Read all audit entries for a session."""
        filename = self.log_dir / f"{session_id}.audit.jsonl"
        if not filename.exists():
            return []

        try:
            entries = []
            with open(filename) as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))
            return entries
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to read audit log for {session_id}: {e}")
            return []
        except Exception as e:
            logger.warning(f"Unexpected error reading audit log: {e}")
            return []


_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create the global audit logger."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


# ─── Performance Metrics ────────────────────────────────────────────────


@dataclass
class PerfMetrics:
    """Aggregated performance metrics for a session."""
    session_id: str
    total_duration_ms: float = 0.0
    agent_durations: dict[str, float] = field(default_factory=dict)
    llm_call_count: int = 0
    avg_llm_latency_ms: float = 0.0
    conflict_count: int = 0
    artifact_count: int = 0


class MetricsCollector:
    """Collects and aggregates performance metrics."""

    def __init__(self):
        self.metrics: dict[str, PerfMetrics] = {}

    def collect_from_trace(self, tracer: WorkflowTracer, session_id: str) -> PerfMetrics:
        """Build PerfMetrics from a session trace."""
        trace = tracer.get_session_trace(session_id)
        pm = PerfMetrics(session_id=session_id)

        for event in trace:
            dur = event.get("duration_ms", 0) or 0
            agent = event.get("agent_type")
            if agent:
                pm.agent_durations[agent] = pm.agent_durations.get(agent, 0) + dur

            if event["event_type"] == TraceEventType.LLM_CALL_END.value:
                pm.llm_call_count += 1
            elif event["event_type"] == TraceEventType.CONFLICT_DETECTED.value:
                pm.conflict_count += 1
            elif event["event_type"] == TraceEventType.ARTIFACT_GENERATED.value:
                pm.artifact_count += 1

            if dur > pm.total_duration_ms:
                pm.total_duration_ms = dur  # wall clock

        self.metrics[session_id] = pm
        return pm

    def get_metrics(self, session_id: str) -> Optional[PerfMetrics]:
        return self.metrics.get(session_id)

    def report(self, session_id: str) -> str:
        """Generate a human-readable performance report."""
        pm = self.metrics.get(session_id)
        if not pm:
            return f"No metrics for session {session_id}"

        lines = [
            f"Session: {session_id}",
            f"Total duration: {pm.total_duration_ms:.0f}ms",
            f"Agent breakdown:",
        ]
        for agent, dur in sorted(pm.agent_durations.items()):
            lines.append(f"  {agent}: {dur:.0f}ms")
        lines.extend([
            f"LLM calls: {pm.llm_call_count}",
            f"Conflicts: {pm.conflict_count}",
            f"Artifacts: {pm.artifact_count}",
        ])
        return "\n".join(lines)


_metrics: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics
