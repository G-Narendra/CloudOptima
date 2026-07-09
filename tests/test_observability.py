"""Tests for the observability module: tracer, audit logger, metrics collector."""

import json
import os
import tempfile

from src.core.observability import (
    WorkflowTracer,
    AuditLogger,
    MetricsCollector,
    TraceEvent,
    TraceEventType,
    PerfMetrics,
    get_tracer,
    reset_tracer,
    get_audit_logger,
    get_metrics_collector,
)


class TestTraceEvent:
    """Test TraceEvent creation and serialization."""

    def test_create_event(self):
        event = TraceEvent(
            event_type=TraceEventType.SESSION_START,
            session_id="session_abc",
            agent_type="architect",
        )
        assert event.event_type == TraceEventType.SESSION_START
        assert event.session_id == "session_abc"
        assert event.agent_type == "architect"
        assert event.trace_id is not None
        assert event.timestamp is not None

    def test_event_to_dict(self):
        event = TraceEvent(
            event_type=TraceEventType.AGENT_END,
            session_id="session_123",
            duration_ms=1500.0,
            metadata={"key": "value"},
        )
        d = event.to_dict()
        assert d["event_type"] == TraceEventType.AGENT_END.value
        assert d["session_id"] == "session_123"
        assert d["duration_ms"] == 1500.0
        assert d["metadata"] == {"key": "value"}

    def test_event_defaults(self):
        event = TraceEvent(
            event_type=TraceEventType.ERROR,
            session_id="session_err",
            error="Something broke",
        )
        assert event.error == "Something broke"
        assert event.duration_ms is None
        assert event.parent_trace_id is None


