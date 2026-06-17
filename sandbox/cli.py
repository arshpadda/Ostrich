import os
import sys

# Ensure api keys can be loaded for local testing bypassing the AI gateway
if not os.getenv("GEMINI_API_KEY"):
    print("Error: Please set GEMINI_API_KEY environment variable for local testing.")
    sys.exit(1)

from langchain_core.messages import HumanMessage

from src.agent import build_graph


def run_cli():
    print("Initializing Autonomous Coding Agent...")
    agent = build_graph()

    state = {"messages": []}

    print("Agent ready! Type 'exit' to quit.")
    while True:
        try:
            user_input = input("\n> ")
            if user_input.lower() in ["exit", "quit"]:
                break
            if not user_input.strip():
                continue

            state["messages"].append(HumanMessage(content=user_input))

            print("\nAgent is thinking and executing tools (check docker logs for tool outputs)...")
            new_state = agent.invoke(state)

            # The last message is the final response
            response = new_state["messages"][-1]
            print(f"\n[Agent]: {response.content}")

            state = new_state

        except (KeyboardInterrupt, EOFError):
            break
        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    run_cli()
