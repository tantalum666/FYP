import asyncio
import base64
from dataclasses import replace
import json

import pytest

from desk import hkd
from desk.app import COOKIE
from desk.commerce_quotes import brief_quote, kiwi_fare_reply, kiwi_hkd_price, read_quote
from desk.conversation import memory_context
from desk.flight_search import recorded_quote
from desk.openai_live import OpenAILiveProtocol
from desk.voice_settings import VoiceRegistration, VoiceSelection
from test_flight_connector_spend import ITEM, LEG, call, draft
from desk.flight_search import search_arguments
from test_official_text_sessions import desk as desk, send
from test_openai_live import config

MIXED = "港币三千三百八十九元五角九仙"
SPOKEN = "三千三百八十九点五九港元"
DISPLAY = "HK$3,389.59"


@pytest.mark.parametrize(
    ("minor", "spoken"),
    [
        (0, "零港元"),
        (1, "零点零一港元"),
        (5, "零点零五港元"),
        (50, "零点五港元"),
        (105, "一点零五港元"),
        (1000, "十港元"),
        (12000, "一百二十港元"),
        (1000100, "一万零一港元"),
        (338959, SPOKEN),
        (10**9, "一千万港元"),
    ],
)
def test_screen_and_chinese_amount_round_trip(minor, spoken):
    price = hkd.amount(minor)
    assert price["spoken_zh"] == spoken
    assert hkd.present_text(spoken) == price["display"]
    assert hkd.present_text(price["display"], spoken=True) == spoken


def test_other_currencies_quotes_and_invalid_amounts_are_untouched():
    examples = [
        "美元三元五角九分",
        "HK$3.999",
        "«EUR 41.99»",
        "US$3,389.59",
        f"用户写的是「{MIXED}」",
        f'"> {MIXED}"',
    ]
    for text in examples:
        assert hkd.present_text(text) == text
    assert all(hkd.amount(v) is None for v in (True, -1, 338959.9, "338959", 10**9 + 1))
    assert hkd.display_message("机票是" + MIXED) == "机票是" + DISPLAY
    assert not hkd.asks_fare_amount("明天去伦敦的机票多少钱？")
    assert not hkd.asks_spoken_readback("再说一遍", previous_was_fare=False)
    assert hkd.asks_spoken_readback("再说一遍", previous_was_fare=True)


def kiwi_record():
    request = draft()
    spec = request["quote_request"]
    spec.update(destination="NRT", departure="2026-11-24", return_date="2026-12-01", nonstop=False)
    outbound = {
        **LEG,
        "route": ["HKG", "TPE", "NRT"],
        "departureTime": "2026-11-24T12:00:00",
        "arrivalTime": "2026-11-24T22:00:00",
        "segments": [
            {"from": "HKG", "to": "TPE", "flightNumber": "BR852", "carrier": "BR"},
            {"from": "TPE", "to": "NRT", "flightNumber": "BR196", "carrier": "BR"},
        ],
    }
    inbound = {
        "route": ["NRT", "HKG"],
        "departureTime": "2026-12-01T10:00:00",
        "arrivalTime": "2026-12-01T15:00:00",
        "segments": [{"from": "NRT", "to": "HKG"}],
    }
    item = {
        **ITEM,
        "price": 3389.59,
        "tripType": "return",
        "outbound": outbound,
        "inbound": inbound,
    }
    wire = {**call([item]), "arguments": search_arguments(spec)}
    return read_quote(
        request, json.dumps(recorded_quote([wire], request, "t")), "2026-11-23T07:29:01Z"
    )


def test_kiwi_minor_unit_and_unknown_total_survive_projection():
    quote = kiwi_record()
    assert quote["offer"]["label"] == "HKG–NRT BR852 / BR196"
    assert quote["offer"]["price_minor"] == quote["subtotal_minor"] == 338959
    assert quote["offer"]["extras_minor"] is None and quote["total_minor"] is None
    for projected in (quote, brief_quote(quote)):
        assert kiwi_hkd_price(projected) == hkd.amount(338959)
        assert DISPLAY in kiwi_fare_reply(projected)["message"]
    assert kiwi_hkd_price({**quote, "subtotal_minor": None}) is None
    assert kiwi_hkd_price({**quote, "offer": {**quote["offer"], "currency": "USD"}}) is None
    instrument = OpenAILiveProtocol()
    instrument.language = "zh"
    wire = instrument.result(
        {"id": "g", "name": "browser_research_status"}, {"record_verified": True, "quote": quote}
    )
    assert json.loads(wire[0]["item"]["output"])["fare_amount"] == hkd.amount(338959)
    assert wire[1]["type"] == "session.instructions.append" and SPOKEN in wire[1]["content"]
    assert instrument.fare_speech.expected["minor"] == 338959


def test_ordinary_price_question_reads_verified_quote_before_model(desk, monkeypatch):
    _, client, api = desk
    from desk import browser_research

    quote = brief_quote(kiwi_record())
    monkeypatch.setattr(
        browser_research,
        "current_chat_quote",
        lambda runtime, chat: {
            "record_verified": True,
            "quote": quote,
        },
    )
    answer = send(client, "read-stored", "刚才的票价是多少？").json()["message"]
    assert all(
        part in answer
        for part in (
            "Kiwi.com",
            "HKG–NRT BR852 / BR196",
            DISPLAY,
            "行李重量未确认",
            "最终应付金额仍待卖家确认",
        )
    )
    assert not api.requests


