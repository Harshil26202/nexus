"""OpenTelemetry + Azure Application Insights setup."""
import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

from app.core.config import settings

log = structlog.get_logger()

_tracer_provider: TracerProvider | None = None


def setup_telemetry() -> None:
    global _tracer_provider

    resource = Resource.create({SERVICE_NAME: settings.OTEL_SERVICE_NAME})

    sampler = TraceIdRatioBased(0.1) if settings.is_production else TraceIdRatioBased(1.0)

    provider = TracerProvider(resource=resource, sampler=sampler)

    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        otlp_exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    if settings.AZURE_APPINSIGHTS_CONNECTION_STRING:
        try:
            from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
            az_exporter = AzureMonitorTraceExporter(
                connection_string=settings.AZURE_APPINSIGHTS_CONNECTION_STRING
            )
            provider.add_span_processor(BatchSpanProcessor(az_exporter))
            log.info("telemetry.azure_appinsights_enabled")
        except Exception as e:
            log.warning("telemetry.azure_appinsights_failed", error=str(e))

    trace.set_tracer_provider(provider)
    FastAPIInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()

    _tracer_provider = provider
    log.info("telemetry.initialized", service=settings.OTEL_SERVICE_NAME)


def get_tracer(name: str = "nexus") -> trace.Tracer:
    return trace.get_tracer(name)
