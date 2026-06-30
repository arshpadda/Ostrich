import contextvars
import logging
import os
import sys
from uuid import uuid4

from fastapi import Request
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pythonjsonlogger import jsonlogger

# Context variables to hold request-scoped metadata
request_id_context = contextvars.ContextVar("request_id", default="")
user_id_context = contextvars.ContextVar("user_id", default="")


class RequestContextFilter(logging.Filter):
    """
    A logging filter that injects the current request_id and user_id
    from contextvars into every log record.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        req_id = request_id_context.get()
        if req_id:
            record.request_id = req_id

        uid = user_id_context.get()
        if uid:
            record.user_id = uid

        return True


def setup_logging():
    """
    Replaces the root logger configuration with JSON structured logging.
    """
    logger = logging.getLogger()

    # Remove all existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)

    # Use python-json-logger to format the LogRecord as JSON
    # We rename 'levelname' to 'severity' for GCP Cloud Logging compatibility
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s %(user_id)s",
        rename_fields={"levelname": "severity", "asctime": "timestamp"},
    )

    handler.setFormatter(formatter)

    # Add the custom context filter
    handler.addFilter(RequestContextFilter())

    logger.addHandler(handler)

    # Define OTel Resource (Service Name)
    resource = Resource.create({"service.name": "ostrich-controlplane"})

    # Configure OpenTelemetry LoggerProvider and OTLP Exporter
    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)

    # Configure OpenTelemetry TracerProvider
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    # Wire OTLP exporters only when a collector endpoint is configured, so local
    # runs without a collector don't spam connection errors every batch interval.
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        try:
            otlp_log_exporter = OTLPLogExporter(endpoint=otlp_endpoint, insecure=True)
            logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_log_exporter))
            otel_handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)

            # OTel logs also need the context variables
            otel_handler.addFilter(RequestContextFilter())
            logger.addHandler(otel_handler)

            # Trace Exporter
            otlp_trace_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            tracer_provider.add_span_processor(BatchSpanProcessor(otlp_trace_exporter))
        except Exception as e:
            # Gracefully handle missing OTLP endpoint configuration
            logger.warning(f"Failed to initialize OTLP Exporters: {e}")
    else:
        logger.info("OTEL_EXPORTER_OTLP_ENDPOINT not set; skipping OTLP exporters.")

    logger.setLevel(logging.INFO)

    return logger


async def logging_middleware(request: Request, call_next):
    """
    FastAPI Middleware to set request_id and extract user_id (if available)
    for structured logging.
    """
    # Generate a unique request ID
    req_id = str(uuid4())
    request_id_token = request_id_context.set(req_id)

    # Attempt to extract user_id if authentication middleware populated it
    # We'll set it to empty initially
    user_id_token = user_id_context.set("")

    try:
        # In FastAPI, auth middlewares might set request.state.user
        # Since this runs before endpoints, we must wait for call_next,
        # but wait, contextvars are tricky.
        # Actually, if we set the contextvar, the endpoints can mutate it!
        response = await call_next(request)
        return response
    finally:
        # Reset context vars to prevent memory leaks
        request_id_context.reset(request_id_token)
        user_id_context.reset(user_id_token)
