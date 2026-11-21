import json

import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from session_protocol_fixture import install_session_protocol


@pytest.fixture
def desk(tmp_path):
    app = create_app(tmp_path, password="fixture", scheduler=False)
    r = app.state.runtime
    svc = install_session_protocol(r)
    client = TestClient(app)
    assert client.post(
        "/api/session",
        json={"username": "owner", "password": "fixture"},
        headers={"X-Desk-Request": "1"},
    ).is_success
    return r, client, svc


def send(client, key, message="Tell me about this subject", chat=None, stream=False):
    fields = {"message": message, **({"conversation_id": chat} if chat else {})}
    return client.post(
        "/api/assistant/messages" + ("/stream" if stream else ""),
        json=fields,
        headers={"X-Desk-Request": "1", "X-Operation-Id": key},
    )


def test_delivery_uses_the_same_session_and_preserves_the_visible_answer(desk):
    from desk.alice_delivery import DELIVERIES, read_delivery

    _, client, api = desk
    text = '好消息！你说的 "yes" 我记得。\n🎉'
    api.final = json.dumps({"delivery": "celebrate", "message": text})
    answer = send(client, "good-news").json()
    assert answer["message"] == text and answer["delivery"] == "celebrate"
    assert len(api.creations) == 1 and not api.functions
    schema = api.creations[0]["agent"]["text"]["format"]
    assert schema["type"] == "json_schema"
    assert schema["schema"]["properties"]["delivery"]["enum"] == list(DELIVERIES)
    for end in range(len(api.final) + 1):
        partial = read_delivery(api.final[:end], complete=False)["message"]
        assert text.startswith(partial)
    assert read_delivery('{"delivery":"something-unknown","message":"OK"}',complete=True)=={"message":"OK"}
    assert read_delivery('{"price":1}', complete=True)=={"message":'{"price":1}'}
    assert read_delivery('{"message":"literal JSON"}', complete=True)=={"message":'{"message":"literal JSON"}'}


@pytest.mark.parametrize("tone", ["relieved", "bashful", "apologetic"])
def test_new_delivery_reaches_ordinary_reply_in_one_session(desk, tone):
    _, client, service = desk
    service.final = json.dumps({"delivery": tone, "message": "收到。"})
    answer = send(client, f"ordinary-{tone}").json()
    assert (answer["delivery"], answer["message"]) == (tone, "收到。")
    assert len(service.creations) == 1 and not service.functions
    field = service.creations[0]["agent"]["text"]["format"]["schema"]["properties"]["delivery"]
    assert tone in field["enum"]


def test_chat_resumes_verified_remote_turn_and_a_cached_request_never_resubmits(desk):
    r, c, api = desk
    first = send(c, "first").json()
    assert first["message"] == api.final
    again = send(
        c, "second", "Can you explain that in other words?", first["conversation_id"]
    ).json()
    assert again["conversation_id"] == first["conversation_id"] and again["message"] == api.final
    assert len(api.creations) == len(api.followups) == 1
    created = api.creations[0]
    assert created["environment"] == {"type": "none"}
    assert (
        created["agent"]["multi_agent"] == {"enabled": False}
        and created["spend_control"]["limit"] > 0
    )
    assert all(t["type"] == "function" for t in created["agent"]["tools"])
    assert not {"stop_physical_outputs", "device_feedback_draft", "shell", "computer_use"} & {
        t["name"] for t in created["agent"]["tools"]
    }
    assert json.loads(api.followups[0][0]["input"][0]["content"][0]["text"])["turns"] == []
    send(c, "second", "Can you explain that in other words?", first["conversation_id"])
    assert len(api.followups) == 1
    assert r.text_ai.conversation_calls_today() == 2


def test_read_call_is_bound_to_pending_turn_and_lost_ack_reuses_result(desk):
    r, c, api = desk
    api.next_calls = [("owner_clock", {})]
    api.lose_result_once = True
    output = send(c, "read", stream=True).text
    assert '"type":"tool"' in output and api.final in output
    first, second = api.functions
    assert (
        first == second
        and first[0][0]["turn_id"] == "turn_1"
        and first[0][0]["call_id"] == "call_0"
    )
    assert (
        first[0][0]["success"] and json.loads(first[0][0]["output"])["timezone"] == "Asia/Hong_Kong"
    )
    assert len([v for v in r.assistant.audit.listing(20) if v["tool"] == "owner_clock"]) == 1


