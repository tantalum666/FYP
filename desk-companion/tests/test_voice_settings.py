import pytest
from fastapi.testclient import TestClient
from desk.app import create_app
from desk.store import DomainError
from desk.voice_settings import (
    VoiceRegistration,
    VoiceSelection,
    VoiceSettings,
    selected_voice_payload,
)


def test_voice_choice_persists_without_changing_environment_or_credentials(tmp_path):
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
    settings = runtime.voice.settings
    assert settings.current("marin")["voice"] == "marin"
    registration = VoiceRegistration(
        expected_version=1,
        id="voice_fixture",
        name="Alice fixture",
        description="A clear warm original adult voice.",
    )
    result = settings.register(registration, "register")
    assert settings.register(registration, "register") == result
    selected = VoiceSelection(
        expected_version=2,
        voice="voice_fixture",
        delivery="Natural Mandarin, Cantonese and English.",
    )
    first = settings.select(selected, "select")
    assert settings.select(selected, "select") == first
    restored = VoiceSettings(runtime.store).current("marin")
    assert restored["voice"] == "voice_fixture" and restored["version"] == 3
    assert restored["description"] == registration.description
    assert not (tmp_path / "service.env").exists()
    assert selected_voice_payload("voice_fixture") == {"id": "voice_fixture"}
    assert selected_voice_payload("gleam") == "gleam"
    with pytest.raises(DomainError):
        settings.select(VoiceSelection(expected_version=3, voice="voice_unknown"), "unknown")
    with pytest.raises(DomainError):
        settings.select(VoiceSelection(expected_version=1, voice="marin"), "stale")


def test_voice_preferences_require_owner_and_reject_mid_call_change(tmp_path):
    app = create_app(tmp_path, password="fixture", scheduler=False)
    client = TestClient(app, base_url="http://127.0.0.1:8831", client=("127.0.0.1", 50001))
    headers = {
        "Origin": "http://127.0.0.1:8831",
        "X-Desk-Request": "1",
        "X-Operation-Id": "select-voice",
    }
    assert client.get("/api/voice/settings").status_code == 401
    assert client.post("/api/session/connect", headers=headers, json={}).status_code == 200
    settings = client.get("/api/voice/settings").json()
    app.state.runtime.voice.active = True
    response = client.post(
        "/api/voice/settings",
        headers=headers,
        json={
            "expected_version": settings["version"],
            "voice": "gleam",
            "delivery": "Natural phrasing.",
        },
    )
    assert response.status_code == 409 and response.json()["error"]["code"] == "VOICE_BUSY"
    app.state.runtime.voice.active = False
    response = client.post(
        "/api/voice/settings",
        headers=headers,
        json={
            "expected_version": settings["version"],
            "voice": "gleam",
            "delivery": "Natural phrasing.",
        },
    )
    assert response.status_code == 200 and response.json()["voice"] == "gleam"
    assert client.get("/api/voice/settings/sample/unknown").status_code == 404
    with app.state.store.connection() as db:
        assert not db.execute("SELECT details FROM records WHERE action='voice_session'").fetchall()
