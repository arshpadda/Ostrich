# Sandbox Operations & Agent Internals

The Sandbox is the beating heart of the Ostrich engine. It is a highly ephemeral, isolated Kubernetes Pod (`sandbox-{user_id}`) running a sophisticated ReAct (Reason + Act) agent powered by LangGraph.

## Internal Architecture

![Diagram](./05_sandbox_operations_0.png)

## LangGraph & LiteLLM Integration

The intelligence of the agent is modeled as a Directed Cyclic Graph using **LangGraph**.
1. **The Graph**: The graph has two primary nodes: `chatbot` (the LLM) and `tools` (the execution environment). 
2. **Conditional Routing**: When a user message arrives, the graph invokes the `chatbot` node. If the LLM determines it needs to read a file or run a bash command, it generates a `tool_call`. LangGraph intercepts this, routes the execution to the `tools` node, runs the python function securely within the pod, appends the tool output to the conversational `State`, and routes *back* to the `chatbot` node. This cycle repeats until the agent generates a final text response, at which point the graph exits and the response is pushed to Redis.
3. **LiteLLM**: To remain model-agnostic, LangGraph binds to `ChatLiteLLM`. Rather than directly authenticating with Google Generative AI, `ChatLiteLLM` is configured with `api_base="http://litellm-proxy.ai-gateway..."`. This ensures the sandbox never possesses a real API key.

## Ephemerality & The TTL Lifecycle

Sandboxes are fundamentally untrusted and resource-heavy. They cannot run forever.
- **TTL Constraint**: Every sandbox pod is created with an `active_deadline_seconds=1800` parameter. Exactly 30 minutes after instantiation, Kubernetes forcefully kills the pod and wipes its local memory.
- **Lazy Re-creation**: If a user comes back an hour later and sends a message, the WebSocket Control Plane queries the Kubernetes API. Finding the pod dead, it simply creates a new one. The new pod boots up, subscribes to the user's Redis channel, and resumes listening.

## State Management & Backups

Because the pod is deleted every 30 minutes, the `/workspace` directory (where the agent writes code) is ephemeral.
- **The `save_workspace` Tool**: To preserve work, the agent is equipped with a `save_workspace` tool. Before the user leaves, or periodically, the agent can call this tool. The tool uses Python's `shutil.make_archive` to zip the entire `/workspace` directory and uses the Google Cloud Storage SDK to upload it to `ostrich-agent-workspaces/sandbox_{user_id}.zip`.
- **Workload Identity Security**: The pod does not have a hardcoded JSON key to upload to GCS. It uses Google Kubernetes Engine's **Workload Identity**. The pod's Kubernetes Service Account (`sandbox-agent-sa`) intercepts metadata API calls and exchanges them for short-lived OAuth tokens, allowing password-less authentication to the Storage bucket.

## Stateful Code Execution (Jupyter Kernel)

The agent has two execution tools with a deliberate division of labor:
- **`execute_bash`**: Stateless shell for system-level operations only - installing packages (`pip`/`apt`/`npm`), `git`, `curl`, and running compiled binaries. Each call is a fresh subprocess; nothing persists.
- **`execute_python`**: A persistent **Jupyter kernel** (`ipykernel`) launched once at pod boot and shut down on exit. Variables, imports, and computed results persist across calls for the lifetime of the pod, so the agent builds up work incrementally like a notebook instead of re-deriving state on every step.

**Mechanics**: `KernelSession` (`sandbox/src/kernel.py`) owns the kernel subprocess and speaks the Jupyter messaging protocol over ZMQ via `jupyter_client.AsyncKernelManager`. Each `execute_python` call sends code on the shell channel and drains the io_pub channel until the kernel reports `idle`, collecting `stream` (stdout), `execute_result` (last-expression value), `display_data` (rich outputs, noted by MIME type), and `error` (structured traceback) messages. An `asyncio.Lock` serializes calls since the kernel is single-threaded.

**Resilience**:
- **Timeouts**: A runaway cell is `SIGINT`-interrupted after 60s rather than killed, so the namespace survives. The interrupted cell's trailing io_pub traffic is drained so the next call starts against a clean channel.
- **Auto-restart**: If the kernel dies (e.g. OOM kill), `_ensure_alive` transparently restarts it and sets `namespace_reset: true` in the response so the model knows prior state is gone and can re-run its setup.
- **Bounded output**: stdout is truncated to 16 KB before being returned to the model to protect context size and the Redis channel.

The kernel is process-isolated from the agent harness (defense-in-depth alongside gVisor and the non-root runtime user): LLM-generated code that segfaults or calls `sys.exit()` takes down only the kernel, not the worker.