def test_lost_draft_ack_keeps_one_local_review_and_no_task_write(desk):
    r, c, api = desk
    api.next_calls = [("task_create_draft", {"title": "Check the museum hours"})]
    api.drop_after_result = True
    first = send(c, "draft").json()
    assert first["kind"] == "draft" and not first["saved"]
    again = send(c, "draft").json()
    assert again["proposal"]["id"] == first["proposal"]["id"]
    assert all("Check the museum hours" not in json.dumps(events) for events, _ in api.functions)
    assert (
        len(api.creations) == 1
        and len(r.assistant.proposals()) == 1
        and not r.tasks.listing()["tasks"]
    )
    assert not api.sessions


def test_parallel_writes_are_never_selected_by_list_order(desk):
    r, c, api = desk
    api.next_calls = [
        ("task_create_draft", {"title": "One"}),
        ("task_create_draft", {"title": "Two"}),
    ]
    assert send(c, "ambiguous").json()["kind"] == "clarify"
    assert not r.assistant.proposals() and not api.functions and not api.sessions


def test_uncertain_create_after_restart_is_found_by_metadata_and_never_replayed(desk):
    r, c, api = desk
    api.lose_create = True
    api.metadata_delay = True
    first = send(c, "lost").json()
    assert first["kind"] == "clarify"
    assert send(c, "lost").json()["message"] == first["message"] and len(api.creations) == 1
    from desk.text_sessions import TextSessions

    r.text_ai.sessions = TextSessions(r.text_ai)
    r.text_ai.sessions.reap()
    assert not api.sessions
    with r.store.connection() as db:
        assert db.execute("SELECT count(*) FROM text_provider_sessions").fetchone()[0] == 0


def test_logout_while_waiting_fences_required_action(desk):
    r, c, api = desk
    api.next_calls = [("task_create_draft", {"title": "Must not exist"})]

    def logout():
        r.store.logout(c.cookies.get("desk_companion_session"))
        api.on_check = None

    api.on_check = logout
    assert send(c, "revoked").status_code == 403
    assert not r.assistant.proposals() and not api.functions and not api.sessions


def test_forgetting_chat_deletes_owned_session_on_maintenance(desk):
    r, c, api = desk
    chat = send(c, "one").json()["conversation_id"]
    r.voice.conversations.forget(
        {"kind": "owner", "session": c.cookies.get("desk_companion_session")}, chat
    )
    r.text_ai.sessions.reap()
    assert not api.sessions
    assert send(c, "stale", chat=chat).status_code == 404


def test_lost_create_and_followup_ack_recover_the_same_chat_without_new_input(desk):
    _, client, api = desk
    api.lose_create = True
    first = send(client, "uncertain-create").json()
    assert first["message"] == api.final
    api.lose_input = True
    second = send(
        client, "uncertain-follow", "Please explain that", first["conversation_id"]
    ).json()
    assert second["message"] == api.final and len(api.followups) == len(api.creations) == 1


def test_owner_login_invalidation_rotate_and_private_mode_excludes_context(desk):
    r, client, api = desk
    r.memory.create("Private fixture violet owl", "sensitive")
    first = send(client, "with-fact", "What comes next for this example?").json()
    assert "Private fixture" in json.dumps(api.creations[0])
    from desk.schemas import SettingsInput

    r.store.update_settings(
        SettingsInput(expected_version=1, timezone="Asia/Hong_Kong", hide_private=True),
        "hide-facts",
    )
    r.text_ai.sessions.reap()
    assert not api.sessions
    assert (
        send(client, "hidden", "Explain a rainbow", first["conversation_id"]).json()["message"]
        == api.final
    )
    body = api.creations[-1]
    assert not body["agent"]["tools"] and "Private fixture" not in json.dumps(body)
    assert json.loads(body["input"][0]["content"][0]["text"]) == {
        "language": "en",
        "user_message": "Explain a rainbow",
    }
    assert not api.sessions


