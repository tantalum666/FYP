"""Ordinary OpenAI chat. The hosted Sessions harness reasons; the desk answers its Functions."""

import time
from dataclasses import dataclass

import httpx

from .calendar import iso
from . import alice_delivery
from .capabilities import CAPABILITIES
from .context_budget import fit_context
from .conversation import memory_context
from .openai_transport import numeric_usage
from .openai_spend import TEXT_STAGE, token_estimate
from .openai_sessions import SESSION_ID, SessionAPI, SessionEvents, digest
from .store import DomainError, encode
from .text_session_store import TextSessionStore
from .tool_policy import (
    ends_text_turn,
    execute_tool,
    outcome_message,
    owner_message,
    text_effect_reply,
)


SESSION_SPEND_LIMIT_CENTS = 25


def interrupted(language):
    return {
        "mode": "ai",
        "kind": "clarify",
        "saved": False,
        "message": "这次对话中断了。请先查看已有结果，再决定是否重试。"
        if language == "zh"
        else "This conversation was interrupted. Check the existing result before trying again.",
    }


class TextSessions:
    poll_seconds = 0.4
    turn_seconds = 45

    def __init__(self, assistant, *, local_budget_transport=None):
        # A separately authorized evaluation can supply its own enforcing transport.
        # Ordinary user requests cannot alter the provider budget or select this mode.
        if local_budget_transport is not None and local_budget_transport is not assistant.transport:
            raise ValueError("Local budget must belong to the installed transport")
        self.local_budget_transport = local_budget_transport
        self.assistant = assistant
        self.runtime = assistant.runtime
        self.store = assistant.store
        self.sessions = TextSessionStore(self.store)
        self.stopping = False

    def creation_budget(self, usage_id):
        if self.runtime.openai_spend.path:
            self.runtime.openai_spend.active(usage_id)
            return {}
        if self.local_budget_transport is None:
            return {"spend_control": {"limit": SESSION_SPEND_LIMIT_CENTS}}
        if self.local_budget_transport is not self.assistant.transport:
            raise DomainError("TEXT_SESSION_BUDGET_CHANGED", 409)
        self.local_budget_transport.require_session_budget(SESSION_SPEND_LIMIT_CENTS)
        return {}

    def destination(self):
        c = self.assistant.config
        return digest(encode([c.provider, c.endpoint, digest(c.api_key)]))

    def authority(self, principal, chat, allow_memory):
        if (
            self.stopping
            or self.assistant.config.provider != "openai"
            or not self.assistant.config.valid()
        ):
            raise DomainError("TEXT_AI_UNAVAILABLE", 503)
        r = self.runtime
        with self.store.connection() as db:
            settings = self.store.settings(db)
            if principal:
                if principal["kind"] == "owner":
                    if not self.store.session_valid(principal.get("session")):
                        raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
                elif not db.execute(
                    "SELECT 1 FROM trusted_clients WHERE id=? AND kind=? AND revoked=0",
                    (principal["id"], principal["kind"]),
                ).fetchone():
                    raise DomainError("AUTH_REQUIRED", 401)
        revision = memory_context(r, allow_memory)[0]
        if chat:
            chats = r.voice.conversations
            with chats.lock:
                if (
                    chats.entries.get(chat.id) is not chat
                    or chats.clock() - chat.touched >= 1800
                    or chat.revision != revision
                    or chat.owner != chats.owner(principal)
                ):
                    raise DomainError("CONVERSATION_SCOPE_CHANGED", 409)
        return self.policy_stamp(revision), settings["hide_private"]

    def policy_stamp(self, revision):
        r = self.runtime
        accounts = [
            (a["connected"], a["version"])
            for a in (
                auth.account()
                for auth in [r.outbound_mail.auth, r.google, *r.microsoft.auth.values()]
            )
        ]
        return digest(
            encode(
                [
                    r.personal_context.revision(),
                    revision,
                    accounts,
                    r.data.preferences()["version"],
                    self.destination(),
                    self.assistant.config.model,
                ]
            )
        )

    def reap(self):
        if self.assistant.config.provider != "openai" or not self.assistant.config.valid():
            return
        destination = self.destination()
        if not self.sessions.has_resources(destination):
            return
        chats = self.runtime.voice.conversations
        with self.store.connection() as db:
            owners = {
                row[0]
                for row in db.execute(
                    "SELECT token_hash FROM sessions WHERE expires>?", (iso(self.store.clock()),)
                )
            }
        with chats.lock:
            chats.prune()
            live_chats = {chat.id for chat in chats.entries.values() if chat.owner in owners}
        record = self.sessions.due(
            destination, live_chats, self.policy_stamp(memory_context(self.runtime, True)[0])
        )
        if not record:
            return
        api = SessionAPI(
            self.assistant.config, self.assistant.transport, deadline=time.monotonic() + 8
        )
        try:
            sid = record["sid"]
            if not sid:
                found = api.locate(record["marker"])
                if not found:
                    return
                sid = found["id"]
                self.sessions.identified(record["marker"], sid)
            if api.close_remote(sid):
                self.sessions.forget(record["marker"])
        finally:
            api.client.close()

    def shutdown(self):
        self.stopping = True
        self.sessions.retire_idle()

    def run(
        self,
        *,
        payload,
        key,
        request_hash,
        principal,
        chat,
        system,
        context,
        allow_memory,
        on_event,
        authority,
    ):
        def check():
            if self.authority(principal, chat, allow_memory) != authority:
                raise DomainError("PROVIDER_CONTEXT_CHANGED", 409)

        check()
        tools = context.pop("tools")
        names = {t["name"] for t in tools}
        config = self.assistant.config
        specs = [{"type": "function", **tool} for tool in tools]
        system += alice_delivery.INSTRUCTIONS
        # Rotate remote history when an already-projected source or a controlling setting changes.
        scope = {k: v for k, v in context.items() if k not in {"now", "turns", "user_message"}}
        permission_version = self.runtime.permissions.snapshot()["version"]
        binding = digest(encode([authority, permission_version, system, specs, scope]))
        fallback = interrupted(payload.language)
        api = SessionAPI(
            config, self.assistant.transport, deadline=time.monotonic() + self.turn_seconds
        )
        observer = SessionEvents(api)
        record = None
        sid = turn_id = usage_id = None
        keep = False
        creating = False
        responder = TextFunctions(
            self, payload, key, names, on_event, allow_memory, permission_version
        )
        try:
            record = self.sessions.claim(
                key, request_hash, fallback, self.destination(), chat, binding, authority[0]
            )
            sid = record["sid"]
            # A local denial before creation leaves no remote resource to locate.

            message = {"role": "user", "content": [{"type": "input_text", "text": encode(context)}]}
            check()
            if sid:
                snapshot = api.snapshot(sid)
                if snapshot is None:
                    # No new input was sent and the previous resource is definitively gone.
                    record = self.sessions.replace_missing(record["marker"], key)
                    sid = None
            responder.budget_scope = record["marker"]
            usage_id = self.assistant._reserve_usage(
                "conversation",
                reservation=("session_input", TEXT_STAGE, 65),
                scope=responder.budget_scope,
            )
            if sid:
                last = api.latest_turn(sid)
                if (
                    snapshot.get("id") != sid
                    or snapshot.get("status") != "idle"
                    or not last
                    or last["id"] != record["last_turn"]
                ):
                    raise ValueError("Remote chat is not at its acknowledged turn")
                # The hosted conversation contains its previous exchange. Keep any newer local/voice exchanges.
                items = chat.items
                last_index = max(
                    i
                    for i, v in enumerate(items)
                    if v.get("operation_id") == record["last_operation"]
                )
                extra = items[last_index + 1 :]
                context["turns"] = [
                    {"role": v["role"], "body": v["text"][:500]} for v in reversed(extra[-16:])
                ]
                message["content"][0]["text"] = encode(context)
                check()
                if on_event:
                    observer.open(sid)
                check()
                try:
                    api.submit(
                        sid,
                        [{"type": "agent.session.input.message", "input": [message]}],
                        digest(key + "/input"),
                    )
                except httpx.TransportError:
                    # The provider may have accepted the input. Observe without replay.
                    pass
            else:
                controls = self.creation_budget(usage_id)
                try:
                    creating = True
                    snapshot = api.request(
                        "POST",
                        body={
                            "agent": {
                                "model": config.model,
                                "instructions": system,
                                "text": alice_delivery.TEXT_FORMAT,
                                "tools": specs,
                                "reasoning": {"effort": "low"},
                                "service_tier": "default",
                                "multi_agent": {"enabled": False},
                            },
                            "environment": {"type": "none"},
                            "input": [message],
                            "review": "none",
                            **controls,
                            "metadata": {"fyp_request": record["marker"]},
                        },
                    )
                except httpx.TransportError:
                    snapshot = api.locate(record["marker"])
                    if snapshot is None:
                        raise
                except httpx.HTTPStatusError as error:
                    if error.response.status_code in {400, 401, 403, 404, 422, 429}:
                        self.sessions.forget(record["marker"])
                    if error.response.extensions.get("desk_session_limit_rejected"):
                        return {
                            "mode": "ai",
                            "kind": "clarify",
                            "saved": False,
                            "error": "TEXT_SESSION_BUDGET_UNSUPPORTED",
                            "message": (
                                "当前 OpenAI 服务不支持配置的会话消费上限，本次会话未启动。"
                                if payload.language == "zh"
                                else "This OpenAI service does not support the configured spending limit. The session did not start."
                            ),
                        }
                    raise
                sid = snapshot["id"]
                if not isinstance(sid, str) or not SESSION_ID.fullmatch(sid):
                    raise ValueError("Invalid session ID")
                self.sessions.identified(record["marker"], sid)
                if on_event and snapshot.get("status") != "idle":
                    observer.open(sid)
            turn_id, reply = self.observe(
                api, observer, sid, record["last_turn"], check, responder, on_event, usage_id
            )
            keep = bool(
                chat and not authority[1] and responder.reusable and not responder.local_reply
            )
            return reply
        except DomainError as error:
            if error.code.startswith("OPENAI_BUDGET_") or error.code in {
                "OPENAI_DAILY_BUDGET_REACHED",
                "OPENAI_SESSION_BUDGET_REACHED",
            }:
                messages = {
                    "OPENAI_BUDGET_PERIOD_CLOSED": (
                        "本次 API 授权期已结束。",
                        "The API spending authorization has ended.",
                    ),
                    "OPENAI_BUDGET_DAY_END": (
                        "已接近香港午夜，请在新一天的授权时段重试。",
                        "This operation is too close to midnight in Hong Kong. Try again in the next authorized day.",
                    ),
                    "OPENAI_SESSION_BUDGET_REACHED": (
                        "这段对话已达到本地会话额度。",
                        "This conversation reached its local spending allowance.",
                    ),
                    "OPENAI_DAILY_BUDGET_REACHED": (
                        "这台设备今天可用的 API 额度不足。",
                        "This desk has insufficient API allowance for today.",
                    ),
                }
                pair = messages.get(
                    error.code,
                    ("本地费用检查已暂停这次请求。", "Local spending checks stopped this request."),
                )
                return responder.local_reply or {
                    "mode": "ai",
                    "kind": "clarify",
                    "error": error.code,
                    "saved": False,
                    "message": pair[0 if payload.language == "zh" else 1],
                }
            if error.code in {"TEXT_AI_CAP", "SESSION_TOOL_LIMIT"}:
                if not sid and record:
                    self.sessions.forget(record["marker"])
                kind = "cap" if error.code == "TEXT_AI_CAP" else "steps"
                return responder.local_reply or {
                    "mode": "ai",
                    "kind": "clarify",
                    "saved": False,
                    "message": owner_message(kind, payload.language),
                }
            raise
        except (
            httpx.HTTPError,
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
            IndexError,
            TimeoutError,
        ):
            return responder.local_reply or fallback
        finally:
            observer.close()
            api.client.close()
            if record:
                if not sid and not creating:
                    self.sessions.forget(record["marker"])
                else:
                    self.sessions.finish(record["marker"], turn_id, key, keep)
                if not keep and sid and isinstance(sid, str) and SESSION_ID.fullmatch(sid):
                    cleanup = SessionAPI(
                        config, self.assistant.transport, deadline=time.monotonic() + 5
                    )
                    try:
                        def capture_cost():
                            if self.runtime.openai_spend.path and turn_id and usage_id and not responder.final_usage_received:
                                usage = cleanup.terminal_usage(sid, turn_id)
                                if usage:
                                    self.record_usage(usage_id, usage)
                                    self.runtime.openai_spend.usage(
                                        [usage_id, *responder.budget_ids], token_estimate(usage), final=True
                                    )
                        if cleanup.close_remote(sid, before_delete=capture_cost):
                            self.sessions.forget(record["marker"])
                    except (httpx.HTTPError, ValueError, KeyError, TimeoutError):
                        pass  # The durable receipt remains for the housekeeping worker.
                    finally:
                        cleanup.client.close()

    def observe(self, api, observer, sid, previous_turn, check, responder, on_event, usage_id):
        """Drive pending application calls and observe the outcome of one submitted input."""
        turn_id = None

        def publish(text):
            if on_event and not responder.local_reply:
                check()
                visible = alice_delivery.read_delivery(text, complete=False)["message"]
                if visible and visible != responder.preview:
                    responder.preview = visible
                    on_event({"type": "preview", "text": visible})

        observation_errors = 0
        while time.monotonic() < api.deadline:
            check()
            try:
                snapshot = api.request("GET", "/" + sid)
                turn = api.latest_turn(sid)
                if snapshot.get("id") != sid or snapshot.get("status") == "failed":
                    raise ValueError("Session failed")
                if turn and turn["id"] != previous_turn:
                    if turn_id and turn_id != turn["id"]:
                        raise ValueError("Turn changed")
                    turn_id = turn["id"]
                    if self.runtime.openai_spend.path and turn["status"] not in {
                        "completed",
                        "failed",
                        "cancelled",
                    }:
                        self.runtime.openai_spend.active(usage_id)
                        self.runtime.openai_spend.usage(
                            [usage_id, *responder.budget_ids], token_estimate(turn.get("usage"))
                        )
                    if turn["status"] in {"failed", "cancelled"}:
                        raise ValueError("Turn did not complete")
                    if turn["status"] == "completed":
                        text = api.answer(sid, turn_id, complete=True)
                        check()
                        if not text:
                            raise ValueError("Missing final answer")
                        usage = turn.get("usage")
                        if usage is None and self.runtime.openai_spend.path:
                            usage = api.terminal_usage(sid, turn_id)
                        self.record_usage(usage_id, usage)
                        self.runtime.openai_spend.usage(
                            [usage_id, *responder.budget_ids],
                            token_estimate(usage),
                            final=True,
                        )
                        responder.final_usage_received = token_estimate(usage) is not None
                        if responder.local_reply:
                            return turn_id, responder.local_reply
                        answer = alice_delivery.read_delivery(text, complete=True)
                        if on_event:
                            on_event({"type": "preview", "text": answer["message"], "final": True})
                        return turn_id, {
                            "mode": "ai",
                            "kind": "reply",
                            **answer,
                            **({"plan": responder.plan} if responder.plan else {}),
                        }
                    if snapshot.get("required_actions"):
                        responder.respond(api, sid, turn_id, snapshot["required_actions"], check)
                        if responder.local_reply:
                            return turn_id, responder.local_reply
                    elif on_event and observer.reader is None and not responder.local_reply:
                        partial = api.answer(sid, turn_id, complete=False)
                        if partial:
                            publish(partial)
            except httpx.TransportError:
                # Read back the same session. Never re-create it or replay the user's input here.
                observation_errors += 1
                if observation_errors > 2:
                    raise

            if not (turn_id and observer.pump(sid, turn_id, publish)):
                time.sleep(self.poll_seconds)
        raise TimeoutError()

    def record_usage(self, usage_id, usage):
        safe = numeric_usage(usage)
        if safe:
            with self.store.connection(write=True) as db:
                db.execute("UPDATE text_ai_usage SET usage=? WHERE id=?", (encode(safe), usage_id))


