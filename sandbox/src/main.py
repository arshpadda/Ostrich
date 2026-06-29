import asyncio
import json
import logging
import os
import sys
import uuid

import litellm
import redis.asyncio as redis
from langchain_core.messages import HumanMessage
from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.propagate import extract
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import start_http_server
from pythonjsonlogger import jsonlogger

from src.agent import build_graph
from src.protocol import event_to_frames, final_state_from_event

# Initialize OpenTelemetry Metrics (Prometheus Scraping)
metric_reader = PrometheusMetricReader()
meter_provider = MeterProvider(metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)

# Create a custom Meter and Counter for Sandbox metrics
meter = metrics.get_meter("sandbox-agent")
message_counter = meter.create_counter(
    "sandbox.messages.received",
    description="Total number of messages received from the user",
    unit="1",
)

# Enable LiteLLM OpenTelemetry Integration for token/cost metrics
litellm.success_callback = ["opentelemetry"]
litellm.failure_callback = ["opentelemetry"]

# Configure structured JSON logging
logger = logging.getLogger("sandbox-agent")

# Set up JSON stdout handler
stream_handler = logging.StreamHandler(sys.stdout)
formatter = jsonlogger.JsonFormatter(
    "%(asctime)s %(levelname)s %(name)s %(message)s", rename_fields={"levelname": "severity", "asctime": "timestamp"}
)
stream_handler.setFormatter(formatter)

# Set up OTel OTLP Exporter
logger_provider = LoggerProvider()
set_logger_provider(logger_provider)

try:
    otlp_exporter = OTLPLogExporter()
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_exporter))
    otel_handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
except Exception as e:
    sys.stderr.write(f"Failed to initialize OTLP Log Exporter: {e}\n")
    otel_handler = None

# Set up OTel OTLP Trace Exporter
try:
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)
except Exception as e:
    sys.stderr.write(f"Failed to initialize OTLP Trace Exporter: {e}\n")

# Remove existing handlers and attach new ones
for h in logger.handlers[:]:
    logger.removeHandler(h)

logger.addHandler(stream_handler)
if otel_handler:
    logger.addHandler(otel_handler)

logger.setLevel(logging.INFO)

# Get environment variables injected by Kubernetes Orchestrator
USER_ID = os.getenv("USER_ID")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CHANNEL_NAME = f"channel:sandbox:{USER_ID}"


def _friendly_error(exc: Exception) -> str:
    """Map provider errors to a user-facing message."""
    err = str(exc).lower()
    if any(s in err for s in ("429", "quota", "rate limit", "resource_exhausted")):
        return "I am currently experiencing high traffic and have been rate-limited by the AI provider. Please try again in a minute."
    if any(s in err for s in ("503", "unavailable", "high demand")):
        return "The AI model is currently experiencing high demand and is unavailable. Please try again later."
    return "I'm sorry, I've encountered an unexpected error."


async def process_turn(agent, redis_client: redis.Redis, state: dict, user_text: str) -> dict:
    """Stream one agent turn, publishing token/tool_call/message frames.

    Returns the updated conversation state for the next turn.
    """
    message_id = str(uuid.uuid4())
    state["messages"].append(HumanMessage(content=user_text))

    final_state = None
    async for event in agent.astream_events(state, version="v2"):
        for frame in event_to_frames(event, message_id):
            await redis_client.publish(CHANNEL_NAME, json.dumps(frame))
        candidate = final_state_from_event(event)
        if candidate is not None:
            final_state = candidate

    # Authoritative final content comes from the graph's final state, not the
    # accumulated deltas (which can include intermediate tool-calling turns).
    if final_state and final_state["messages"]:
        content = final_state["messages"][-1].content
        state = final_state
    else:
        content = ""

    await redis_client.publish(
        CHANNEL_NAME,
        json.dumps({"type": "message", "message_id": message_id, "role": "bot", "content": content, "done": True}),
    )
    logger.info("Completed turn %s", message_id)
    return state


async def main():
    # Start the Prometheus scraping HTTP server. The port is configurable
    # (METRICS_PORT=0 picks a free ephemeral port, useful for local dev where
    # multiple sandboxes or other services may contend for a fixed port).
    # A bind failure must not take down the agent — metrics are best-effort.
    metrics_port = int(os.getenv("METRICS_PORT", "8000"))
    try:
        start_http_server(metrics_port, addr="0.0.0.0")
        logger.info("Prometheus metrics server started on port %s", metrics_port)
    except OSError as e:
        logger.warning("Could not start Prometheus metrics server on port %s: %s", metrics_port, e)

    logger.info(f"Starting Agent Harness for User {USER_ID}")

    # Initialize LangGraph Agent
    agent = build_graph()

    # Setup Redis Connection
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True, health_check_interval=30)
    pubsub = r.pubsub(ignore_subscribe_messages=True)
    await pubsub.subscribe(CHANNEL_NAME)

    logger.info(f"Subscribed to {CHANNEL_NAME}. Listening for user messages...")

    # The LangGraph state holds the conversation history
    state = {"messages": []}

    while True:
        try:
            async for message in pubsub.listen():
                if not (message and message["type"] == "message"):
                    continue
                try:
                    data = json.loads(message["data"])
                except json.JSONDecodeError:
                    logger.warning("Skipping non-JSON message on channel")
                    continue

                # Only respond to inbound user prompts; ignore frames we publish.
                if data.get("role") != "user" and data.get("type") != "user_message":
                    continue

                user_text = data.get("content", "")
                message_counter.add(1, {"user_id": USER_ID})
                logger.info(f"Received from user: {user_text}")

                ctx = extract(data.get("trace_context", {}))
                tracer = trace.get_tracer("sandbox-agent")
                try:
                    with tracer.start_as_current_span("process_user_message", context=ctx):
                        logger.info("Streaming LangGraph turn...")
                        state = await process_turn(agent, r, state, user_text)
                except Exception as e:
                    logger.error("Error processing message", exc_info=True)
                    await r.publish(CHANNEL_NAME, json.dumps({"type": "error", "message": _friendly_error(e)}))
                    logger.info("Sent error notification back to Redis.")
        except redis.RedisError:
            logger.warning("Redis connection issue, retrying...", exc_info=True)
            await asyncio.sleep(1)
            continue
        except Exception:
            logger.error("PubSub loop error", exc_info=True)
            break


if __name__ == "__main__":
    asyncio.run(main())
