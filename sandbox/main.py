import os
import json
import redis
import logging
import litellm
from prometheus_client import start_http_server
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.messages import HumanMessage, AIMessage

# Initialize OpenTelemetry Metrics (Prometheus Scraping)
metric_reader = PrometheusMetricReader()
meter_provider = MeterProvider(metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)

# Create a custom Meter and Counter for Sandbox metrics
meter = metrics.get_meter("sandbox-agent")
message_counter = meter.create_counter(
    "sandbox.messages.received",
    description="Total number of messages received from the user",
    unit="1"
)

# Enable LiteLLM OpenTelemetry Integration for token/cost metrics
litellm.success_callback = ["opentelemetry"]
litellm.failure_callback = ["opentelemetry"]

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sandbox-agent")

# Get environment variables injected by Kubernetes Orchestrator
USER_ID = os.getenv("USER_ID")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CHANNEL_NAME = f"channel:sandbox:{USER_ID}"

# Define the State
class State(TypedDict):
    messages: Annotated[list, add_messages]

def build_graph():
    # Initialize the Gemini Model
    # It automatically uses the GEMINI_API_KEY environment variable
    llm = ChatLiteLLM(model="gemini/gemini-2.5-flash")

    def chatbot(state: State):
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    graph_builder = StateGraph(State)
    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_edge("chatbot", END)
    
    return graph_builder.compile()

def main():
    # Start the Prometheus scraping HTTP server on port 8000
    start_http_server(8000, addr="0.0.0.0")
    logger.info("Prometheus metrics server started on port 8000")
    
    logger.info(f"Starting Agent Harness for User {USER_ID}")
    
    # Initialize LangGraph Agent
    agent = build_graph()
    
    # Setup Redis Connection
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True, health_check_interval=30)
    pubsub = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(CHANNEL_NAME)
    
    logger.info(f"Subscribed to {CHANNEL_NAME}. Listening for user messages...")
    
    # The LangGraph state holds the conversation history
    state = {"messages": []}
    
    while True:
        try:
            for message in pubsub.listen():
                if message and message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        
                        # Only respond to messages from the user
                        if data.get("role") == "user":
                            user_text = data.get("content", "")
                            
                            # Increment our custom Prometheus metric
                            message_counter.add(1, {"user_id": USER_ID})
                            
                            logger.info(f"Received from user: {user_text}")
                            
                            # Update State with Human Message
                            state["messages"].append(HumanMessage(content=user_text))
                            
                            # Run LangGraph Agent
                            logger.info("Invoking LangGraph with Gemini...")
                            new_state = agent.invoke(state)
                            
                            # The latest message is the AI's response
                            ai_response = new_state["messages"][-1].content
                            
                            # Update our local state pointer to the new state
                            state = new_state
                            
                            # Publish the agent's response back to the channel
                            response_payload = {
                                "role": "bot",
                                "content": ai_response
                            }
                            r.publish(CHANNEL_NAME, json.dumps(response_payload))
                            logger.info("Sent response back to Redis.")
                            
                    except Exception as e:
                        logger.error("Error processing message", exc_info=True)
                        
                        error_msg = "I'm sorry, I've encountered an unexpected error."
                        err_str = str(e).lower()
                        if "429" in err_str or "quota" in err_str or "rate limit" in err_str or "resource_exhausted" in err_str:
                            error_msg = "I am currently experiencing high traffic and have been rate-limited by the AI provider. Please try again in a minute."
                        elif "503" in err_str or "unavailable" in err_str or "high demand" in err_str:
                            error_msg = "The AI model is currently experiencing high demand and is unavailable. Please try again later."
                            
                        # Publish the error response back to the channel
                        response_payload = {
                            "role": "bot",
                            "content": error_msg
                        }
                        r.publish(CHANNEL_NAME, json.dumps(response_payload))
                        logger.info("Sent error notification back to Redis.")
        except redis.exceptions.TimeoutError:
            # Reconnect or continue if a timeout happens
            continue
        except Exception as e:
            logger.error("PubSub loop error", exc_info=True)
            break

if __name__ == "__main__":
    main()
