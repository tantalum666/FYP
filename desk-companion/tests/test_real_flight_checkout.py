"""An actual-shaped Kiwi receipt enters an owner-confirmed, separately priced seller checkout."""

from copy import deepcopy
from datetime import UTC, datetime
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from desk.app import create_app
from desk.flight_search import recorded_quote, search_arguments
from desk.stream_contract import parse_sse
from session_protocol_fixture import install_session_protocol


DAY, BACK = "2026-11-24", "2026-12-01"
SPEC = {
    "kind": "flight",
    "provider": "kiwi",
    "origin": "HKG",
    "destination": "NRT",
    "departure": DAY,
    "return_date": BACK,
    "adults": 1,
    "checked_bag_kg": 20,
    "currency": "HKD",
}
DRAFT = {
    "title": "Tokyo return fare",
    "goal": "HKG to NRT return with a checked bag",
    "start_url": "https://www.kiwi.com/",
    "quote_request": SPEC,
}
HEAD = {"X-Desk-Request": "1"}
BUY = "帮我购买这个机票"
OUT = [
    ("HKG", "TPE", "BR852", DAY + "T11:20:00", DAY + "T13:05:00"),
    ("TPE", "NRT", "BR196", DAY + "T15:30:00", DAY + "T19:20:00"),
]
IN = [
    ("NRT", "TPE", "BR197", BACK + "T10:00:00", BACK + "T13:40:00"),
    ("TPE", "HKG", "BR851", BACK + "T15:00:00", BACK + "T17:00:00"),
]


def sector(legs):
    return {
        "route": [legs[0][0], *[i[1] for i in legs]],
        "departureTime": legs[0][3],
        "arrivalTime": legs[-1][4],
        "segments": [
            {
                "from": a,
                "to": b,
                "flightNumber": n,
                "carrier": "BR",
                "departureTime": d,
                "arrivalTime": r,
            }
            for a, b, n, d, r in legs
        ],
    }


class KiwiSession:
    def __init__(self, *args, **kwargs):
        pass

    async def run(self, intent, checkpoint, on_session, **kwargs):
        checkpoint()
        on_session("synthetic-kiwi-job")
        item = {
            "tripType": "return",
            "price": 3389.59,
            "bookingUrl": "https://www.kiwi.com/u/public-test-only",
            "outbound": sector(OUT),
            "inbound": sector(IN),
            "baggage": {"checkedBag": 1.0},
        }
        output = {
            "currency": "HKD",
            "passengers": {"adults": 1, "children": 0, "infants": 0},
            "itineraries": [item],
        }
        call = {
            "type": "mcp_call",
            "name": "search-flight",
            "server_label": "kiwi",
            "status": "completed",
            "error": None,
            "turn_id": "turn-1",
            "arguments": search_arguments(intent["quote_request"]),
            "output": {"structuredContent": output},
        }
        report = recorded_quote([call], intent, "turn-1")
        return {
            "report": json.dumps(report),
            "activity_count": 1,
            "usage": {"input_tokens": 6, "output_tokens": 5},
            "session_deleted": True,
            "deletion_readback": True,
            "stop_code": None,
            "turn_completed": True,
            "account_access_authorized": False,
            "stream_reconnections": 0,
        }


def legs(rows):
    return [
        dict(origin=a, destination=b, flight=n, carrier="BR", departs=d, arrives=r)
        for a, b, n, d, r in rows
    ]


class Supplier:
    def __init__(self):
        self.offer = {
            "account_version": "account-version",
            "search_id": "live-search",
            "offer_id": "live-offer",
            "currency": "HKD",
            "total_minor": 350000,
            "fare_minor": 330000,
            "passenger_count": 1,
            "checked_bags": 1,
            "checked_bag_kg": 20,
            "ready": True,
            "reason": None,
            "outbound": legs(OUT),
            "inbound": legs(IN),
            "booking_url": "https://letsfg.co/",
        }
        self.searches = []
        self.rereads = []
        self.submitted = []
        self.reads = []
        self.bank = False

    def search(self, query, *, principal, search_id=None):
        self.searches.append(query.model_dump())
        return {"state": "offers", "search_id": "live-search", "offers": [deepcopy(self.offer)]}

    def reprice(self, query, sid, oid, *, principal):
        self.rereads.append((sid, oid))
        return {"state": "offers", "search_id": sid, "offers": [deepcopy(self.offer)]}

    def submit(self, approval, passengers, email, *, principal):
        self.submitted.append(approval.approval_id)
        assert (
            approval.offer["total_minor"] == self.offer["total_minor"]
            and email == "traveller@example.invalid"
        )
        return {
            "state": "bank_approval" if self.bank else "held",
            "booking_ref": approval.approval_id,
            "held_minor": approval.offer["total_minor"],
            "currency": "HKD",
            **({"action_url": "https://letsfg.co/connect"} if self.bank else {}),
        }

    def status(self, handle, offer, *, principal):
        assert handle == self.submitted[0]
        self.reads.append(handle)
        return {
            "state": "completed",
            "booking_ref": handle,
            "pnr": "TEST7A",
            "currency": "HKD",
            "charged_minor": self.offer["total_minor"],
        }


