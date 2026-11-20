"""Public Agents Sessions REST resources for the text surface, over the desk's pinned transport."""

import hashlib
import json
import re
import time

import httpx

from .bounded_json import bounded_json_request
from .alice_delivery import WIRE_LIMIT
from .openai_transport import OPENAI_API, SESSION_ID, model_proxy

SESSIONS = OPENAI_API + "/agents/sessions"
TURN_ID = re.compile(r"[A-Za-z0-9_-]{1,160}")


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _capture_creation_error(response):
    if (
        response.status_code != 400
        or response.request.method != "POST"
        or str(response.request.url) != SESSIONS
        or response.headers.get("content-encoding", "identity").lower() != "identity"
    ):
        return
    raw = bytearray()
    deadline = time.monotonic() + 3
    try:
        chunks = [response.content] if response.is_stream_consumed else response.iter_raw()
        for chunk in chunks:
            if len(raw) + len(chunk) > 4096 or time.monotonic() >= deadline:
                return
            raw.extend(chunk)
        error = json.loads(raw)["error"]
        response.extensions["desk_session_limit_rejected"] = (
            isinstance(error, dict)
            and error.get("code") == "unknown_parameter"
            and error.get("param") == "spend_control"
        )
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return


class SessionAPI:
    def __init__(self, config, transport, *, deadline):
        self.deadline = deadline
        self.client = httpx.Client(
            headers={"Authorization": "Bearer " + config.api_key, "OpenAI-Beta": "agents=v1"},
            proxy=model_proxy(config, transport),
            transport=transport,
            trust_env=False,
            follow_redirects=False,
            event_hooks={"response": [_capture_creation_error]},
            timeout=httpx.Timeout(8, connect=3),
        )

    def request(self, method, path="", *, body=None, params=None, key=None, deadline=None):
        if time.monotonic() >= self.deadline:
            raise TimeoutError()
        return bounded_json_request(
            self.client,
            method,
            SESSIONS + path,
            json_body=body,
            params=params,
            headers={"Idempotency-Key": key} if key else {},
            max_bytes=1_000_000,
            deadline=self.deadline if deadline is None else min(self.deadline, deadline),
            allow_empty=True,
        )

    def submit(self, sid, events, key):
        return self.request("POST", f"/{sid}/events", body={"events": events}, key=key)

    def latest_turn(self, sid):
        page = self.request("GET", f"/{sid}/turns", params={"order": "desc", "limit": 1})
        rows = page["data"]
        if not rows:
            return None
        turn = rows[0]
        if turn.get("subagent_id") or not TURN_ID.fullmatch(turn["id"]):
            raise ValueError("Unexpected root turn")
        return turn

    def answer(self, sid, turn_id, *, complete):
        page = self.request("GET", f"/{sid}/items", params={"order": "desc", "limit": 25})
        messages = [
            row
            for row in page["data"]
            if row.get("turn_id") == turn_id
            and row.get("type") == "message"
            and row.get("role") == "assistant"
            and row.get("phase") == "final_answer"
            and (not complete or row.get("status") == "completed")
        ]
        if len(messages) > 1:
            raise ValueError("Ambiguous final answer")
        if not messages:
            return ""
        parts = messages[0]["content"]
        text = "".join(part["text"] for part in parts if part.get("type") == "output_text").strip()
        if len(text) > WIRE_LIMIT:
            raise ValueError("Oversized answer")
        return text

    def locate(self, marker):
        page = self.request("GET", params={"metadata[fyp_request]": marker, "limit": 2})
        found = [s for s in page["data"] if s.get("metadata", {}).get("fyp_request") == marker]
        if len(found) == 1 and not page.get("has_more") and SESSION_ID.fullmatch(found[0]["id"]):
            return found[0]
        return None

    def snapshot(self, sid):
        try:
            return self.request("GET", "/" + sid)
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                return None
            raise

    def terminal_usage(self, sid, turn_id):
        if not isinstance(turn_id, str) or not TURN_ID.fullmatch(turn_id):
            return None
        try:
            turn = self.request("GET", f"/{sid}/turns/{turn_id}", deadline=time.monotonic() + 1.5)
            if (turn.get("id") == turn_id and turn.get("session_id", sid) == sid and
                    not turn.get("subagent_id") and turn.get("status") in {"completed", "cancelled", "failed"}):
                return turn.get("usage")
        except (httpx.HTTPError, TimeoutError, ValueError):
            pass
        return None

    def close_remote(self, sid, *, before_delete=None):
        """Only an independent GET 404 clears the local cleanup receipt."""
        snapshot = self.snapshot(sid)
        if snapshot is None:
            return True
        if snapshot.get("id") != sid:
            raise ValueError("Unexpected cleanup session")
        if snapshot["status"] in {"in_progress", "requires_action"}:
            self.submit(sid, [{"type": "agent.session.input.cancel"}], digest(sid + "/cancel"))
        if before_delete and time.monotonic() + 2 < self.deadline:
            try:
                before_delete()
            except Exception:
                # A metering failure leaves its reservation intact. Remote
                # cleanup must still run, even if the local database is busy.
                pass
        try:
            self.request("DELETE", "/" + sid)
        except httpx.HTTPStatusError as error:
            if error.response.status_code != 404:
                raise
        except httpx.TransportError:
            pass
        return self.snapshot(sid) is None


