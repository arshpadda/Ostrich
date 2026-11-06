"""Stateful Python execution backed by a Jupyter (ipykernel) subprocess.

The agent's ``execute_bash`` tool is stateless: every call is a fresh shell, so
Python variables and imports never survive between tool calls. ``KernelSession``
wraps a long-lived ipykernel process and speaks the Jupyter messaging protocol
over ZMQ, giving the agent a REPL whose namespace persists across
``execute_python`` calls for the lifetime of the sandbox pod.

Design notes:
- One kernel per sandbox pod. It is started at boot and shut down on exit. State
  persists across user conversations within a pod, matching the existing
  conversation-history semantics; a recycled pod gets a fresh kernel.
- A single ``asyncio.Lock`` serializes ``execute`` calls. The kernel is
  single-threaded, and interleaving io_pub messages from concurrent executes
  would be unattributable, so we never run two executes at once.
- ``_ensure_alive`` restarts a dead kernel (OOM kill, hard crash) transparently
  and signals the caller that the namespace was reset, so the model can recover.
"""

import asyncio
import logging

from jupyter_client import AsyncKernelManager

logger = logging.getLogger("sandbox-agent")

# Wall-clock ceiling for a single execute_python call. A runaway cell is
# interrupted (SIGINT) rather than killed, so the namespace survives.
DEFAULT_EXECUTE_TIMEOUT = 60.0

# Bound the text we return to the model so a chatty cell can't blow up context
# or flood the Redis channel. The full output still ran in the kernel.
MAX_STREAM_CHARS = 16_384

# How long to wait for the kernel to come up / go down before giving up.
KERNEL_START_TIMEOUT = 30.0
KERNEL_SHUTDOWN_TIMEOUT = 10.0


class ExecutionResult:
    """Structured result of a single kernel execution.

    ``status`` is "success" unless the code raised an uncaught exception, in
    which case ``error`` carries the exception name, value, and traceback.
    ``namespace_reset`` is True when the kernel had to be restarted before this
    call (e.g. it had died), signalling to the caller that prior state is gone.
    """

    def __init__(self) -> None:
        self.status: str = "success"
        self.stdout: str = ""
        self.result: str | None = None
        self.displays: list[str] = []
        self.error: dict[str, str] | None = None
        self.execution_count: int | None = None
        self.namespace_reset: bool = False

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "stdout": _truncate(self.stdout),
            "result": self.result,
            "displays": self.displays,
            "error": self.error,
            "execution_count": self.execution_count,
            "namespace_reset": self.namespace_reset,
        }


def _truncate(text: str) -> str:
    if len(text) > MAX_STREAM_CHARS:
        return text[:MAX_STREAM_CHARS] + "\n...[output truncated]"
    return text


def _clean_traceback(traceback: list[str]) -> str:
    """Join and strip ANSI color codes from a kernel traceback for readability."""
    import re

    ansi = re.compile(r"\x1b\[[0-9;]*m")
    return "\n".join(ansi.sub("", line) for line in traceback)