@pytest.fixture
def desk(tmp_path):
    def app():
        a = create_app(
            tmp_path,
            clock=lambda: datetime(2026, 11, 23, 7, tzinfo=UTC),
            password="fixture",
            scheduler=False,
        )
        r = a.state.runtime
        r.jobs.managed_browser.enabled = True
        r.jobs.managed_browser.client_factory = KiwiSession
        session = install_session_protocol(r)
        c = TestClient(a, base_url="https://testserver", headers=HEAD)
        return a, r, c, session

    a, r, c, session = app()
    c.post("/api/session", json={"username": "owner", "password": "fixture"}).raise_for_status()
    source = Supplier()
    account = {"connected": False, "version": "account-version"}
    r.letsfg_auth = SimpleNamespace(account=lambda: account)
    r.live_flight_provider = source
    return SimpleNamespace(
        app=a, r=r, c=c, session=session, source=source, account=account, boot=app
    )


def ask(c, key, words, chat=None):
    res = c.post(
        "/api/assistant/messages/stream",
        headers={"X-Operation-Id": key},
        json={"message": words, "language": "zh", "conversation_id": chat},
    )
    res.raise_for_status()
    last = parse_sse(res.text)[-1]
    assert last["type"] == "done", last
    return last["reply"]


def research(d, *, finish=True):
    d.session.next_calls = [("browser_research_draft", DRAFT)]
    opening = ask(d.c, "open", "查 11 月 24 日香港往返成田，12 月 1 日回来，一人20公斤托运。")
    prop = opening["proposal"]["id"]
    chat = opening["conversation_id"]
    decision = d.c.post(
        f"/api/assistant/proposals/{prop}/decisions",
        headers={"X-Operation-Id": "share-trip"},
        json={"action": "confirm", "share_itinerary": True},
    )
    decision.raise_for_status()
    job = decision.json()["job"]["id"]
    if finish:
        d.r.jobs.run_one()
        assert d.r.jobs.detail(job)["state"] == "succeeded", d.r.jobs.detail(job)
    return chat, prop, job


def action(d, row, chat, which, number=None):
    result = d.c.post(
        f"/api/assistant/flight-checkouts/{row['id']}/actions",
        json={
            "conversation_id": chat,
            "version": row["version"],
            "action": which,
            "number": number,
        },
    )
    result.raise_for_status()
    return result.json()


def payment(row, chat):
    return {
        "conversation_id": chat,
        "version": row["version"],
        "amount_minor": row["choices"][row["selected"] - 1]["total_minor"],
        "currency": "HKD",
        "confirm_purchase": True,
        "contact_email": "traveller@example.invalid",
        "passengers": [
            {
                "given_name": "Synthetic",
                "family_name": "Passenger",
                "born_on": "1992-01-02",
                "gender": "f",
                "nationality": "HK",
                "phone_number": "+85255550123",
                "phone_country": "HK",
                "address_line1": "Fictional training address",
                "address_city": "Test City",
                "address_postal": "00000",
                "address_country": "HK",
            }
        ],
    }


