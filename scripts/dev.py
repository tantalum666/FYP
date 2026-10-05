#!/usr/bin/env python3
"""Manage only this repository's local PostgreSQL cluster and demo accounts."""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".runtime"
PG = STATE / "postgres"
PG_PORT = 55437


def write_private(path, data):
    path.write_text(data)
    path.chmod(0o600)


def command(*args):
    subprocess.run(list(map(str, args)), check=True, cwd=ROOT)


def start_database():
    if not (STATE / "SENPLATE_LOCAL_ONLY").exists():
        raise SystemExit("Run setup first. No existing database will be altered.")
    running = subprocess.run(["pg_ctl", "-D", str(PG), "status"], capture_output=True).returncode == 0
    if not running:
        command("pg_ctl", "-D", PG, "-l", STATE / "postgres.log", "-w", "start")


def setup():
    if not shutil.which("initdb"):
        raise SystemExit("PostgreSQL binaries are required. Install PostgreSQL before setup.")
    STATE.mkdir(exist_ok=True)
    STATE.chmod(0o700)
    if not (PG / "PG_VERSION").exists():
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", PG_PORT))
            except OSError:
                raise SystemExit(f"Port {PG_PORT} is occupied; setup did not touch that service.")
        write_private(STATE / "pg-password", secrets.token_urlsafe(30))
        command("initdb", "-D", PG, "-U", "senplate", "--encoding=UTF8", "--locale=C",
                "--auth-host=scram-sha-256", "--auth-local=scram-sha-256",
                "--pwfile=" + str(STATE / "pg-password"))
        (STATE / "pgsocket").mkdir(exist_ok=True)
        with (PG / "postgresql.conf").open("a") as file:
            file.write(f"\nlisten_addresses = '127.0.0.1'\nport = {PG_PORT}\n")
            file.write("unix_socket_directories = '" + str(STATE / "pgsocket") + "'\n")
            file.write("max_connections = 30\nshared_buffers = '64MB'\n")
        (STATE / "SENPLATE_LOCAL_ONLY").write_text("Owned by this Senplate development workspace.\n")
    start_database()
    password = (STATE / "pg-password").read_text().strip()
    import psycopg
    from psycopg import sql
    with psycopg.connect(host="127.0.0.1", port=PG_PORT, user="senplate", password=password,
                        dbname="postgres", autocommit=True) as db:
        for name in ["senplate", "senplate_test"]:
            if not db.execute("SELECT 1 FROM pg_database WHERE datname=%s", [name]).fetchone():
                db.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    config_file = STATE / "config.json"
    if not config_file.exists():
        write_private(config_file, json.dumps({
            "database_url": f"postgresql+psycopg://senplate:{quote(password)}@127.0.0.1:{PG_PORT}/senplate",
            "device_key": secrets.token_urlsafe(32), "simulator_key": secrets.token_urlsafe(32),
            "development": True,
        }, indent=2))
    config = json.loads(config_file.read_text())
    if not config.get("console_key"):
        config["console_key"] = secrets.token_urlsafe(32)
        write_private(config_file, json.dumps(config, indent=2))
    seed()
    credentials = json.loads((STATE / "credentials.json").read_text())
    config["console_workspace_id"] = credentials["workspace_id"]
    write_private(config_file, json.dumps(config, indent=2))
    write_private(STATE / "station-console.json", json.dumps({
        "workspace_id": credentials["workspace_id"], "setup_key": config["console_key"]}, indent=2))
    print("Ready. Local credentials: " + str(STATE / "credentials.json"))
    print("API: uv run python scripts/dev.py api")
    print("Web: cd apps/operations-web && npm run dev")


def seed():
    sys.path.insert(0, str(ROOT / "services/api"))
    from senplate_api.app import passwords
    from senplate_api.config import load_settings
    from senplate_api.models import Membership, User, Workspace
    from senplate_api.database import prepare_database
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    engine = create_engine(load_settings().database_url)
    prepare_database(engine)
    credentials = []
    with Session(engine) as db:
        workspace = db.scalar(select(Workspace))
        if not workspace:
            workspace = Workspace(name="示范餐厅")
            db.add(workspace)
            db.flush()
        workspace.name = "示范餐厅"
        for username, name, role in [("manager", "Alex", "manager"), ("kitchen", "Sam", "staff"),
                                     ("viewer", "Taylor", "viewer"), ("personal", "Jamie", None)]:
            if db.scalar(select(User).where(User.username == username)):
                continue
            password = secrets.token_urlsafe(12)
            user = User(username=username, name=name, password_hash=passwords.hash(password))
            db.add(user)
            db.flush()
            if role:
                db.add(Membership(user_id=user.id, workspace_id=workspace.id, role=role))
            credentials.append({"username": username, "password": password, "role": role or "personal"})
        db.commit()
        if credentials:
            write_private(STATE / "credentials.json", json.dumps({"workspace_id": workspace.id,
                          "accounts": credentials}, ensure_ascii=False, indent=2))
    engine.dispose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["setup", "db", "api", "stop-db"])
    args = parser.parse_args()
    if args.action == "setup":
        setup()
    elif args.action == "db":
        start_database()
    elif args.action == "api":
        start_database()
        os.execvp("uv", ["uv", "run", "uvicorn", "senplate_api.app:create_app", "--factory",
                         "--app-dir", str(ROOT / "services/api"), "--host", "127.0.0.1", "--port", "8799"])
    else:
        if not (STATE / "SENPLATE_LOCAL_ONLY").exists():
            raise SystemExit("No owned cluster to stop.")
        command("pg_ctl", "-D", PG, "-m", "fast", "-w", "stop")


if __name__ == "__main__":
    main()