class KernelSession:
    """Owns a single ipykernel subprocess and serializes execution against it."""

    def __init__(self, execute_timeout: float = DEFAULT_EXECUTE_TIMEOUT) -> None:
        self._km: AsyncKernelManager | None = None
        self._kc = None  # AsyncKernelClient
        self._lock = asyncio.Lock()
        self._execute_timeout = execute_timeout

    async def start(self) -> None:
        """Launch the kernel and connect its channels. Idempotent."""
        if self._km is not None:
            return
        logger.info("Starting Jupyter kernel...")
        km = AsyncKernelManager()
        await asyncio.wait_for(km.start_kernel(), timeout=KERNEL_START_TIMEOUT)
        kc = km.client()
        kc.start_channels()
        await asyncio.wait_for(kc.wait_for_ready(timeout=KERNEL_START_TIMEOUT), timeout=KERNEL_START_TIMEOUT)
        self._km = km
        self._kc = kc
        logger.info("Jupyter kernel ready.")

    async def _ensure_alive(self) -> bool:
        """Ensure a live kernel exists. Returns True if a restart was performed
        (i.e. the namespace was reset), False if the existing kernel was healthy."""
        if self._km is not None and await self._km.is_alive():
            return False
        logger.warning("Kernel is not alive; (re)starting. In-memory namespace was lost.")
        await self._teardown()
        await self.start()
        return True

    async def execute(self, code: str) -> ExecutionResult:
        """Run ``code`` in the kernel and collect all output until it goes idle."""
        async with self._lock:
            result = ExecutionResult()
            result.namespace_reset = await self._ensure_alive()
            msg_id = self._kc.execute(code)
            try:
                await asyncio.wait_for(self._collect(msg_id, result), timeout=self._execute_timeout)
            except asyncio.TimeoutError:
                logger.warning("execute_python timed out after %ss; interrupting kernel.", self._execute_timeout)
                await self._km.interrupt_kernel()
                result.status = "error"
                result.error = {
                    "ename": "TimeoutError",
                    "evalue": f"Execution exceeded {self._execute_timeout:.0f}s and was interrupted.",
                    "traceback": "",
                }
                # Drain the interrupted cell's remaining io_pub traffic (the
                # KeyboardInterrupt error and trailing idle status) so the next
                # execute starts against a clean channel.
                await self._drain_until_idle(msg_id)
            return result

    async def _drain_until_idle(self, msg_id: str) -> None:
        """Consume and discard io_pub messages for ``msg_id`` up to its idle
        status, so a subsequent execute doesn't read stale output. Bounded by a
        short timeout so a wedged kernel can't hang us here forever."""
        try:
            while True:
                msg = await asyncio.wait_for(self._kc.get_iopub_msg(), timeout=5.0)
                if msg.get("parent_header", {}).get("msg_id") != msg_id:
                    continue
                if msg["header"]["msg_type"] == "status" and msg["content"].get("execution_state") == "idle":
                    return
        except asyncio.TimeoutError:
            logger.debug("Drain of interrupted cell %s timed out; continuing.", msg_id)

    async def _collect(self, msg_id: str, result: ExecutionResult) -> None:
        """Drain io_pub for ``msg_id`` until the kernel goes idle. The idle status
        on our own message is the authoritative end-of-execution signal in the
        Jupyter protocol."""
        stdout_parts: list[str] = []

        while True:
            msg = await self._kc.get_iopub_msg()
            parent = msg.get("parent_header", {})
            # Ignore io_pub traffic from unrelated executions (defensive: with the
            # lock held there should be none, but the channel can carry startup noise).
            if parent.get("msg_id") != msg_id:
                continue

            msg_type = msg["header"]["msg_type"]
            content = msg["content"]

            if msg_type == "status":
                if content.get("execution_state") == "idle":
                    break
            elif msg_type == "stream":
                stdout_parts.append(content.get("text", ""))
            elif msg_type == "execute_result":
                result.execution_count = content.get("execution_count")
                result.result = content.get("data", {}).get("text/plain")
            elif msg_type == "display_data":
                data = content.get("data", {})
                text = data.get("text/plain", "")
                mimes = [m for m in data if m != "text/plain"]
                note = f" [rich output: {', '.join(mimes)}]" if mimes else ""
                result.displays.append(text + note)
            elif msg_type == "error":
                result.status = "error"
                result.error = {
                    "ename": content.get("ename", ""),
                    "evalue": content.get("evalue", ""),
                    "traceback": _clean_traceback(content.get("traceback", [])),
                }

        result.stdout = "".join(stdout_parts)

    async def restart(self) -> None:
        """Restart the kernel, discarding all in-memory state."""
        async with self._lock:
            if self._km is not None:
                logger.info("Restarting Jupyter kernel (namespace reset).")
                await self._km.restart_kernel(now=True)
                await asyncio.wait_for(
                    self._kc.wait_for_ready(timeout=KERNEL_START_TIMEOUT), timeout=KERNEL_START_TIMEOUT
                )

    async def _teardown(self) -> None:
        """Stop channels and shut down the kernel, tolerating a dead process."""
        if self._kc is not None:
            try:
                self._kc.stop_channels()
            except Exception:
                logger.debug("Error stopping kernel channels", exc_info=True)
            self._kc = None
        if self._km is not None:
            try:
                await asyncio.wait_for(self._km.shutdown_kernel(now=True), timeout=KERNEL_SHUTDOWN_TIMEOUT)
            except Exception:
                logger.debug("Error shutting down kernel", exc_info=True)
            self._km = None

    async def shutdown(self) -> None:
        """Gracefully shut down the kernel on pod exit."""
        async with self._lock:
            logger.info("Shutting down Jupyter kernel.")
            await self._teardown()


# Module-level singleton. Started in main() at boot; imported by tools.py so the
# execute_python tool can reach the live kernel without threading it through the
# LangGraph state.
kernel_session = KernelSession()