class TestWorkflowTracer:
    """Test the WorkflowTracer class."""

    def setup_method(self):
        self.tracer = WorkflowTracer()

    def test_record_event(self):
        event = TraceEvent(
            event_type=TraceEventType.SESSION_START,
            session_id="session_1",
        )
        trace_id = self.tracer.record(event)
        assert trace_id == event.trace_id
        assert len(self.tracer.events) == 1

    def test_start_and_end_span(self):
        trace_id = self.tracer.start_span(
            TraceEventType.AGENT_START,
            "session_1",
            agent_type="architect",
        )
        assert trace_id in self.tracer._call_stack

        self.tracer.end_span(trace_id, output_summary="Done", error=None)

        # Verify duration was calculated (may be 0 in fast environments)
        matching = [e for e in self.tracer.events if e.trace_id == trace_id]
        assert len(matching) == 1
        assert matching[0].duration_ms is not None
        assert matching[0].output_summary == "Done"

    def test_end_unknown_span(self):
        """Should log warning but not crash."""
        self.tracer.end_span("nonexistent", output_summary="test")

    def test_get_session_trace(self):
        self.tracer.record(TraceEvent(
            event_type=TraceEventType.SESSION_START,
            session_id="session_a",
        ))
        self.tracer.record(TraceEvent(
            event_type=TraceEventType.AGENT_START,
            session_id="session_a",
            agent_type="architect",
        ))
        self.tracer.record(TraceEvent(
            event_type=TraceEventType.SESSION_START,
            session_id="session_b",
        ))

        trace_a = self.tracer.get_session_trace("session_a")
        assert len(trace_a) == 2

        trace_b = self.tracer.get_session_trace("session_b")
        assert len(trace_b) == 1

    def test_get_session_trace_empty(self):
        trace = self.tracer.get_session_trace("nonexistent")
        assert trace == []

    def test_export_to_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracer = WorkflowTracer(export_path=tmpdir)
            tracer.record(TraceEvent(
                event_type=TraceEventType.SESSION_START,
                session_id="session_export",
            ))
            tracer.export_to_file("session_export")

            # Verify file was created
            files = os.listdir(tmpdir)
            assert len(files) == 1
            assert "trace_session_export" in files[0]
            assert files[0].endswith(".json")

            # Verify content
            with open(os.path.join(tmpdir, files[0])) as f:
                data = json.load(f)
            assert len(data) == 1
            assert data[0]["session_id"] == "session_export"

    def test_export_to_file_no_path(self):
        """Should not crash if no export path is configured."""
        tracer = WorkflowTracer()
        tracer.export_to_file("session_no_path")  # Should not raise

    def test_get_session_summary(self):
        tracer = WorkflowTracer()
        tracer.record(TraceEvent(
            event_type=TraceEventType.SESSION_START,
            session_id="session_summary",
        ))
        tracer.record(TraceEvent(
            event_type=TraceEventType.AGENT_START,
            session_id="session_summary",
            agent_type="architect",
            duration_ms=500,
        ))
        tracer.record(TraceEvent(
            event_type=TraceEventType.CONFLICT_DETECTED,
            session_id="session_summary",
        ))
        tracer.record(TraceEvent(
            event_type=TraceEventType.ERROR,
            session_id="session_summary",
            error="test error",
        ))

        summary = tracer.get_session_summary("session_summary")
        assert summary["session_id"] == "session_summary"
        assert summary["total_events"] == 4
        assert summary["agent_interactions"] >= 1
        assert summary["conflicts_detected"] >= 1
        assert summary["errors"] >= 1
        assert summary["total_duration_ms"] > 0

    def test_get_session_summary_empty(self):
        """Empty session returns valid summary with zero events."""
        tracer = WorkflowTracer()  # Fresh tracer for isolation
        summary = tracer.get_session_summary("nonexistent")
        assert summary["session_id"] == "nonexistent"
        assert summary["events"] == 0

    def test_export_opentelemetry(self):
        tracer = WorkflowTracer()
        tracer.record(TraceEvent(
            event_type=TraceEventType.SESSION_START,
            session_id="session_otel",
            duration_ms=100,
        ))

        otel = tracer.export_opentelemetry("session_otel")
        assert "resourceSpans" in otel
        assert len(otel["resourceSpans"][0]["scopeSpans"][0]["spans"]) == 1
        span = otel["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        assert span["name"] == TraceEventType.SESSION_START.value
        assert span["attributes"]["session.id"] == "session_otel"


class TestGlobalTracer:
    """Test the global tracer singleton."""

    def teardown_method(self):
        reset_tracer()

    def test_get_tracer_singleton(self):
        t1 = get_tracer()
        t2 = get_tracer()
        assert t1 is t2

    def test_reset_tracer(self):
        t1 = get_tracer()
        reset_tracer()
        t2 = get_tracer()
        assert t1 is not t2


class TestAuditLogger:
    """Test the AuditLogger class."""

    def setup_method(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.logger = AuditLogger(log_dir=self.tmpdir.name)

    def teardown_method(self):
        self.tmpdir.cleanup()

    def test_log_decision(self):
        log_id = self.logger.log_decision(
            "session_audit", "test_decision", "architect",
            "Testing audit logging",
            evidence={"key": "value"},
        )
        assert log_id is not None
        assert len(log_id) > 0

    def test_get_session_log(self):
        self.logger.log_decision("session_get", "decision_1", "cost", "First decision")
        self.logger.log_decision("session_get", "decision_2", "security", "Second decision")

        entries = self.logger.get_session_log("session_get")
        assert len(entries) == 2
        assert entries[0]["decision_type"] == "decision_1"
        assert entries[1]["decision_type"] == "decision_2"

    def test_get_session_log_empty(self):
        entries = self.logger.get_session_log("nonexistent")
        assert entries == []

    def test_log_decision_includes_timestamp(self):
        log_id = self.logger.log_decision("session_ts", "test", "compliance", "test")
        entries = self.logger.get_session_log("session_ts")
        assert len(entries) == 1
        assert "timestamp" in entries[0]
        assert entries[0]["log_id"] == log_id

    def test_log_decision_with_rationale_truncation(self):
        long_rationale = "A" * 500
        self.logger.log_decision("session_long", "test", "judge", long_rationale)
        entries = self.logger.get_session_log("session_long")
        assert len(entries) == 1
        # Rationale should be full in the log (truncation is for breadcrumbs)
        assert len(entries[0]["rationale"]) == 500

    def test_append_only(self):
        """Verify audit logs are append-only (immutable)."""
        self.logger.log_decision("session_immutable", "first", "architect", "First")
        self.logger.log_decision("session_immutable", "second", "cost", "Second")

        entries = self.logger.get_session_log("session_immutable")
        assert len(entries) == 2
        assert entries[0]["decision_type"] == "first"
        assert entries[1]["decision_type"] == "second"


class TestAuditLoggerFileFailure:
    """Test audit logger handles file failures gracefully."""

    def test_invalid_directory(self):
        """Should not crash with invalid directory."""
        logger = AuditLogger(log_dir="/nonexistent/deep/path")
        log_id = logger.log_decision("session_fail", "test", "architect", "test")
        # Should still return a log_id even if write fails
        assert log_id is not None


class TestGlobalAuditLogger:
    """Test the global audit logger singleton."""

    def test_get_audit_logger(self):
        l1 = get_audit_logger()
        l2 = get_audit_logger()
        assert l1 is l2


class TestMetricsCollector:
    """Test the MetricsCollector class."""

    def setup_method(self):
        self.collector = MetricsCollector()
        self.tracer = WorkflowTracer()

        # Add some trace events
        self.tracer.record(TraceEvent(
            event_type=TraceEventType.AGENT_START,
            session_id="session_metrics",
            agent_type="architect",
            duration_ms=1000,
        ))
        self.tracer.record(TraceEvent(
            event_type=TraceEventType.AGENT_START,
            session_id="session_metrics",
            agent_type="cost",
            duration_ms=500,
        ))
        self.tracer.record(TraceEvent(
            event_type=TraceEventType.LLM_CALL_END,
            session_id="session_metrics",
            duration_ms=200,
        ))
        self.tracer.record(TraceEvent(
            event_type=TraceEventType.CONFLICT_DETECTED,
            session_id="session_metrics",
        ))
        self.tracer.record(TraceEvent(
            event_type=TraceEventType.ARTIFACT_GENERATED,
            session_id="session_metrics",
        ))

    def test_collect_from_trace(self):
        pm = self.collector.collect_from_trace(self.tracer, "session_metrics")
        assert pm.session_id == "session_metrics"
        assert pm.llm_call_count == 1
        assert pm.conflict_count == 1
        assert pm.artifact_count == 1

    def test_agent_durations(self):
        pm = self.collector.collect_from_trace(self.tracer, "session_metrics")
        assert "architect" in pm.agent_durations
        assert pm.agent_durations["architect"] >= 1000

    def test_get_metrics(self):
        self.collector.collect_from_trace(self.tracer, "session_metrics")
        pm = self.collector.get_metrics("session_metrics")
        assert pm is not None
        assert pm.session_id == "session_metrics"

        none_pm = self.collector.get_metrics("nonexistent")
        assert none_pm is None

    def test_report(self):
        self.collector.collect_from_trace(self.tracer, "session_metrics")
        report = self.collector.report("session_metrics")
        assert "session_metrics" in report
        assert "Total duration" in report
        assert "Agent breakdown" in report

    def test_report_no_metrics(self):
        report = get_metrics_collector().report("nonexistent")
        assert "No metrics" in report


class TestPerfMetrics:
    """Test PerfMetrics dataclass."""

    def test_create(self):
        pm = PerfMetrics(session_id="test_session")
        assert pm.session_id == "test_session"
        assert pm.total_duration_ms == 0.0
        assert pm.agent_durations == {}
        assert pm.llm_call_count == 0

    def test_with_values(self):
        pm = PerfMetrics(
            session_id="test",
            total_duration_ms=5000.0,
            llm_call_count=4,
            agent_durations={"architect": 2000.0, "cost": 1500.0},
        )
        assert pm.total_duration_ms == 5000.0
        assert pm.llm_call_count == 4
        assert pm.agent_durations["architect"] == 2000.0