def test_real_followup_reopens_original_roundtrip_and_waits_for_exact_approval(desk):
    d = desk
    chat, _, _ = research(d, finish=False)
    waiting = ask(d.c, "buy", BUY, chat)["live_flight_checkout"]
    assert waiting["state"] == "waiting_source"
    d.r.jobs.run_one()
    view = d.c.get(
        f"/api/assistant/flight-checkouts/{waiting['id']}", params={"conversation_id": chat}
    ).json()
    assert (
        view["source"]["listed_minor"] == 338959
        and view["source"]["bags"] == 1
        and view["source"]["bag_kg"] is None
    )
    assert view["source"]["request"] == SPEC and [
        x["flight"] for x in view["source"]["outbound"]
    ] == ["BR852", "BR196"]
    assert not view["connected"] and not d.source.searches
    d.account["connected"] = True
    offers = action(d, view, chat, "search")
    q = d.source.searches[0]
    assert (
        q["origin"],
        q["destination"],
        q["departure"],
        q["return_date"],
        q["checked_bags"],
        q["checked_bag_kg"],
        q["currency"],
    ) == ("HKG", "NRT", DAY, BACK, 1, 20, "HKD")
    assert q["outbound_flights"] == ["BR852", "BR196"] and q["inbound_flights"] == [
        "BR197",
        "BR851",
    ]
    review = action(d, offers, chat, "select", 1)
    assert review["state"] == "review" and not d.source.submitted
    url = f"/api/assistant/flight-checkouts/{review['id']}/confirm"
    old = payment(review, chat)
    d.source.offer["total_minor"] = 353200
    refreshed = d.c.post(url, json=old).json()
    assert (
        refreshed["state"] == "review"
        and refreshed["reason"] == "terms_changed"
        and not d.source.submitted
    )
    assert d.c.post(url, json=old).status_code == 409
    body = payment(refreshed, chat)
    d.source.bank = True
    held = d.c.post(url, json=body).json()
    assert held["state"] == "bank_approval" and held["receipt"].get("pnr") is None
    done = action(d, held, chat, "status")
    assert (
        done["state"] == "completed"
        and done["receipt"]["charged_minor"] == 353200
        and done["receipt"]["pnr"] == "TEST7A"
    )
    assert (
        d.c.post(url, json=body).json()["receipt"] == done["receipt"]
        and len(d.source.submitted) == len(d.source.reads) == 1
    )
    with d.r.store.connection() as db:
        retained = "".join(
            row[0] for row in db.execute("select data from live_flight_checkouts")
        ) + "".join(row[0] for row in db.execute("select result from assistant_replies"))
    assert (
        "Fictional training address" not in retained and "traveller@example.invalid" not in retained
    )


@pytest.mark.parametrize("change", ["checked_bag_kg", "return", "airport", "other_flight", "time"])
def test_missing_bag_or_wrong_service_cannot_be_paid(desk, change):
    d = desk
    chat, _, _ = research(d)
    d.account["connected"] = True
    base = ask(d.c, "buy", BUY, chat)["live_flight_checkout"]
    s = d.source.offer
    if change == "checked_bag_kg":
        s["checked_bag_kg"] = None
    elif change == "return":
        s["inbound"] = []
    elif change == "airport":
        s["outbound"][-1]["destination"] = "HND"
    elif change == "time":
        s["outbound"][0]["departs"] = DAY + "T11:25:00"
    else:
        s["outbound"][0]["flight"] = "BR999"
    found = action(d, base, chat, "search")
    if change == "checked_bag_kg":
        assert not found["choices"][0]["payable"]
        blocked = action(d, found, chat, "select", 1)
        assert blocked["state"] == "seller_only"
    else:
        assert found["state"] == "seller_only" and not found["choices"]
    assert not d.source.submitted


def test_legacy_voice_job_requires_original_owner_selection_then_survives_restart(desk):
    d = desk

    class OlderKiwiReceipt(KiwiSession):
        async def run(self, *args, **kwargs):
            result = await super().run(*args, **kwargs)
            report = json.loads(result["report"])
            report["supplier"].pop("outbound")
            report["supplier"].pop("inbound")
            result["report"] = json.dumps(report)
            return result

    d.r.jobs.managed_browser.client_factory = OlderKiwiReceipt
    chat, prop, job = research(d)
    with d.r.store.connection(write=True) as db:
        db.execute("delete from live_flight_checkouts")
        db.execute("delete from assistant_replies")
    a, r, c, _ = d.boot()
    c.cookies.update(d.c.cookies)
    offer = ask(c, "legacy", BUY, chat)
    assert offer["live_flight_checkout"]["state"] == "choose_source"
    replacement = offer["conversation_id"]
    assert (
        replacement != chat and offer["live_flight_checkout"]["sources"][0]["proposal_id"] == prop
    )
    other = TestClient(a, base_url="https://testserver", headers=HEAD)
    other.post("/api/session", json={"username": "owner", "password": "fixture"}).raise_for_status()
    assert (
        other.post("/api/assistant/flight-checkouts/source", json={"job_id": job}).status_code
        == 404
    )
    confirmed = c.post(
        "/api/assistant/flight-checkouts/source",
        json={"conversation_id": replacement, "job_id": job},
    )
    confirmed.raise_for_status()
    row = confirmed.json()["live_flight_checkout"]
    assert row["source"]["request"]["return_date"] == BACK
    assert row["source"]["outbound"] == [
        {"flight": "BR852", "departs": DAY + "T11:20:00"},
        {"flight": "BR196", "arrives": DAY + "T19:20:00"},
    ]
    assert (
        row["source"]["inbound"] == []
    )  # Legacy receipt has the return date but no return designator.
    _, _, c2, _ = d.boot()
    c2.cookies.update(c.cookies)
    again = ask(c2, "later", BUY, replacement)
    assert (
        again["conversation_id"] == replacement and again["live_flight_checkout"]["id"] == row["id"]
    )
    assert (
        other.get(
            "/api/assistant/flight-checkouts/" + row["id"], params={"conversation_id": replacement}
        ).status_code
        == 404
    )
    c2.delete("/api/voice/conversations/" + replacement).raise_for_status()
    assert (
        c2.get(
            "/api/assistant/flight-checkouts/" + row["id"], params={"conversation_id": replacement}
        ).status_code
        == 404
    )


