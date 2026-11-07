from http.cookiejar import CookieJar
from fastapi.testclient import TestClient
from desk.app import create_app


def test_two_local_backends_keep_independent_cookies_and_no_refresh_loop(tmp_path):
    apps = [
        create_app(tmp_path / name, password="fixture", scheduler=False) for name in ["mac", "pi"]
    ]
    ports = [5190, 8891]
    clients = [
        TestClient(app, base_url=f"http://127.0.0.1:{port}", client=("127.0.0.1", 40000))
        for app, port in zip(apps, ports)
    ]
    jar = CookieJar()
    for client in clients:
        client.cookies.jar = jar
    for client, port in zip(clients, ports):
        response = client.post(
            "/api/session/connect",
            headers={"X-Desk-Request": "1", "Origin": f"http://127.0.0.1:{port}"},
        )
        assert response.status_code == 200
        assert f"desk_companion_session_p{port}=" in response.headers["set-cookie"]
    for _ in range(4):
        for client in clients:
            assert client.get("/api/workspace").status_code == 200
            assert client.get("/api/computer/jobs").status_code == 200
    for app in apps:
        with app.state.store.connection() as db:
            assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1
    clients[0].delete("/api/session", headers={"X-Desk-Request": "1"})
    assert clients[0].get("/api/session").status_code == 401
    assert clients[1].get("/api/session").status_code == 200


def test_unscoped_cookie_cannot_be_mistaken_for_local_backend_session(tmp_path):
    app = create_app(tmp_path, password="fixture", scheduler=False)
    client = TestClient(app, base_url="http://127.0.0.1:5190", client=("127.0.0.1", 40000))
    token = app.state.store.create_owner_session()
    client.cookies.set("desk_companion_session", token, path="/api")
    assert client.get("/api/session").status_code == 401
    assert (
        client.post(
            "/api/session/connect",
            headers={"X-Desk-Request": "1", "Origin": "http://127.0.0.1:5190"},
        ).status_code
        == 200
    )
    assert client.get("/api/session").status_code == 200
