"""The SSH web entry must retain the normal origin, login and write boundaries."""

import pytest
from fastapi.testclient import TestClient

from desk.app import create_app


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost"])
def test_pi_tunnel_can_sign_in_but_still_requires_request_header(tmp_path, host):
    app = create_app(tmp_path, password="synthetic-pi-test", scheduler=False)
    with TestClient(app, base_url=f"http://{host}:8891") as client:
        client.headers["Origin"] = f"http://{host}:8891"
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/session").status_code == 401
        payload = {"username": "owner", "password": "synthetic-pi-test"}
        denied = client.post("/api/session", json=payload)
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "REQUEST_HEADER_REQUIRED"
        client.headers["X-Desk-Request"] = "1"
        assert client.post("/api/session", json=payload).status_code == 200
        assert client.get("/api/session").json()["principal"]["kind"] == "owner"


@pytest.mark.parametrize(
    "origin",
    ["http://192.168.49.5:8891", "http://127.0.0.1:8892", "https://example.test:8891"],
)
def test_pi_tunnel_does_not_allow_other_hosts_or_ports(tmp_path, origin):
    app = create_app(tmp_path, password="synthetic-pi-test", scheduler=False)
    with TestClient(app) as client:
        result = client.get("/api/health", headers={"Origin": origin})
        assert result.status_code == 403
        assert result.json()["error"]["code"] == "ORIGIN_NOT_ALLOWED"
