"""Standalone, isolated record application for bounded execution demonstrations.

Only immutable create and read endpoints exist. Run on IPv4 loopback, use fictional
records, and keep its separate runtime directory private. This is not a production
multi-user service or a bridge into another desktop application.
"""

import argparse
import html
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from .application_executor import APP_ID, SCHEMA_VERSION, RecordInput, canonical_origin


def create_demo_app(directory=None, origin=None):
    origin = canonical_origin(origin or os.environ.get("DESK_DEMO_APP_ORIGIN", ""))
    root = Path(directory or os.environ.get("DESK_DEMO_APP_DIR", ".runtime/demo-records"))
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    database = root / "records.sqlite3"

    @contextmanager
    def connection():
        conn = sqlite3.connect(database, timeout=5)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    with connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS identity (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        """)
        conn.execute("INSERT OR IGNORE INTO identity VALUES(1, ?)", (uuid4().hex,))
        instance_id = conn.execute("SELECT value FROM identity WHERE id=1").fetchone()[0]
    os.chmod(database, 0o600)
    app = FastAPI(title="Desk Companion isolated record application", docs_url=None, redoc_url=None)
    app.state.database = database
    app.state.instance_id = instance_id

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        if request.headers.get("host") != origin.removeprefix("http://"):
            return JSONResponse({"error": "TARGET_DENIED"}, status_code=403)
        if request.headers.get("origin") not in (None, origin):
            return JSONResponse({"error": "ORIGIN_DENIED"}, status_code=403)
        if request.method not in {"GET", "HEAD"}:
            size = request.headers.get("content-length", "")
            if request.headers.get("x-desk-demo") != "1":
                return JSONResponse({"error": "HEADER_REQUIRED"}, status_code=403)
            if not size.isascii() or not size.isdigit() or int(size) > 64_000:
                return JSONResponse({"error": "BODY_LIMIT"}, status_code=413)
            if request.headers.get("content-type", "").split(";")[0] != "application/json":
                return JSONResponse({"error": "JSON_REQUIRED"}, status_code=415)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response

    @app.get("/api/status")
    def status():
        return {"application": APP_ID, "instance_id": instance_id, "schema_version": SCHEMA_VERSION}

    @app.post("/api/records", status_code=201)
    def create(payload: RecordInput):
        if payload.instance_id != instance_id:
            raise HTTPException(409, "APPLICATION_INSTANCE_CHANGED")
        value = {**payload.model_dump(), "schema_version": SCHEMA_VERSION}
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT payload FROM records WHERE id=?", (payload.id,)
            ).fetchone()
            if existing:
                # Same generated ID + identical intent is safe if an operator explicitly
                # repeats a request. The job worker itself never retries dispatched writes.
                if existing["payload"] != encoded:
                    raise HTTPException(409, "RECORD_CONFLICT")
                return {"id": payload.id, "accepted": True}
            if conn.execute("SELECT COUNT(*) FROM records").fetchone()[0] >= 1000:
                raise HTTPException(429, "RECORD_LIMIT")
            conn.execute("INSERT INTO records VALUES(?,?)", (payload.id, encoded))
        # This acknowledgement alone is deliberately insufficient for verified success.
        return {"id": payload.id, "accepted": True}

    @app.get("/api/records/{record_id}")
    def read(record_id: str):
        if len(record_id) != 32 or any(c not in "0123456789abcdef" for c in record_id):
            raise HTTPException(404, "RECORD_NOT_FOUND")
        with connection() as conn:
            row = conn.execute("SELECT payload FROM records WHERE id=?", (record_id,)).fetchone()
        if not row:
            raise HTTPException(404, "RECORD_NOT_FOUND")
        return json.loads(row["payload"])

    @app.get("/", response_class=HTMLResponse)
    def page():
        with connection() as conn:
            rows = conn.execute(
                "SELECT payload FROM records ORDER BY rowid DESC LIMIT 100"
            ).fetchall()
            count = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        items = "".join(
            "<article><h2>"
            + html.escape(record["title"])
            + "</h2><p>Record "
            + html.escape(record["id"])
            + "</p><pre>"
            + html.escape(record["content"])
            + "</pre></article>"
            for record in (json.loads(row["payload"]) for row in rows)
        )
        return (
            "<!doctype html><html lang='en'><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Isolated record application</title><main><h1>Isolated record application</h1>"
            "<p>API-controlled local demonstration. Refresh to read persisted records. "
            "Fictional test data only. No desktop control.</p><p>Instance: "
            + instance_id
            + f" · {count} records (latest 100 shown)</p>"
            + (items or "<p>No records saved.</p>")
            + "</main></html>"
        )

    return app


def main():
    import uvicorn

    parser = argparse.ArgumentParser(description="Run the isolated loopback record application")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--directory", required=True)
    args = parser.parse_args()
    origin = canonical_origin(f"http://127.0.0.1:{args.port}")
    uvicorn.run(
        create_demo_app(args.directory, origin), host="127.0.0.1", port=args.port, access_log=False
    )


if __name__ == "__main__":
    main()
