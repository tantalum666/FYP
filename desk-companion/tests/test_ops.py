"""Structured logs, owner diagnostics, and the local backup schedule."""

import logging
import stat
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.backups import CHECK_INTERVAL_SECONDS, RETENTION
from desk.diagnostics import diagnostics_report
from desk.log import redact


PASSWORD = "fixture-secret"
API_KEY = "super-secret-key"


class Capture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


@pytest.fixture
def captured():
    handler = Capture()
    logging.getLogger("desk").addHandler(handler)
    try:
        yield handler
    finally:
        logging.getLogger("desk").removeHandler(handler)


def _app(tmp_path, monkeypatch, clock=None):
    monkeypatch.setenv("DESK_TEXT_PROVIDER", "qwen")
    monkeypatch.setenv("DESK_TEXT_MODEL", "qwen-test")
    monkeypatch.setenv(
        "DESK_TEXT_ENDPOINT",
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
    )
    monkeypatch.setenv("DESK_TEXT_API_KEY", API_KEY)
    monkeypatch.setenv("DESK_TEXT_BACKGROUND", "1")
    return create_app(tmp_path, password=PASSWORD, scheduler=False, clock=clock)


def test_redaction_covers_structured_fields_query_values_and_bearer_tokens():
    hidden = redact(
        {
            "password": PASSWORD,
            "nested": {"api_key": API_KEY, "title": "visible"},
            "query": "code=oauth-secret&ok=1",
            "note": "Authorization: Bearer abc.def-ghi",
        }
    )
    text = str(hidden)
    assert PASSWORD not in text and API_KEY not in text and "oauth-secret" not in text
    assert "abc.def-ghi" not in text
    assert hidden["nested"]["title"] == "visible"
    assert hidden["query"] == "code=[redacted]&ok=1"


def test_http_log_redacts_the_query_and_omits_the_login_body(tmp_path, monkeypatch, captured):
    app = _app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        client.headers["X-Desk-Request"] = "1"
        client.get("/api/health", params={"code": "oauth-secret", "ok": "1"})
        client.post("/api/session", json={"username": "owner", "password": PASSWORD})
    text = "\n".join(captured.messages)
    assert "oauth-secret" not in text
    assert "code=[redacted]" in text and "ok=1" in text
    assert PASSWORD not in text
    assert "/api/session" in text


def test_owner_diagnostics_hide_secrets_and_report_cap_and_schedule(
    tmp_path, monkeypatch, captured
):
    clock = [datetime(2026, 10, 2, tzinfo=UTC)]
    app = _app(tmp_path, monkeypatch, clock=lambda: clock[0])
    app.state.runtime.worker_health["rules"] = "ready"
    app.state.runtime.worker_health["task_advice"] = "traceback api_key=super-secret-key"
    with app.state.store.connection(write=True) as conn:
        conn.execute(
            "INSERT INTO text_ai_usage VALUES(?,?,?,?,?)",
            ("today", "2026-10-02T01:00:00.000000Z", "followup", "qwen", "{}"),
        )
        conn.execute(
            "INSERT INTO text_ai_usage VALUES(?,?,?,?,?)",
            ("yesterday", "2026-10-01T23:00:00.000000Z", "followup", "qwen", "{}"),
        )
        conn.execute(
            "INSERT INTO text_ai_usage VALUES(?,?,?,?,?)",
            ("other", "2026-10-02T02:00:00.000000Z", "reply", "qwen", "{}"),
        )
    assert ("local_backup", CHECK_INTERVAL_SECONDS) in app.state.scheduled
    with TestClient(app) as client:
        client.headers["X-Desk-Request"] = "1"
        assert client.get("/api/diagnostics").status_code == 403
        client.cookies.set("desk_companion_device", "not-the-owner", path="/api")
        assert client.get("/api/diagnostics").status_code == 403
        assert (
            client.post(
                "/api/session", json={"username": "owner", "password": PASSWORD}
            ).status_code
            == 200
        )
        body = client.get("/api/diagnostics")
        page = client.get("/api/diagnostics/page")
    report = body.json()
    text = body.text + page.text
    assert body.status_code == 200 and page.status_code == 200
    assert "default-src 'none'" in page.headers["content-security-policy"]
    assert report["versions"]["service"] == "0.1.0"
    assert report["provider"]["configured"] is True
    assert report["provider"]["name"] == "qwen"
    assert report["provider"]["cap_used"] == 1
    assert report["provider"]["cap_limit"] == 20
    assert report["database"]["bytes"] > 0
    assert report["backup"]["last_at"] is None
    assert report["scheduler"]["ticks"] == {
        "rules": "ready",
        "task_advice": "retrying_after_error",
    }
    assert API_KEY not in text and PASSWORD not in text and "qwen-test" not in text
    assert "dashscope" not in text and str(tmp_path) not in text
    assert "<h1>Diagnostics</h1>" in page.text


def test_scheduled_backup_retains_seven_regular_files(tmp_path, monkeypatch, captured):
    clock = [datetime(2026, 10, 2, tzinfo=UTC)]
    app = _app(tmp_path, monkeypatch, clock=lambda: clock[0])
    backups = app.state.runtime.backups
    outside = tmp_path / "outside.txt"
    outside.write_text("keep-me")
    first = backups.tick()
    assert first["written"] is True
    assert backups.tick()["written"] is False
    backup_dir = backups.directory
    assert stat.S_IMODE(backup_dir.stat().st_mode) == 0o700
    saved = next(backup_dir.glob("desk-*.sqlite3"))
    assert stat.S_IMODE(saved.stat().st_mode) == 0o600
    assert PASSWORD.encode() not in saved.read_bytes()
    assert API_KEY.encode() not in saved.read_bytes()
    assert not (backup_dir / "credentials.json").exists()
    (backup_dir / "notes.txt").write_text("leave this")
    link = backup_dir / "desk-19990101T000000Z.sqlite3"
    link.symlink_to(outside)
    clock[0] += timedelta(hours=23, minutes=59)
    assert backups.tick()["written"] is False
    for _ in range(RETENTION):
        clock[0] += timedelta(hours=24)
        backups.tick()
    names = sorted(path.name for path in backup_dir.glob("desk-*.sqlite3"))
    regular = [name for name in names if not (backup_dir / name).is_symlink()]
    assert len(regular) == RETENTION
    assert link.is_symlink() and outside.read_text() == "keep-me"
    assert (backup_dir / "notes.txt").read_text() == "leave this"
    described = backups.describe()
    assert described["retained"] == RETENTION
    assert described["file_name"] == regular[-1]
    assert str(backup_dir) not in described["file_name"]
    report = diagnostics_report(app.state.runtime, "0.1.0")
    assert report["backup"]["file_name"] == regular[-1]
    assert API_KEY not in str(report)


def test_backup_failure_logs_the_exception_type_only(tmp_path, monkeypatch, captured):
    app = _app(tmp_path, monkeypatch, clock=lambda: datetime(2026, 10, 2, tzinfo=UTC))

    def boom(_path):
        raise RuntimeError("api_key=" + API_KEY)

    monkeypatch.setattr(app.state.store, "backup", boom)
    with pytest.raises(RuntimeError):
        app.state.runtime.backups.tick()
    assert app.state.runtime.backups.health == "retrying_after_error"
    text = "\n".join(captured.messages)
    assert "RuntimeError" in text
    assert API_KEY not in text
