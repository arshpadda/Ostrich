import os
from typing import Annotated

from langchain_community.chat_models import ChatLiteLLM
from langchain_core.messages import SystemMessage
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

from src.tools import execute_bash, get_weather, read_file, save_workspace, write_file


# Define the State
class State(TypedDict):
    messages: Annotated[list, add_messages]


def build_graph() -> CompiledStateGraph:
    # Initialize the Gemini Model via our internal Zero-Trust AI Gateway
    if os.getenv("GEMINI_API_KEY"):
        # Local standalone testing override
        llm = ChatLiteLLM(model="gemini/gemini-2.5-flash", api_key=os.getenv("GEMINI_API_KEY"))
    else:
        llm = ChatLiteLLM(
            model="openai/gemini-2.5-flash",
            api_base="http://litellm-proxy.ai-gateway.svc.cluster.local:4000",
            api_key="sk-internal-proxy-key",  # Dummy key for internal auth
        )

    # 1. Bind our tools to the LLM so it knows they exist
    tools = [get_weather, execute_bash, read_file, write_file, save_workspace]
    llm_with_tools = llm.bind_tools(tools)

    # Load system prompt from separate file
    prompt_path = os.path.join(os.path.dirname(__file__), "..", "system_prompt.txt")
    with open(prompt_path, "r") as f:
        prompt_content = f.read()
    system_prompt = SystemMessage(content=prompt_content)

    def chatbot(state: State) -> dict:
        # 2. Invoke the LLM with the tools bound
        response = llm_with_tools.invoke([system_prompt] + state["messages"])
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
