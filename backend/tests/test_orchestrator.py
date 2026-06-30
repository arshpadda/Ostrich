import uuid
from unittest.mock import MagicMock, patch

from kubernetes import client

from src.controlplane.services import orchestrator


def _fake_api(get_returns):
    api = MagicMock()
    api.get_namespaced_custom_object.side_effect = get_returns
    return api


def test_claim_sandbox_returns_resolved_name():
    uid = uuid.uuid4()
    # First poll: no sandbox yet; second poll: resolved.
    api = _fake_api(
        [
            {"status": {}},
            {"status": {"sandbox": {"name": "ostrich-warmpool-abc12"}}},
        ]
    )
    with patch.object(orchestrator.client, "CustomObjectsApi", return_value=api):
        name = orchestrator.claim_sandbox(uid)
    assert name == "ostrich-warmpool-abc12"
    api.create_namespaced_custom_object.assert_called_once()


def test_claim_sandbox_reuses_existing_claim_on_conflict():
    uid = uuid.uuid4()
    api = _fake_api([{"status": {"sandbox": {"name": "sb-existing"}}}])
    api.create_namespaced_custom_object.side_effect = client.exceptions.ApiException(status=409)
    with patch.object(orchestrator.client, "CustomObjectsApi", return_value=api):
        name = orchestrator.claim_sandbox(uid)
    assert name == "sb-existing"


def test_release_sandbox_deletes_claim():
    uid = uuid.uuid4()
    api = MagicMock()
    with patch.object(orchestrator.client, "CustomObjectsApi", return_value=api):
        orchestrator.release_sandbox(uid)
    api.delete_namespaced_custom_object.assert_called_once()
    assert api.delete_namespaced_custom_object.call_args.args[-1] == f"claim-{uid}"