def test_real_live_voice_fragments_open_the_same_owner_review(desk):
    import asyncio
    from test_openai_live import config

    d = desk
    d.r.voice.config = config()
    chat, _, _ = research(d)

    async def scenario():
        queue = asyncio.Queue()
        client_queue = asyncio.Queue()
        observed = []
        wire = []
        local = []
        start = d.r.live_flight_checkouts.start

        def checkout(*args, **kwargs):
            try:
                view = start(*args, **kwargs)
                local.append(view["state"])
                return view
            except Exception as exc:
                local.append((type(exc).__name__, str(exc)))
                raise

        d.r.live_flight_checkouts.start = checkout

        class Client:
            async def send_json(self, event):
                observed.append(event)
                if event["type"] == "ready":
                    for n, value in enumerate(("帮我购买", "这个机票")):
                        await queue.put(
                            {
                                "type": "session.input_transcript.delta",
                                "delta": value,
                                "start_ms": 100 + n * 300,
                                "end_ms": 400 + n * 300,
                            }
                        )
                if event["type"] == "flight_checkout":
                    await client_queue.put({"type": "stop"})

            async def iter_text(self):
                while True:
                    yield json.dumps(await client_queue.get())

            async def close(self):
                pass

        class Provider:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            def __aiter__(self):
                async def events():
                    while True:
                        e = await queue.get()
                        yield json.dumps(e)
                        if e["type"] == "session.closed":
                            return

                return events()

            async def send(self, request):
                body = json.loads(request)
                wire.append(body)
                if body["type"] == "session.start":
                    await queue.put({"type": "session.started"})
                elif body["type"] == "session.close":
                    await queue.put({"type": "session.closed", "usage": {"seconds": 1}})

        voice = d.r.voice
        voice.connector = lambda *a, **k: Provider()
        principal = voice.consume(
            voice.ticket(
                {"kind": "owner", "id": "owner", "session": d.c.cookies["desk_companion_session"]}
            )["ticket"]
        )
        try:
            await asyncio.wait_for(voice.run(Client(), principal, "zh", conversation_id=chat), 6)
        except TimeoutError as exc:
            raise AssertionError(
                [(e["type"], e.get("text"), e.get("code"), e.get("reason")) for e in observed]
                + [(v["type"],) for v in wire]
                + local
            ) from exc
        cards = [x for x in observed if x["type"] == "flight_checkout"]
        assert len(cards) == 1
        assert (
            cards[0]["conversation_id"] == chat
            and cards[0]["live_flight_checkout"]["source"]["request"]["return_date"] == BACK
        )
        assert any(
            x["type"] == "session.instructions.append" and "LetsFG" in x["content"] for x in wire
        )
        assert "flight_purchase_review" in {
            t["name"] for t in wire[0]["session"]["delegation"]["responses"]["tools"]
        }
        assert not d.source.submitted and not d.source.searches

    asyncio.run(scenario())


