"""Create (never reset) an isolated local M1.2 UI-test database and private credentials."""

import json
from pathlib import Path
import secrets
import sys

import psycopg
from psycopg import sql
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api"))
from senplate_api.app import passwords  # noqa: E402
from senplate_api.database import prepare_database  # noqa: E402
from senplate_api.models import Membership, User, Workspace  # noqa: E402

state = ROOT / ".runtime"
assert (state / "SENPLATE_LOCAL_ONLY").is_file()
config = json.loads((state / "config.json").read_text())
url = make_url(config["database_url"]).set(database="senplate_meals_qa")
assert url.host == "127.0.0.1" and url.port == 55437 and url.database == "senplate_meals_qa"
with psycopg.connect(
    host=url.host,
    port=url.port,
    user=url.username,
    password=url.password,
    dbname="postgres",
    autocommit=True,
) as db:
    if not db.execute("SELECT 1 FROM pg_database WHERE datname=%s", [url.database]).fetchone():
        db.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(url.database)))


def private(name, value):
    path = state / name
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    path.chmod(0o600)


engine = create_engine(url)
prepare_database(engine)
credentials_path = state / "meals-qa-credentials.json"
with Session(engine) as db:
    ws = db.scalar(select(Workspace))
    if not ws:
        ws = Workspace(name="Meal workflow QA")
        db.add(ws)
        db.flush()
    accounts = []
    for username, name, role in [
        ("qa-personal", "Jamie QA", None),
        ("qa-manager", "Alex QA", "manager"),
    ]:
        if db.scalar(select(User).where(User.username == username)):
            continue
        password = secrets.token_urlsafe(18)
        user = User(username=username, name=name, password_hash=passwords.hash(password))
        db.add(user)
        db.flush()
        if role:
            db.add(Membership(user_id=user.id, workspace_id=ws.id, role=role))
        accounts.append({"username": username, "password": password, "role": role or "personal"})
    wsid = ws.id
    db.commit()
    if accounts:
        assert not credentials_path.exists(), (
            "Preserve existing QA credentials; inspect partial setup."
        )
        private(credentials_path.name, {"workspace_id": wsid, "accounts": accounts})
engine.dispose()
qa_path = state / "meals-qa-config.json"
if not qa_path.exists():
    private(
        qa_path.name,
        {
            "database_url": url.render_as_string(hide_password=False),
            "device_key": secrets.token_urlsafe(32),
            "simulator_key": secrets.token_urlsafe(32),
            "development": True,
            "console_key": secrets.token_urlsafe(32),
            "console_workspace_id": wsid,
            "allowed_origins": [
                "http://localhost:5178",
                "http://127.0.0.1:5178",
                "http://localhost:8800",
                "http://127.0.0.1:8800",
            ],
        },
    )
print(
    "Isolated meal QA ready: senplate_meals_qa / API 8800 / Web 5178. Existing demo data preserved."
)
