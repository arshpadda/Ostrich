import logging
import os
import subprocess
import time
import uuid

from kubernetes import client, config

from ..core.config import settings

logger = logging.getLogger(__name__)

# Initialize Kubernetes client
try:
    if not settings.USE_LOCAL_SANDBOX:
        config.load_incluster_config()
except config.ConfigException:
    try:
        if not settings.USE_LOCAL_SANDBOX:
            config.load_kube_config()
    except config.ConfigException:
        logger.warning("Could not configure kubernetes python client. Is KUBECONFIG set?")

# Global dictionary to keep track of local subprocesses
local_sandboxes = {}

# Cache to avoid redundant Kubernetes API calls (Bolt ⚡)
# Maps user_id (str) to the last time (float) the pod was confirmed running
pod_status_cache = {}


def clean_pod_status_cache():
    """Periodically cleans up old entries from the pod_status_cache to prevent unbounded memory growth."""
    current_time = time.time()
    expired_keys = [k for k, v in pod_status_cache.items() if (current_time - v) >= 60]
    for k in expired_keys:
        del pod_status_cache[k]


def provision_sandbox_pod(user_id: uuid.UUID):
    """
    Provisions a dedicated Kubernetes Sandbox Pod for the given user_id using gVisor,
    or runs it locally via subprocess if USE_LOCAL_SANDBOX is True.
    """
    if settings.USE_LOCAL_SANDBOX:
        str_id = str(user_id)
        if str_id in local_sandboxes and local_sandboxes[str_id].poll() is None:
            logger.info(f"Local sandbox for {str_id} is already running.")
            return True

        logger.info(f"Starting local sandbox subprocess for {str_id}")
        sandbox_path = os.path.join(os.path.dirname(__file__), "../../../../sandbox/main.py")
        env = os.environ.copy()
        env["USER_ID"] = str_id
        env["REDIS_URL"] = settings.REDIS_URL
        env["PYTHONUNBUFFERED"] = "1"
        if settings.GEMINI_API_KEY:
            env["GEMINI_API_KEY"] = settings.GEMINI_API_KEY

        import sys

        # Start as background subprocess and pipe logs
        log_file_path = os.path.join(os.path.dirname(__file__), f"../../../../sandbox-{str_id}.log")
        log_file = open(log_file_path, "a")
        proc = subprocess.Popen([sys.executable, sandbox_path], env=env, stdout=log_file, stderr=subprocess.STDOUT)
        local_sandboxes[str_id] = proc
        return True

    str_id = str(user_id)
    current_time = time.time()

    # Clean the cache periodically (e.g. 1 in 100 chance) to avoid memory leaks
    import random

    if random.random() < 0.01:
        clean_pod_status_cache()

    # Performance Note (Bolt ⚡):
    # Check our in-memory cache before making a synchronous Kubernetes API call.
    # This prevents adding ~100ms of latency to every single WebSocket message.
    if str_id in pod_status_cache and (current_time - pod_status_cache[str_id]) < 60:
        return True

    v1 = client.CoreV1Api()
    namespace = "sandbox-chat"  # Can be customized via env vars
    pod_name = f"sandbox-{user_id}"

    # Check if pod already exists
    try:
        existing_pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        if existing_pod:
            if existing_pod.status.phase in ["Failed", "Succeeded"]:
                logger.info(f"Sandbox pod {pod_name} is in {existing_pod.status.phase} state. Deleting to recreate.")
                v1.delete_namespaced_pod(name=pod_name, namespace=namespace, grace_period_seconds=0)
            else:
                logger.info(f"Sandbox pod {pod_name} already exists and is in {existing_pod.status.phase} state.")
                pod_status_cache[str_id] = current_time
                return True
    except client.exceptions.ApiException as e:
        if e.status != 404:
            logger.error(f"Error checking for pod {pod_name}: {e}")
            return False

    # Define the pod
    container = client.V1Container(
        name="agent-harness",
        image="ostrich-sandbox:latest",
        image_pull_policy="IfNotPresent",
        env=[
            client.V1EnvVar(name="USER_ID", value=str(user_id)),
            client.V1EnvVar(name="REDIS_URL", value="redis://redis.redis-system.svc.cluster.local:6379"),
            client.V1EnvVar(name="GCS_BUCKET_NAME", value="ostrich-agent-workspaces"),
        ],
        ports=[client.V1ContainerPort(container_port=8000, name="metrics")],
        resources=client.V1ResourceRequirements(
            requests={"cpu": "250m", "memory": "256Mi"}, limits={"cpu": "500m", "memory": "512Mi"}
        ),
        volume_mounts=[client.V1VolumeMount(mount_path="/workspace", name="workspace-vol")],
    )

    pod_spec = client.V1PodSpec(
        containers=[container],
        restart_policy="Never",
        service_account_name="sandbox-agent-sa",
        # Automatically terminate the pod after 30 minutes (1800 seconds)
        active_deadline_seconds=1800,
        volumes=[client.V1Volume(name="workspace-vol", empty_dir=client.V1EmptyDirVolumeSource())],
    )

    pod = client.V1Pod(
        metadata=client.V1ObjectMeta(
            name=pod_name,
            labels={"app": "sandbox", "user_id": str(user_id)},
            annotations={
                "prometheus.io/scrape": "true",
                "prometheus.io/port": "8000",
                "prometheus.io/path": "/metrics",
            },
        ),
        spec=pod_spec,
    )

    try:
        v1.create_namespaced_pod(namespace=namespace, body=pod)
        logger.info(f"Successfully provisioned sandbox pod: {pod_name} in {namespace}.")
        pod_status_cache[str_id] = current_time
        return True
    except client.exceptions.ApiException as e:
        logger.error(f"Failed to provision sandbox pod {pod_name}: {e}")
        return False
