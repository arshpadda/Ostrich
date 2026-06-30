"""Sandbox lifecycle via the agent-sandbox (kubernetes-sigs) controller.

The control plane claims a pre-warmed sandbox from a SandboxWarmPool by creating
a SandboxClaim custom resource and reading back the assigned sandbox's name. That
name is the pod's stable hostname, which the in-pod worker uses as its Redis
channel key (channel:sandbox:<name>). We talk to the CRDs directly with the
kubernetes client rather than the agent-sandbox SDK: the SDK is oriented around
exec/port-forward connections we don't use (our data plane is Redis pub/sub).
"""

import logging
import time
import uuid

from kubernetes import client, config

from ..core.config import settings

logger = logging.getLogger(__name__)

GROUP = "extensions.agents.x-k8s.io"
VERSION = "v1beta1"
CLAIM_PLURAL = "sandboxclaims"


def _load_kube_config() -> None:
    """In-cluster config when running as a pod, else a (optionally pinned) kubeconfig context."""
    try:
        config.load_incluster_config()
        return
    except config.ConfigException:
        pass
    try:
        config.load_kube_config(context=settings.SANDBOX_KUBE_CONTEXT or None)
    except config.ConfigException:
        logger.warning("Could not configure kubernetes client. Is KUBECONFIG set?")


_load_kube_config()


def _claim_name(user_id: uuid.UUID) -> str:
    return f"claim-{user_id}"


def claim_sandbox(user_id: uuid.UUID) -> str | None:
    """Claim (idempotently) a warm sandbox for the user and return its name.

    The returned name is the sandbox/pod hostname and the Redis channel key.
    Reused across reconnects via the deterministic claim name. Returns None if
    the claim never resolves within the configured timeout.
    """
    api = client.CustomObjectsApi()
    ns = settings.SANDBOX_NAMESPACE
    name = _claim_name(user_id)
    body = {
        "apiVersion": f"{GROUP}/{VERSION}",
        "kind": "SandboxClaim",
        "metadata": {"name": name},
        "spec": {
            "warmPoolRef": {"name": settings.SANDBOX_WARMPOOL},
            # Deleting the claim (on disconnect) tears the sandbox down.
            "lifecycle": {"shutdownPolicy": "Delete"},
        },
    }
    try:
        api.create_namespaced_custom_object(GROUP, VERSION, ns, CLAIM_PLURAL, body)
        logger.info("Created SandboxClaim %s", name)
    except client.exceptions.ApiException as e:
        if e.status != 409:  # 409 = already claimed; reuse it
            logger.error("Failed to create SandboxClaim %s: %s", name, e)
            return None

    deadline = time.monotonic() + settings.SANDBOX_CLAIM_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            obj = api.get_namespaced_custom_object(GROUP, VERSION, ns, CLAIM_PLURAL, name)
        except client.exceptions.ApiException as e:
            logger.error("Failed to read SandboxClaim %s: %s", name, e)
            return None
        sandbox_name = (obj.get("status") or {}).get("sandbox", {}).get("name")
        if sandbox_name:
            logger.info("Claim %s resolved to sandbox %s", name, sandbox_name)
            return sandbox_name
        time.sleep(0.5)

    logger.error("SandboxClaim %s did not resolve within timeout", name)
    return None


def release_sandbox(user_id: uuid.UUID) -> None:
    """Delete the user's SandboxClaim, which tears down the sandbox (shutdownPolicy: Delete)."""
    api = client.CustomObjectsApi()
    name = _claim_name(user_id)
    try:
        api.delete_namespaced_custom_object(GROUP, VERSION, settings.SANDBOX_NAMESPACE, CLAIM_PLURAL, name)
        logger.info("Released SandboxClaim %s", name)
    except client.exceptions.ApiException as e:
        if e.status != 404:
            logger.error("Failed to delete SandboxClaim %s: %s", name, e)