@dataclass
class FunctionReceipt:
    signature: str
    event: dict
    attempts: int = 0
    accepted: bool = False


class TextFunctions:
    """Bound one original message to already-registered application functions and their receipts."""

    def __init__(self, sessions, payload, key, names, on_event, allow_memory, permission_version):
        self.sessions, self.payload, self.key = sessions, payload, key
        self.names, self.on_event, self.allow_memory = names, on_event, allow_memory
        self.budget_ids = []
        self.budget_scope = None
        self.final_usage_received = False
        self.calls = {}
        self.local_reply = None
        self.plan = None
        self.reusable = True
        self.permission_version = permission_version
        self.preview = ""

    def respond(self, api, sid, turn_id, actions, check):
        if not isinstance(actions, list) or not 1 <= len(actions) <= 3:
            raise DomainError("SESSION_TOOL_LIMIT", 409)
        for a in actions:
            if (
                a.get("type") != "function_call"
                or a.get("turn_id") != turn_id
                or a.get("name") not in self.names
                or not isinstance(a.get("arguments"), dict)
                or not isinstance(a.get("call_id"), str)
                or not 0 < len(a["call_id"]) <= 256
            ):
                raise ValueError("Unexpected required action")
        # An ambiguous parallel batch has no authority to choose among mutations.
        if len(actions) > 1 and any(CAPABILITIES[a["name"]].risk != "read" for a in actions):
            raise ValueError("Parallel action needs a single choice")
        for a in actions:
            ident = a["call_id"]
            signature = digest(encode([a["name"], a["arguments"]]))
            receipt = self.calls.get(ident)
            if receipt is None:
                if self.local_reply or len(self.calls) >= 3:
                    raise DomainError("SESSION_TOOL_LIMIT", 409)
                check()
                receipt = FunctionReceipt(signature, self.call(sid, turn_id, a))
                self.calls[ident] = receipt
            if receipt.signature != signature:
                raise ValueError("Pending function definition changed")
            if receipt.accepted:
                continue
            check()
            if receipt.attempts == 0:
                attempt = self.sessions.assistant._reserve_usage(
                    "conversation",
                    reservation=("session_function", TEXT_STAGE, 65),
                    scope=self.budget_scope,
                )
                self.budget_ids.append(attempt)
            if receipt.attempts >= 3:
                raise ValueError("Function acknowledgement is unresolved")
            receipt.attempts += 1
            check()
            api.submit(sid, [receipt.event], digest(encode([sid, turn_id, ident])))
            receipt.accepted = True

    def call(self, sid, tid, a):
        name = a["name"]
        if (
            CAPABILITIES[name].risk in {"cancel", "stop"}
            and self.sessions.runtime.permissions.snapshot()["version"] != self.permission_version
        ):
            raise DomainError("PERMISSION_CHANGED", 409)
        # Mail, private details and draft contents must not become unbounded provider history.
        if name not in {"owner_clock", "weather_query"}:
            self.reusable = False
        if self.on_event:
            self.on_event({"type": "tool", "phase": "started", "tool": name})
        arguments = a["arguments"]
        choice = getattr(self.payload,"calendar_flight_choice",None)
        if name == "sandbox_flight_quote" and choice is not None:
            # A tapped, read-only fare is fully specified by the owner's UI action.
            arguments = {**choice.model_dump(exclude_none=True), "avoid_calendar_conflicts": True}
        result = execute_tool(
            self.sessions.runtime,
            name,
            arguments,
            "text/" + digest(encode([sid, tid, a["call_id"]])),
            scope=self.key,
            allow_memory=self.allow_memory,
            language=self.payload.language,
            channel="text",
        )
        if self.on_event:
            self.on_event(
                {
                    "type": "tool",
                    "phase": "finished",
                    "tool": name,
                    "outcome": result.get("error") or "ok",
                    "saved": bool(result.get("saved")),
                }
            )
        if isinstance(result.get("plan"), dict):
            self.plan = result["plan"].get("summary")
        error = result.get("error")
        if ends_text_turn(name, result):
            message = outcome_message(error or "ok", result, self.payload.language)
            if not message:
                message = (
                    "操作结果已更新。"
                    if self.payload.language == "zh"
                    else "The action result is available."
                )
            self.local_reply = text_effect_reply(message, result, self.payload.language)
            if self.plan:
                self.local_reply["plan"] = self.plan
            with self.sessions.store.connection(write=True) as db:
                db.execute(
                    "UPDATE assistant_replies SET result=? WHERE id=?",
                    (encode(self.local_reply), self.key),
                )
        if self.local_reply:
            # Alice displays the original review card locally. Recipients, files and draft
            # bodies do not need to be copied into the provider's persistent tool transcript.
            output = {"kind": self.local_reply["kind"], "saved": bool(result.get("saved"))}
        else:
            output = fit_context({"last_tool_result": {"tool": name, "result": result}})[
                "last_tool_result"
            ]["result"]
        return {
            "type": "agent.session.input.tool_result",
            "turn_id": tid,
            "call_id": a["call_id"],
            "success": not error,
            **({"error": error} if error else {"output": encode(output)}),
        }
