"""OpenTelemetry bootstrap with graceful no-op fallback."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import RESOURCE_ATTRIBUTES, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    OTEL_AVAILABLE = True
except ImportError:
    trace = None
    OTLPSpanExporter = None
    Resource = None
    RESOURCE_ATTRIBUTES = "service.name"
    TracerProvider = None
    BatchSpanProcessor = None
    ConsoleSpanExporter = None
    OTEL_AVAILABLE = False


class _NoOpSpan:
    def set_attribute(self, _key: str, _value: Any) -> None:
        return None

    def set_attributes(self, _attributes: dict[str, Any]) -> None:
        return None

    def record_exception(self, _exc: BaseException) -> None:
        return None


class _NoOpTracer:
    @contextmanager
    def start_as_current_span(self, _name: str) -> Iterator[_NoOpSpan]:
        yield _NoOpSpan()


_CONFIGURED = False
_NOOP_TRACER = _NoOpTracer()


def configure_telemetry(
    *,
    service_name: str = "traceflow-ai",
    service_version: str = "0.1.0",
) -> bool:
    """Configure OTEL tracing once, returning whether a real provider was installed."""
    global _CONFIGURED

    if _CONFIGURED:
        return OTEL_AVAILABLE

    if not OTEL_AVAILABLE or os.getenv("TRACEFLOW_OTEL_ENABLED", "true").lower() == "false":
        _CONFIGURED = True
        return False

    resource = Resource.create(
        {
            RESOURCE_ATTRIBUTES: service_name,
            "service.version": service_version,
            "deployment.environment": os.getenv("TRACEFLOW_ENV", "local"),
        }
    )
    provider = TracerProvider(resource=resource)

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if endpoint:
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    elif os.getenv("TRACEFLOW_OTEL_CONSOLE", "false").lower() == "true":
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    _CONFIGURED = True
    return True


def get_tracer(name: str) -> Any:
    if not OTEL_AVAILABLE or trace is None:
        return _NOOP_TRACER
    return trace.get_tracer(name)


def mark_span_error(span: Any, exc: BaseException) -> None:
    if hasattr(span, "record_exception"):
        span.record_exception(exc)
