"""Actual authenticated HTTP boundary; no external connector call in these tests."""

from uuid import uuid4

from fastapi.testclient import TestClient

from desk.app import create_app
from desk.connectors.contracts import ConnectorConfig, ToolGrant
from desk.connectors.schema import digest
from desk.schemas import SettingsInput

SCHEMA = {
    "type": "object",
    "properties": {"query": {"type": "string", "maxLength": 100}},
    "required": ["query"],
    "additionalProperties": False,
}
DESCRIPTOR = {"name": "search", "inputSchema": SCHEMA}
CONFIG = ConnectorConfig(
    id="publicdocs",
    endpoint="https://fixture.example/mcp",
    server_name="Fixture",
    server_version="1",
    tools=[
        ToolGrant(
            tool_name="search",
            descriptor_sha256=digest(DESCRIPTOR),
            effect="read",
            input_schema=SCHEMA,
            destination_scope="Public documentation fixture only",
        )
    ],
)


def login(client):
    client.headers["X-Desk-Request"] = "1"
    client.headers["X-Operation-Id"] = uuid4().hex
    assert (
        client.post(
            "/api/session", json={"username": "owner", "password": "fixture-only"}
        ).status_code
        == 200
    )
    return {"kind": "owner", "session": client.cookies.get("desk_companion_session")}


class CatalogFixture:
    """No-network catalog fixture; actual MCP protocol has separate HTTP tests."""

    def __init__(self, config):
        self.config = config

    def discover(self, checkpoint):
        checkpoint()
        return {"search": {"descriptor_sha256": digest(DESCRIPTOR), "descriptor": DESCRIPTOR}}


def prepare(app, principal):
    app.state.runtime.connectors.client_factory = CatalogFixture
    return app.state.runtime.connectors.prepare(
        "mcp.publicdocs.search",
        {"query": "Fictional public docs"},
        uuid4().hex,
        principal,
        public_only=True,
    )


def test_default_disabled_and_authentication(tmp_path):
    app = create_app(tmp_path, password="fixture-only", scheduler=False, connector_configs=[])
    with TestClient(app) as client:
        assert client.get("/api/connectors/capabilities").status_code in {401, 403}
        login(client)
        assert client.get("/api/connectors/capabilities").json()["tools"] == []
        assert client.get("/api/connectors/intents").json() == {"intents": []}
    assert app.state.runtime.connectors.stopped


def test_review_exact_hash_public_ack_version_and_cancellation(tmp_path):
    app = create_app(tmp_path, password="fixture-only", scheduler=False, connector_configs=[CONFIG])
    with TestClient(app) as client:
        owner = login(client)
        item = prepare(app, owner)
        path = f"/api/connectors/intents/{item['id']}"
        assert client.get(path).json()["intent"]["intent"]["arguments"] == {
            "query": "Fictional public docs"
        }
        approval = {
            "expected_version": item["version"],
            "intent_hash": item["intent_hash"],
            "public_only": True,
        }
        for field, value in (
            ("intent_hash", "0" * 64),
            ("expected_version", 99),
            ("public_only", False),
        ):
            response = client.post(path + "/approve", json={**approval, field: value})
            assert response.status_code in {403, 409, 422}, response.text
        assert (
            client.post(path + "/approve", json={**approval, "public_only": "true"}).status_code
            == 422
        )
        approved = client.post(path + "/approve", json=approval)
        assert approved.status_code == 200, approved.text
        assert approved.json()["intent"]["state"] == "queued"
        # Repeating approval returns same durable intent without executing anything.
        assert client.post(path + "/approve", json=approval).json()["intent"]["id"] == item["id"]
        current = approved.json()["intent"]
        cancelled = client.post(
            path + "/cancel?metadata_only=true", json={"expected_version": current["version"]}
        )
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["intent"]["state"] == "cancelled"
        assert cancelled.json()["intent"]["dispatched"] is False
        assert not ({"intent", "intent_hash", "result"} & cancelled.json()["intent"].keys())
        assert not app.state.runtime.connectors.advance_one()


def test_metadata_projection_hidden_cancel_and_session_rotation(tmp_path):
    app = create_app(tmp_path, password="fixture-only", scheduler=False, connector_configs=[CONFIG])
    with TestClient(app) as client:
        owner = login(client)
        item = prepare(app, owner)
        path = f"/api/connectors/intents/{item['id']}"
        metadata = client.get("/api/connectors/intents?metadata_only=true").json()["intents"]
        assert len(metadata) == 1
        direct_metadata = client.get(path + "?metadata_only=true").json()["intent"]
        assert not ({"intent", "intent_hash", "result"} & direct_metadata.keys())
        assert not ({"intent", "intent_hash", "result"} & metadata[0].keys())
        runtime = app.state.runtime
        with runtime.store.connection() as conn:
            version = runtime.store.settings(conn)["version"]
        runtime.store.update_settings(
            SettingsInput(expected_version=version, timezone="Asia/Hong_Kong", hide_private=True),
            uuid4().hex,
        )
        hidden = client.get(path).json()["intent"]
        assert not ({"intent", "intent_hash", "result"} & hidden.keys())
        assert client.get("/api/connectors/capabilities").status_code == 403
        stopped = client.post(path + "/cancel", json={"expected_version": hidden["version"]})
        assert stopped.status_code == 200, stopped.text
        assert "intent_hash" not in stopped.json()["intent"]
        with runtime.store.connection() as conn:
            version = runtime.store.settings(conn)["version"]
        runtime.store.update_settings(
            SettingsInput(expected_version=version, timezone="Asia/Hong_Kong", hide_private=False),
            uuid4().hex,
        )
        second = prepare(app, owner)
        client.delete("/api/session")
        assert client.get(path).status_code in {401, 403}
        login(client)
        response = client.post(
            f"/api/connectors/intents/{second['id']}/approve",
            json={
                "expected_version": second["version"],
                "intent_hash": second["intent_hash"],
                "public_only": True,
            },
        )
        assert response.status_code == 403


def test_public_operation_id_cannot_impersonate_review_receipt(tmp_path):
    app = create_app(tmp_path, password="fixture-only", scheduler=False, connector_configs=[])
    with TestClient(app) as client:
        login(client)
        client.headers["X-Operation-Id"] = "assistant-confirm/not-a-real-proposal"
        response = client.post("/api/tasks", json={"title": "Unrelated fictional task"})
        assert response.status_code == 422
        assert "RESERVED_OPERATION_ID" in response.text
        assert app.state.runtime.tasks.listing()["tasks"] == []