def test_read_only_function_followup_reuses_session_but_changed_owner_cannot(desk):
    r, c, api = desk
    api.next_calls = [("owner_clock", {})]
    first = send(c, "clock", "What time is it here?").json()
    api.next_calls = []
    assert (
        send(c, "next", "And which timezone?", first["conversation_id"]).json()["message"]
        == api.final
    )
    assert len(api.creations) == 1 and len(api.followups) == 1
    other = TestClient(c.app)
    assert other.post(
        "/api/session",
        json={"username": "owner", "password": "fixture"},
        headers={"X-Desk-Request": "1"},
    ).is_success
    assert send(other, "wrong-login", chat=first["conversation_id"]).status_code == 404
    r.store.logout(c.cookies.get("desk_companion_session"))
    r.text_ai.sessions.reap()
    assert not api.sessions


def test_live_delta_only_from_verified_final_phase_and_turn(desk):
    _, client, api = desk
    sid, tid = "sess_sample1", "turn_1"

    def event(kind, i, **fields):
        return {
            "type": "agent.session.turn." + kind,
            "session_id": sid,
            "turn_id": tid,
            "event_id": "e" + str(i),
            **fields,
        }

    def message(phase):
        return {"id": phase, "phase": phase, "role": "assistant", "type": "message"}

    def dt(i, m, text):
        return event("output_text.delta", i, item_id=m, delta=text)

    events = [
        event("item.added", 1, item=message("commentary")),
        dt(2, "commentary", "untrusted commentary"),
        event("item.added", 3, item=message("final_answer")),
        dt(4, "final_answer", "A scoped"),
        dt(4, "final_answer", "DUPLICATE"),
        {**dt(5, "final_answer", "WRONG-TURN"), "turn_id": "previous"},
        event("completed", 6),
    ]
    api.pending_polls = 1
    api.stream_body = b"".join(b"data: " + json.dumps(e).encode() + b"\r\n\r\n" for e in events)
    output = send(client, "stream-actual", stream=True).text
    assert '"text":"A scoped"' in output and api.final in output
    assert not any(t in output for t in ["DUPLICATE", "WRONG-TURN", "untrusted commentary"])


def test_nonadvertised_function_cannot_execute(desk):
    r, c, api = desk
    api.next_calls = [("device_feedback_draft", {"kind": "arm", "preset": "rest"})]
    assert send(c, "not-offered").json()["kind"] == "clarify"
    assert not api.functions and not r.assistant.proposals()


def test_session_budget_and_refusal_do_not_fall_back_to_responses(desk, monkeypatch):
    r, c, api = desk
    monkeypatch.setenv("DESK_TEXT_DAILY_CAP", "1")
    assert send(c, "one").json()["message"] == api.final
    answer = send(c, "two").json()
    assert "daily limit" in answer["message"] and len(api.creations) == 1


def test_provider_expiry_before_followup_rehydrates_from_local_chat_once(desk):
    _, client, api = desk
    first = send(client, "plain", "Use the word amber in our example").json()
    api.sessions.clear()
    follow = send(client, "again", "What was the word?", first["conversation_id"]).json()
    assert follow["message"] == api.final and len(api.creations) == 2 and not api.followups
    assert api.creations[0]["metadata"] != api.creations[1]["metadata"]
    context = json.loads(api.creations[1]["input"][0]["content"][0]["text"])
    assert any("amber" in t["body"] for t in context["turns"])


def test_private_function_data_is_closed_after_use_and_a_wrong_turn_cannot_execute(desk):
    r, client, api = desk
    api.next_calls = [("task_query", {})]
    assert send(client, "private-read").json()["message"] == api.final and not api.sessions
    api.next_calls = [("task_create_draft", {"title": "Wrong turn"})]

    def wrong_turn(request):
        response = api(request)
        if (
            request.method == "GET"
            and request.url.path.endswith("sess_sample2")
            and response.status_code == 200
        ):
            body = response.json()
            if body["required_actions"]:
                body["required_actions"][0]["turn_id"] = "turn_another"
                return httpx.Response(200, json=body)
        return response

    import httpx

    r.text_ai.transport = httpx.MockTransport(wrong_turn)
    assert send(client, "wrong-turn").json()["kind"] == "clarify"
    assert not r.assistant.proposals() and not api.sessions


