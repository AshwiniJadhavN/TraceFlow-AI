"""Observability tests."""

from __future__ import annotations

from observability.tracing import configure_telemetry, get_tracer


def test_configure_telemetry_is_idempotent(monkeypatch):
    monkeypatch.setenv("TRACEFLOW_OTEL_ENABLED", "false")
    assert configure_telemetry(service_name="traceflow-test") is False
    assert configure_telemetry(service_name="traceflow-test") is False


def test_tracer_fallback_supports_span_context():
    tracer = get_tracer("tests.observability")
    with tracer.start_as_current_span("unit-test") as span:
        span.set_attribute("traceflow.test", True)