def test_sessions_fare_tool_ends_with_provider_minor_units(desk, monkeypatch):
    from desk import browser_research

    _, client, provider = desk
    quote = kiwi_record()
    monkeypatch.setattr(
        browser_research,
        "status",
        lambda runtime, args: {
            "record_verified": True,
            "proposal_id": args["proposal_id"],
            "quote": quote,
        },
    )
    provider.next_calls = [("browser_research_status", {"proposal_id": "a" * 32})]
    provider.final = "Kiwi.com 的报价为 HK$9,999.99。"
    answer = send(client, "model-selected-source", "刚才的票价是多少？").json()
    assert DISPLAY in answer["message"] and "BR852 / BR196" in answer["message"]
    assert provider.functions and answer["message"] != provider.final


def test_actual_sessions_readback_normalizes_only_assistant_text(desk):
    runtime, client, provider = desk
    provider.final = json.dumps(
        {"delivery": "neutral", "message": "Kiwi.com 显示" + MIXED + "，总额未确认。"}
    )
    user_text = "请说明这次香港往返东京报价，我的原话是「" + MIXED + "」。"
    reply = send(client, "yuan-test", user_text, stream=True)
    assert reply.is_success
    frames = [json.loads(x[6:]) for x in reply.text.splitlines() if x.startswith("data: ")]
    assert MIXED not in reply.text
    result = frames[-1]["reply"]
    assert result["message"] == "Kiwi.com 显示" + DISPLAY + "，总额未确认。"
    assert provider.creations and not provider.functions
    chat = runtime.voice.conversations.entries[result["conversation_id"]]
    assert chat.items[0]["text"] == user_text
    assert chat.replay()[0]["item"]["content"][0]["text"] == user_text
    assert SPOKEN in chat.replay()[-1]["item"]["content"][0]["text"]
    assert send(client, "yuan-test", user_text).json()["message"] == result["message"]


class FareProvider:
    """Feed the recorded protocol boundaries and capture the original PCM returned by the desk."""

    def __init__(self, audio, caption, voice):
        self.queue = asyncio.Queue()
        self.audio, self.captions, self.voice = (
            audio,
            list(caption) if isinstance(caption, tuple) else [caption],
            voice,
        )
        self.sent = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        pass

    async def __aiter__(self):
        while True:
            event = await self.queue.get()
            yield json.dumps(event)
            if event["type"] == "session.closed":
                return

    async def send(self, raw):
        event = json.loads(raw)
        self.sent.append(event)
        if event["type"] == "session.start":
            await self.queue.put(
                {
                    "type": "session.started",
                    "session": {
                        "model": "gpt-live-1.1",
                        "audio": {"output": {"voice": {"id": self.voice}}},
                    },
                }
            )
            await self.queue.put(
                {"type": "session.input_transcript.delta", "delta": "再念一遍刚才的票价"}
            )
        elif event["type"] == "session.instructions.append":
            # The PCM arrives first and may not reach the owner before the caption check.
            await self.queue.put(
                {
                    "type": "session.output_audio.delta",
                    "delta": base64.b64encode(self.audio).decode(),
                }
            )
            caption = self.captions.pop(0) if len(self.captions) > 1 else self.captions[0]
            await self.queue.put({"type": "session.output_transcript.delta", "delta": caption})
        elif event["type"] == "session.close":
            await self.queue.put({"type": "session.closed", "usage": {"seconds": 2}})


def voice_roundtrip(runtime, client, audio, caption, voice="voice_fixture_alice"):
    service = runtime.voice
    service.config = replace(config(), model="gpt-live-1.1")
    service.settings.register(
        VoiceRegistration(
            expected_version=1, id=voice, name="Alice test", description="An original adult voice."
        ),
        "register",
    )
    service.settings.select(
        VoiceSelection(expected_version=2, voice=voice, delivery="Natural Mandarin and Cantonese."),
        "choose",
    )
    owner = {"kind": "owner", "id": "owner", "session": client.cookies.get(COOKIE)}
    chat = service.conversations.open(owner, memory_context(runtime, True)[0])
    chat.append("assistant", "上次我提到" + MIXED + "。")
    provider = FareProvider(audio, caption, voice)
    service.connector = lambda *_args, **_kwargs: provider
    token = client.post("/api/voice/tickets", headers={"X-Desk-Request": "1"}).json()["ticket"]
    packets, captions = [], []
    with client.websocket_connect("/api/voice/ws", headers={"Origin": "http://testserver"}) as ws:
        ws.send_json({"ticket": token, "language": "zh", "conversation_id": chat.id})
        for _ in range(30):
            event = ws.receive_json()
            assert event["type"] != "error", event
            if event["type"] == "audio":
                packets.append(base64.b64decode(event["audio"]))
            if event["type"] == "transcript" and event["role"] == "assistant":
                captions.append(event["text"])
            if event["type"] == "turn_complete":
                break
        ws.send_json({"type": "stop"})
    assert provider.sent[0]["session"]["audio"]["output"]["voice"] == {"id": voice}
    history = provider.sent[0]["session"]["input"]
    assert any(
        m["role"] == "assistant"
        and m["content"][0]["type"] == "output_text"
        and SPOKEN in m["content"][0]["text"]
        for m in history
    )
    assert MIXED not in str(history) and chat.items[0]["text"].endswith(MIXED + "。")
    assert any(
        w["type"] == "session.instructions.append" and SPOKEN in w["content"] for w in provider.sent
    )
    return b"".join(packets), "".join(captions)


@pytest.mark.parametrize(
    "caption", [SPOKEN, MIXED, "一万" + SPOKEN, "HK$3,389.59", (MIXED, SPOKEN)]
)
def test_websocket_checks_original_audio_before_playback(desk, caption):
    runtime, client, _ = desk
    pcm = b"\x10\x00" * 2400
    played, visible = voice_roundtrip(runtime, client, pcm, caption)
    assert played == (pcm if caption in (SPOKEN, (MIXED, SPOKEN)) else b"")
    assert DISPLAY in visible and MIXED not in visible