def test_unknown_deletion_is_retried_without_starting_work_or_dropping_metadata(desk):
    import httpx

    r, client, api = desk
    blocked = [True]

    def handle(req):
        if req.method == "DELETE" and blocked[0]:
            return httpx.Response(409)
        return api(req)

    r.text_ai.transport = httpx.MockTransport(handle)
    api.next_calls = [("task_query", {})]
    assert send(client, "cleanup").json()["message"] == api.final
    with r.store.connection() as db:
        assert db.execute("SELECT state FROM text_provider_sessions").fetchone()[0] == "closing"
    blocked[0] = False
    r.text_ai.sessions.reap()
    assert not api.sessions and len(api.creations) == len(api.functions) == 1


@pytest.mark.parametrize("variant", ["failed", "cancelled", "other-turn", "historical-call"])
def test_terminal_authority_comes_from_the_current_root_turn(desk, variant):
    import httpx

    r, client, api = desk

    def transport(req):
        res = api(req)
        if req.url.path.endswith("/turns") and variant in {"failed", "cancelled"}:
            payload = res.json()
            payload["data"][0]["status"] = variant
            return httpx.Response(200, json=payload)
        if req.url.path.endswith("/items"):
            payload = res.json()
            if variant == "other-turn":
                payload["data"][0]["turn_id"] = "turn_wrong"
            payload["data"].append(
                {
                    "type": "function_call",
                    "turn_id": "turn_1",
                    "name": "task_create_draft",
                    "arguments": {"title": "History is not a request"},
                }
            )
            return httpx.Response(200, json=payload)
        return res

    r.text_ai.transport = httpx.MockTransport(transport)
    result = send(client, "terminal").json()
    assert result["kind"] == ("reply" if variant == "historical-call" else "clarify")
    assert not r.assistant.proposals() and not api.functions


def test_real_unknown_spend_parameter_fails_closed_without_unlimited_replay(desk):
    import httpx

    runtime, client, _ = desk
    dispatched = []

    class ChunkedError(httpx.SyncByteStream):
        def __iter__(self):
            yield b'{"error":{"type":"invalid_request_error","code":"unknown_parameter",'
            yield b'"param":"spend_control","message":"Unknown parameter: spend_control"}}'

    def reject(request):
        dispatched.append((request.method, json.loads(request.content).get("spend_control")))
        return httpx.Response(400, stream=ChunkedError())

    runtime.text_ai.transport = httpx.MockTransport(reject)
    first = send(client, "unsupported-cap").json()
    second = send(client, "unsupported-cap").json()
    assert first["error"] == second["error"] == "TEXT_SESSION_BUDGET_UNSUPPORTED"
    assert dispatched == [("POST", {"limit": 25})]
    with runtime.store.connection() as db:
        assert db.execute("SELECT count(*) FROM text_provider_sessions").fetchone()[0] == 0


def test_explicit_local_budget_denial_precedes_creation_and_cleanup_ownership(desk):
    import httpx
    from desk.store import DomainError
    from desk.text_sessions import TextSessions

    runtime, client, _ = desk
    calls = []

    class Denied(httpx.BaseTransport):
        def require_session_budget(self, cents):
            calls.append(cents)
            raise DomainError("TRIAL_CLOSED", 409)

        def handle_request(self, request):
            pytest.fail("No remote session should be created after budget denial")

    transport = Denied()
    with pytest.raises(ValueError, match="installed transport"):
        TextSessions(runtime.text_ai, local_budget_transport=transport)
    runtime.text_ai.transport = transport
    runtime.text_ai.sessions = TextSessions(runtime.text_ai, local_budget_transport=transport)
    assert send(client, "closed-local-budget").status_code == 409
    assert calls == [25]
    with runtime.store.connection() as db:
        assert db.execute("SELECT count(*) FROM text_provider_sessions").fetchone()[0] == 0
