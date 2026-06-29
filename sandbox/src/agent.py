import os
from typing import Annotated

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

from src.tools import execute_bash, get_weather, read_file, save_workspace, write_file

# Gemini's OpenAI-compatible endpoint, used for local standalone runs. In the
# cluster, requests instead flow through the LiteLLM proxy (also OpenAI-compatible),
# which keeps provider API keys out of the sandbox (zero-trust gateway).
GEMINI_OPENAI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"


# Define the State
class State(TypedDict):
    messages: Annotated[list, add_messages]


def _normalize_model(name: str) -> str:
    """Strip any LiteLLM-style provider prefix (e.g. 'gemini/', 'openai/').

    ChatOpenAI / the proxy expect the bare model id (e.g. 'gemini-2.5-flash').
    """
    return name.split("/", 1)[-1] if "/" in name else name


def _build_llm(model: str) -> ChatOpenAI:
    """Construct a streaming ChatOpenAI client for either local or cluster use.

    We use ChatOpenAI (not ChatLiteLLM) because ChatLiteLLM does not emit
    incremental content through ``astream_events`` — its stream chunks come back
    empty, which makes token-by-token streaming impossible. ChatOpenAI streams
    correctly against any OpenAI-compatible endpoint, including both Gemini's
    native compatibility layer and the in-cluster LiteLLM proxy.
    """
    if os.getenv("GEMINI_API_KEY") and not os.getenv("LITELLM_PROXY_URL"):
        # Local standalone: talk directly to Gemini's OpenAI-compatible endpoint.
        return ChatOpenAI(
            model=model,
            api_key=os.environ["GEMINI_API_KEY"],
            base_url=GEMINI_OPENAI_BASE,
            temperature=0,
            streaming=True,
        )
    # Cluster: route through the LiteLLM proxy gateway.
    return ChatOpenAI(
        model=model,
        api_key=os.getenv("LITELLM_API_KEY", "sk-internal-proxy-key"),
        base_url=os.getenv("LITELLM_PROXY_URL", "http://litellm-proxy.ai-gateway.svc.cluster.local:4000"),
        temperature=0,
        streaming=True,
    )


def build_graph() -> CompiledStateGraph:
    primary_model = _normalize_model(os.getenv("LLM_MODEL", "gemini-2.5-flash"))
    fallback_model = _normalize_model(os.getenv("FALLBACK_LLM_MODEL", "")) if os.getenv("FALLBACK_LLM_MODEL") else ""

    primary_llm = _build_llm(primary_model)
    fallback_llm = _build_llm(fallback_model) if fallback_model else None

    # 1. Bind our tools to the LLM so it knows they exist
    tools = [get_weather, execute_bash, read_file, write_file, save_workspace]

    primary_with_tools = primary_llm.bind_tools(tools)
    if fallback_llm:
        fallback_with_tools = fallback_llm.bind_tools(tools)
        llm_with_tools = primary_with_tools.with_fallbacks([fallback_with_tools])
    else:
        llm_with_tools = primary_with_tools

    # Load system prompt from separate file
    prompt_path = os.path.join(os.path.dirname(__file__), "..", "system_prompt.txt")
    with open(prompt_path, "r") as f:
        prompt_content = f.read()
    system_prompt = SystemMessage(content=prompt_content)

    async def chatbot(state: State) -> dict:
        # 2. Invoke the LLM with the tools bound. Async so token deltas surface
        # through astream_events for real-time streaming.
        response = await llm_with_tools.ainvoke([system_prompt] + state["messages"])
        return {"messages": [response]}

    graph_builder = StateGraph(State)
    graph_builder.add_node("chatbot", chatbot)

    # 3. Create a ToolNode to automatically execute any tool calls made by the LLM
    tool_node = ToolNode(tools=tools)
    graph_builder.add_node("tools", tool_node)

    # 4. Define the routing logic (ReAct Architecture)
    graph_builder.add_edge(START, "chatbot")
    # If the LLM returns a tool_call, route to "tools". Otherwise, route to END.
    graph_builder.add_conditional_edges("chatbot", tools_condition)
    # Once the tool finishes, route back to the chatbot so it can read the tool's output and answer the user
    graph_builder.add_edge("tools", "chatbot")

    return graph_builder.compile()
