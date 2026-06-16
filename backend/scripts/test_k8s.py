import logging

from kubernetes import client, config

logger = logging.getLogger(__name__)

is_k8s_available = True
try:
    config.load_incluster_config()
except config.ConfigException:
    try:
        config.load_kube_config()
    except config.ConfigException:
        logger.warning("Could not configure kubernetes python client. Is KUBECONFIG set?")
        is_k8s_available = False

print("Available:", is_k8s_available)
if is_k8s_available:
    try:
        v1 = client.CoreV1Api()
        v1.list_namespaced_pod("default")
    except Exception as e:
        print("Error:", e)