class SessionEvents:
    """Observe visible final-answer deltas. Canonical Sessions resources settle all outcomes."""

    def __init__(self, api):
        self.api = api
        self.response = None
        self.reader = None
        self.message = None
        self.text = ""
        self.seen = set()

    def open(self, sid):
        try:
            request = self.api.client.build_request(
                "GET",
                SESSIONS + f"/{sid}/events",
                params={"include_obfuscation": "false"},
                headers={"Accept": "text/event-stream", "Accept-Encoding": "identity"},
                timeout=httpx.Timeout(2, connect=3),
            )
            self.response = self.api.client.send(request, stream=True)
            self.response.raise_for_status()
            if not self.response.headers.get("content-type", "").startswith("text/event-stream"):
                self.close()
                return
            self.reader = self.events()
        except httpx.HTTPError:
            self.close()

    def events(self):
        data = bytearray()
        chunks = (
            [self.response.content]
            if self.response.is_stream_consumed
            else self.response.iter_raw()
        )
        for chunk in chunks:
            data.extend(chunk)
            if len(data) > 512_000 or time.monotonic() > self.api.deadline:
                raise ValueError("Session stream bound exceeded")
            while True:
                boundary = re.search(rb"\r?\n\r?\n", data)
                if not boundary:
                    break
                frame = bytes(data[: boundary.start()])
                del data[: boundary.end()]
                parts = [
                    line[5:].lstrip() for line in frame.splitlines() if line.startswith(b"data:")
                ]
                if not parts:
                    continue
                raw = b"\n".join(parts)
                if raw == b"[DONE]":
                    return
                yield json.loads(raw)

    def pump(self, sid, tid, publish):
        """Give a ready stream a short slice, then recheck the turn and pending calls."""
        if self.reader is None:
            return False
        until = min(self.api.deadline, time.monotonic() + 0.35)
        try:
            for event in self.reader:
                kind = event["type"]
                if kind in {
                    "agent.session.requires_action",
                    "agent.session.turn.completed",
                    "agent.session.turn.failed",
                    "agent.session.turn.cancelled",
                    "agent.session.idle",
                }:
                    return True
                ident = event.get("event_id")
                if (
                    event.get("turn_id") == tid
                    and event.get("session_id") == sid
                    and isinstance(ident, str)
                    and ident not in self.seen
                ):
                    self.seen.add(ident)
                    if len(self.seen) > 2000:
                        raise ValueError("Too many output events")
                    item = event.get("item") or {}
                    if (
                        kind == "agent.session.turn.item.added"
                        and item.get("type") == "message"
                        and item.get("role") == "assistant"
                        and item.get("phase") == "final_answer"
                    ):
                        self.message = item["id"]
                    if (
                        kind == "agent.session.turn.output_text.delta"
                        and self.message
                        and event.get("item_id") == self.message
                    ):
                        self.text += event["delta"]
                        if len(self.text) > WIRE_LIMIT:
                            raise ValueError("Oversized preview")
                        publish(self.text)
                if time.monotonic() >= until:
                    return True
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            pass
        self.close()
        return False

    def close(self):
        if self.response is not None:
            self.response.close()
        self.reader = None
