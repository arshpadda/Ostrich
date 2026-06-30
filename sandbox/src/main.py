import asyncio
import contextlib
import json
import logging
import os
import socket
import sys
import time
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

# Create a custom Meter and instruments for Sandbox metrics
meter = metrics.get_meter("sandbox-agent")
message_counter = meter.create_counter(
    "sandbox.messages.received",
    description="Total number of messages received from the user",
    unit="1",
)
tool_call_counter = meter.create_counter(
    "sandbox.tool_calls", description="Total tool invocations by the agent", unit="1"
)
turn_error_counter = meter.create_counter(
    "sandbox.turn.errors", description="Total turns that ended in an error", unit="1"
)
turn_latency = meter.create_histogram(
    "sandbox.turn.latency", description="Wall-clock seconds to complete an agent turn", unit="s"
)

# Keep at most this many trailing messages in context (trimmed at a turn boundary
# to avoid orphaning tool-call/tool-result pairs) to bound cost and context size.
MAX_HISTORY_MESSAGES = 40

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

# Set up OTel OTLP exporters only when a collector endpoint is configured, so
# local runs without a collector don't spam connection errors every interval.
logger_provider = LoggerProvider()
set_logger_provider(logger_provider)
otel_handler = None

if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
    try:
        otlp_exporter = OTLPLogExporter()
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_exporter))
        otel_handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
    except Exception as e:
        sys.stderr.write(f"Failed to initialize OTLP Log Exporter: {e}\n")

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

# Identity is the sandbox's stable hostname (== Sandbox/pod name under
# agent-sandbox). Warm-pool pods are generic until claimed, so each worker keys
# its Redis channel off its own identity; the control plane maps user -> sandbox
# and bridges the WebSocket to this channel.
SANDBOX_ID = os.getenv("SANDBOX_ID") or socket.gethostname()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CHANNEL_NAME = f"channel:sandbox:{SANDBOX_ID}"


def _friendly_error(exc: Exception) -> str:
    """Map provider errors to a user-facing message."""
    err = str(exc).lower()
    if any(s in err for s in ("429", "quota", "rate limit", "resource_exhausted")):
        return "I am currently experiencing high traffic and have been rate-limited by the AI provider. Please try again in a minute."
    if any(s in err for s in ("503", "unavailable", "high demand")):
        return "The AI model is currently experiencing high demand and is unavailable. Please try again later."
    return "I'm sorry, I've encountered an unexpected error."


def _trim_history(messages: list) -> list:
    """Cap history at MAX_HISTORY_MESSAGES, slicing at a HumanMessage boundary so
    we never start mid-sequence (which would orphan tool-call/tool-result pairs)."""
    if len(messages) <= MAX_HISTORY_MESSAGES:
        return messages
    tail = messages[-MAX_HISTORY_MESSAGES:]
    for i, msg in enumerate(tail):
        if isinstance(msg, HumanMessage):
            return tail[i:]
    return tail  # no human boundary found; return the window as-is


async def process_turn(agent, redis_client: redis.Redis, state: dict, user_text: str, message_id: str) -> dict:
    """Stream one agent turn, publishing token/tool_call/message frames.

    Returns the updated conversation state for the next turn. Raises on error or
    cancellation; in both cases the unanswered prompt is rolled back so the next
    turn sees consistent history.
    """
    state["messages"] = _trim_history(state["messages"])
    state["messages"].append(HumanMessage(content=user_text))

    started = time.monotonic()
    final_state = None
    try:
        async for event in agent.astream_events(state, version="v2"):
            for frame in event_to_frames(event, message_id):
                if frame["type"] == "tool_call" and frame.get("status") == "running":
                    tool_call_counter.add(1, {"tool": frame.get("tool", "unknown")})
                await redis_client.publish(CHANNEL_NAME, json.dumps(frame))
            candidate = final_state_from_event(event)
            if candidate is not None:
                final_state = candidate
    except (Exception, asyncio.CancelledError):
        # Drop the unanswered human message so the next turn doesn't see a
        # dangling prompt. Covers both errors (caller emits an error frame) and
        # cancellation (caller emits a cancelled frame). CancelledError is a
        # BaseException, so it must be named explicitly here.
        if state["messages"] and isinstance(state["messages"][-1], HumanMessage):
            state["messages"].pop()
        raise

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
    turn_latency.record(time.monotonic() - started, {"sandbox_id": SANDBOX_ID})
    logger.info("Completed turn %s in %.2fs", message_id, time.monotonic() - started)
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

    logger.info("Starting Agent Harness for sandbox %s", SANDBOX_ID)

    # Initialize LangGraph Agent
    agent = build_graph()

    # Setup Redis Connection
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True, health_check_interval=30)
    pubsub = r.pubsub(ignore_subscribe_messages=True)
    await pubsub.subscribe(CHANNEL_NAME)

    logger.info(f"Subscribed to {CHANNEL_NAME}. Listening for user messages...")

    # The LangGraph state holds the conversation history. A single turn runs at a
    # time as a cancellable background task so the reader stays responsive and a
    # new prompt (or an explicit cancel) can interrupt the in-flight turn.
    state = {"messages": []}
    current_task: asyncio.Task | None = None
    current_message_id: str | None = None

    async def _run_turn(data: dict, message_id: str) -> None:
        nonlocal state
        user_text = data.get("content", "")
        message_counter.add(1, {"sandbox_id": SANDBOX_ID})
        logger.info("Received from user: %s", user_text)
        ctx = extract(data.get("trace_context", {}))
        tracer = trace.get_tracer("sandbox-agent")
        try:
            with tracer.start_as_current_span("process_user_message", context=ctx):
                logger.info("Streaming LangGraph turn %s...", message_id)
                state = await process_turn(agent, r, state, user_text, message_id)
        except asyncio.CancelledError:
            logger.info("Turn %s cancelled", message_id)
            raise
        except Exception as e:
            logger.error("Error processing message", exc_info=True)
            turn_error_counter.add(1, {"sandbox_id": SANDBOX_ID})
            await r.publish(CHANNEL_NAME, json.dumps({"type": "error", "message": _friendly_error(e)}))

    async def _cancel_current() -> None:
        nonlocal current_task, current_message_id
        if current_task and not current_task.done():
            current_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await current_task
            if current_message_id:
                # Notify the client the in-flight turn was interrupted. Note: a
                # blocking tool (e.g. subprocess.run) only yields at the next await
                # boundary, so cancelling mid-tool waits for it to return (v1).
                await r.publish(
                    CHANNEL_NAME,
                    json.dumps({"type": "system", "event": "cancelled", "message_id": current_message_id}),
                )
        current_task = None
        current_message_id = None

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

                # Explicit stop from the client.
                if data.get("type") == "cancel":
                    await _cancel_current()
                    continue

                # Ignore frames we publish ourselves; only act on user prompts.
                if data.get("role") != "user" and data.get("type") != "user_message":
                    continue

                # A new prompt supersedes any in-flight turn.
                await _cancel_current()
                current_message_id = str(uuid.uuid4())
                current_task = asyncio.create_task(_run_turn(data, current_message_id))
        except redis.RedisError:
            logger.warning("Redis connection issue, retrying...", exc_info=True)
            await asyncio.sleep(1)
            continue
        except Exception:
            logger.error("PubSub loop error", exc_info=True)
            break


if __name__ == "__main__":
    asyncio.run(main())
