"""Checks for the assistant SSE body. This module does not call a model."""

import json


EVENT_TYPES = frozenset({"tool", "preview", "delta", "done", "error"})


def parse_sse(body: str) -> list[dict]:
    events = []
    for block in body.replace("\r\n", "\n").split("\n\n"):
        data = "".join(line[5:].lstrip() for line in block.split("\n") if line.startswith("data:"))
        if not data:
            continue
        event = json.loads(data)
        if not isinstance(event, dict):
            raise ValueError("event")
        events.append(event)
    return events


def check_event(event: dict) -> None:
    kind = event.get("type")
    if kind not in EVENT_TYPES:
        raise ValueError(str(kind))
    if kind == "tool":
        if event.get("phase") not in {"started", "finished"}:
            raise ValueError("phase")
        if not isinstance(event.get("tool"), str) or not event["tool"]:
            raise ValueError("tool")
        if "arguments" in event:
            raise ValueError("arguments")
        if set(event) - {"type", "phase", "tool", "outcome", "saved"}:
            raise ValueError("extra")
        if event["phase"] == "finished":
            if not isinstance(event.get("outcome"), str):
                raise ValueError("outcome")
            if not isinstance(event.get("saved"), bool):
                raise ValueError("saved")
        return
    if kind in {"preview", "delta"}:
        if not isinstance(event.get("text"), str) or set(event) - {"type", "text"}:
            raise ValueError("text")
        return
    if kind == "done":
        reply = event.get("reply")
        if not isinstance(reply, dict) or not isinstance(reply.get("message"), str):
            raise ValueError("reply")
        if set(event) - {"type", "reply"}:
            raise ValueError("extra")
        return
    if not isinstance(event.get("code"), str) or not event["code"]:
        raise ValueError("code")
    if "status" in event and not isinstance(event["status"], int):
        raise ValueError("status")
    if set(event) - {"type", "code", "status"}:
        raise ValueError("extra")
