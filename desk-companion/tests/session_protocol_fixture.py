"""Scripted public REST resources. This fixture never opens a network socket."""

import json

import httpx


class SessionProtocol:
    root = "/v1/agents/sessions"

    def __init__(self):
        self.sessions = {}
        self.creations = []
        self.events = []
        self.functions = []
        self.followups = []
        self.requests = []
        self.next_calls = []
        self.lose_create = False
        self.metadata_delay = False
        self.lose_input = False
        self.pending_polls = 0
        self.stream_body = b"data: [DONE]\n\n"
        self.lose_result_once = False
        self.drop_after_result = False
        self.on_check = None
        self.final = "A scoped answer from Alice."

    def __call__(self, request):
        assert (
            request.url.host == "api.openai.com" and request.headers["openai-beta"] == "agents=v1"
        )
        assert request.headers["authorization"] == "Bearer fake-only"
        path = request.url.path.removeprefix(self.root)
        method = request.method
        self.requests.append((method, path))

        def res(value):
            return httpx.Response(200, json=value)

        if path == "" and method == "POST":
            body = json.loads(request.content)
            self.creations.append(body)
            sid = f"sess_sample{len(self.creations)}"
            self.sessions[sid] = {
                "id": sid,
                "metadata": body["metadata"],
                "n": 1,
                "calls": list(self.next_calls),
            }
            if self.lose_create:
                raise httpx.ReadTimeout("lost creation", request=request)
            return res({"id": sid, "status": "in_progress"})
        if path == "" and method == "GET":
            if self.metadata_delay:
                self.metadata_delay = False
                return res({"data": [], "has_more": False})
            marker = request.url.params["metadata[fyp_request]"]
            return res(
                {
                    "data": [
                        s for s in self.sessions.values() if s["metadata"]["fyp_request"] == marker
                    ],
                    "has_more": False,
                }
            )
        sid, *rest = path.lstrip("/").split("/")
        if sid not in self.sessions:
            return httpx.Response(404)
        s = self.sessions[sid]
        tid = f"turn_{s['n']}"
        calls = s["calls"]
        if method == "DELETE":
            del self.sessions[sid]
            return res({"deleted": True})
        if rest == ["events"] and method == "GET":
            return httpx.Response(
                200, headers={"Content-Type": "text/event-stream"}, content=self.stream_body
            )
        if not rest:
            if self.on_check:
                self.on_check()
            return res(
                {
                    "id": sid,
                    "status": "requires_action" if calls else "idle",
                    "required_actions": [
                        {
                            "type": "function_call",
                            "turn_id": tid,
                            "call_id": "call_" + str(i),
                            "name": name,
                            "arguments": args,
                        }
                        for i, (name, args) in enumerate(calls)
                    ],
                }
            )
        if rest == ["turns"]:
            waiting = self.pending_polls > 0
            self.pending_polls -= int(waiting)
            return res(
                {
                    "data": [
                        {
                            "id": tid,
                            "status": "in_progress" if calls or waiting else "completed",
                            "usage": {"input_tokens": 8, "output_tokens": 5},
                        }
                    ]
                }
            )
        if rest == ["items"]:
            return res(
                {
                    "data": [
                        {
                            "type": "message",
                            "role": "assistant",
                            "phase": "final_answer",
                            "status": "completed",
                            "turn_id": tid,
                            "content": [{"type": "output_text", "text": self.final}],
                        }
                    ]
                }
            )
        assert rest == ["events"] and method == "POST"
        body = json.loads(request.content)["events"]
        self.events += body
        typ = body[0]["type"]
        if typ.endswith(".message"):
            self.followups.append((body[0], request.headers["idempotency-key"]))
            s["n"] += 1
            s["calls"] = list(self.next_calls)
            if self.lose_input:
                raise httpx.ReadTimeout("input already accepted", request=request)
        elif typ.endswith(".tool_result"):
            self.functions.append((body, request.headers["idempotency-key"]))
            if self.lose_result_once:
                self.lose_result_once = False
                raise httpx.ReadTimeout("not acknowledged", request=request)
            if self.drop_after_result:
                raise httpx.ReadTimeout("unknown", request=request)
            s["calls"] = []
        elif typ.endswith(".cancel"):
            s["calls"] = []
        else:
            raise AssertionError(typ)
        return httpx.Response(202)


def install_session_protocol(runtime):
    from desk.provider_policy import OPENAI_TEXT_ENDPOINT
    from desk.text_ai import TextConfig

    fixture = SessionProtocol()
    runtime.text_ai.config = TextConfig("openai", "gpt-6.1-sol", OPENAI_TEXT_ENDPOINT, "fake-only")
    runtime.text_ai.transport = httpx.MockTransport(fixture)
    runtime.text_ai.sessions.poll_seconds = 0
    return fixture