def test_checkout_cannot_retain_a_charge_instruction_or_repeat_an_uncertain_submission(desk):
    from desk.store import DomainError

    d = desk
    empty = ask(d.c, "empty", BUY)
    assert empty["live_flight_checkout"]["state"] == "no_source"
    chat, _, _ = research(d)
    d.account["connected"] = True
    original = ask(d.c, "bind-purchase", BUY, chat)["live_flight_checkout"]
    priced = action(d, action(d, original, chat, "search"), chat, "select", 1)

    def lost(approval, passengers, email, *, principal):
        d.source.submitted.append(approval.approval_id)
        raise DomainError("LETSFG_PROVIDER_UNAVAILABLE", 503)

    d.source.submit = lost
    url = f"/api/assistant/flight-checkouts/{priced['id']}/confirm"
    body = payment(priced, chat)
    first = d.c.post(url, json=body).json()
    assert first["state"] == "uncertain" and first["receipt"].get("pnr") is None
    recovered = d.c.post(url, json=body).json()
    assert (
        recovered["state"] == "completed"
        and len(d.source.submitted) == 1
        and len(d.source.reads) == 1
    )
    assert recovered["receipt"]["charged_minor"] == body["amount_minor"]
    foreign = TestClient(d.app, base_url="https://testserver", headers=HEAD)
    foreign.post(
        "/api/session", json={"username": "owner", "password": "fixture"}
    ).raise_for_status()
    assert foreign.post(url, json=body).status_code == 404
    with d.r.store.connection() as db:
        marker = json.loads(
            db.execute(
                "select result from assistant_replies where json_extract(result,'$.live_id')=?",
                (priced["id"],),
            ).fetchone()[0]
        )
        assert set(marker) == {"kind", "live_id", "live_scope", "saved"}
    assert "live_flight_checkout" not in marker and not marker["saved"]


def test_live_delegated_kiwi_proposal_publishes_completed_original_to_chat(desk):
    import asyncio
    from desk.browser_research import current_chat_quote
    from test_openai_live import config

    d = desk

    async def scenario():
        source_events = asyncio.Queue()
        client_events = asyncio.Queue()
        shown = {}

        def nested(value):
            return {"type": "response.event", "delegation_id": "fixture-1", "event": value}

        class Client:
            async def send_json(self, event):
                if event["type"] == "ready":
                    shown["chat"] = event["conversation_id"]
                    for item in (
                        {"type": "response.created", "response": {"id": "r1"}},
                        {
                            "type": "response.output_item.done",
                            "item": {
                                "id": "i1",
                                "type": "function_call",
                                "call_id": "c1",
                                "name": "browser_research_draft",
                                "arguments": json.dumps(DRAFT),
                            },
                        },
                        {
                            "type": "response.completed",
                            "response": {
                                "id": "r1",
                                "status": "completed",
                                "output": [],
                                "usage": {"input_tokens": 5, "output_tokens": 2},
                            },
                        },
                    ):
                        await source_events.put(nested(item))
                if event["type"] == "proposal":
                    pid = event["proposal"]["id"]
                    shown["proposal"] = pid
                    chat = d.r.voice.conversations.entries[shown["chat"]]
                    assert d.r.live_flight_checkouts.last_proposal(chat)["id"] == pid
                    decision = await asyncio.to_thread(
                        d.c.post,
                        f"/api/assistant/proposals/{pid}/decisions",
                        headers={"X-Operation-Id": "share-voice-trip"},
                        json={"action": "confirm", "share_itinerary": True},
                    )
                    decision.raise_for_status()
                    shown["job"] = decision.json()["job"]["id"]
                    await client_events.put({"type": "stop"})

            async def iter_text(self):
                while True:
                    yield json.dumps(await client_events.get())

            async def close(self):
                pass

        class Provider:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            def __aiter__(self):
                async def events():
                    while True:
                        event = await source_events.get()
                        yield json.dumps(event)
                        if event["type"] == "session.closed":
                            return

                return events()

            async def send(self, value):
                kind = json.loads(value)["type"]
                if kind == "session.start":
                    await source_events.put({"type": "session.started"})
                if kind == "session.close":
                    await source_events.put({"type": "session.closed", "usage": {"seconds": 1}})

        voice = d.r.voice
        voice.config = config()
        voice.connector = lambda *args, **kwargs: Provider()
        principal = voice.consume(
            voice.ticket(
                {"kind": "owner", "id": "owner", "session": d.c.cookies["desk_companion_session"]}
            )["ticket"]
        )
        await asyncio.wait_for(voice.run(Client(), principal, "zh"), 8)
        return shown

    observed = asyncio.run(scenario())
    d.r.jobs.run_one()
    assert d.r.jobs.detail(observed["job"])["state"] == "succeeded"
    chat = d.r.voice.conversations.entries[observed["chat"]]
    ref = current_chat_quote(d.r, chat)
    assert ref["proposal_id"] == observed["proposal"] and ref["record_verified"]
    assert ref["quote"]["price_minor"] == 338959 and ref["quote"]["request"]["return_date"] == BACK
    reply = ask(d.c, "buy-voice-result", BUY, chat.id)
    assert reply["live_flight_checkout"]["source"]["request"]["checked_bag_kg"] == 20
    assert not d.source.searches and not d.source.submitted
