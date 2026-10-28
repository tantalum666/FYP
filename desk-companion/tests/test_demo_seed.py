import importlib.util
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest


def seed(*args, **kwargs):
    path = Path(__file__).resolve().parents[1] / "scripts" / "seed_demo.py"
    spec = importlib.util.spec_from_file_location("seed_demo", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.seed(*args, **kwargs)


def test_demo_seed_is_offline_repeatable_and_refuses_other_directories(tmp_path):
    with pytest.raises(SystemExit):
        seed(tmp_path / "real-runtime")
    clock = lambda: datetime(2026, 10, 14, 2, tzinfo=UTC)  # noqa: E731
    runtime = seed(tmp_path / ".demo-runtime", clock=clock)
    again = seed(runtime, clock=clock)
    assert again == runtime
    conn = sqlite3.connect(runtime / "desk.sqlite3")
    conn.row_factory = sqlite3.Row
    memories = conn.execute("SELECT body FROM owner_memories WHERE state='active'").fetchall()
    assert [row["body"] for row in memories] == ["The owner studies at CUHK."]
    reminders = conn.execute("SELECT status FROM reminders").fetchall()
    assert any(row["status"] == "due" for row in reminders)
    jobs = conn.execute("SELECT state FROM computer_jobs ORDER BY rowid").fetchall()
    assert [row["state"] for row in jobs] == ["review", "review"]
    prefs = conn.execute("SELECT data FROM workspace_preferences").fetchone()["data"]
    assert '"quiet_start":"00:00"' in prefs and '"quiet_end":"23:59"' in prefs
    holds = conn.execute("SELECT held_until FROM task_quiet_holds").fetchall()
    assert len(holds) == 1
    assert (runtime / "credentials.json").stat().st_mode & 0o777 == 0o600
    conn.close()
    seed(runtime, refresh=True, clock=clock)
    assert Path(runtime / "credentials.json").is_file()
