import logging
import os
import subprocess
import sys
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
        sandbox_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../sandbox"))
        env = os.environ.copy()
        env["USER_ID"] = str_id
        env["REDIS_URL"] = settings.REDIS_URL
        env["PYTHONUNBUFFERED"] = "1"
        env["LLM_MODEL"] = os.getenv("LLM_MODEL", "gemini-2.5-flash")
        env["FALLBACK_LLM_MODEL"] = os.getenv("FALLBACK_LLM_MODEL", "")
        # Bind metrics to an ephemeral port locally so it never collides with
        # other services (in-cluster the pod keeps the fixed 8000 for scraping).
        env["METRICS_PORT"] = os.getenv("SANDBOX_METRICS_PORT", "0")
        if settings.GEMINI_API_KEY:
            env["GEMINI_API_KEY"] = settings.GEMINI_API_KEY

        # The sandbox has its own virtualenv (langgraph, langchain-openai, etc.) that
        # the control-plane venv lacks, so spawn it with the sandbox interpreter and
        # run it as a module from the sandbox dir — mirroring the container's
        # `python -m src.main` so the `src` package imports resolve.
        venv_python = os.path.join(sandbox_dir, ".venv", "bin", "python")
        python_exe = venv_python if os.path.exists(venv_python) else sys.executable

        log_file_path = os.path.join(sandbox_dir, os.pardir, f"sandbox-{str_id}.log")
        # Popen dups the fd, so closing our handle after launch is safe (no leak).
        with open(log_file_path, "a") as log_file:
            proc = subprocess.Popen(
                [python_exe, "-m", "src.main"],
                cwd=sandbox_dir,
                env=env,
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )
        local_sandboxes[str_id] = proc
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
            client.V1EnvVar(name="GEMINI_API_KEY", value=settings.GEMINI_API_KEY),
            client.V1EnvVar(name="OTEL_EXPORTER_OTLP_ENDPOINT", value="http://host.minikube.internal:4317"),
            client.V1EnvVar(name="OTEL_SERVICE_NAME", value="ostrich-sandbox"),
            client.V1EnvVar(name="LLM_MODEL", value=os.getenv("LLM_MODEL", "openai/gemini-2.5-flash")),
            client.V1EnvVar(name="FALLBACK_LLM_MODEL", value=os.getenv("FALLBACK_LLM_MODEL", "")),
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
        return True
    except client.exceptions.ApiException as e:
        logger.error(f"Failed to provision sandbox pod {pod_name}: {e}")
        return False
