from desk.live_captions import LiveCaptionGroups, transcript_interval
from desk.conversation import Conversation


def test_timeline_groups_two_rounds_despite_uneven_delivery_and_late_fragments():
    groups = LiveCaptionGroups()
    assert groups.observe("user", (100, 500), 1) == 0
    assert groups.observe("user", (500, 900), 8) == 0  # Network delay is not a new question.
    assert groups.observe("assistant", (1100, 2100), 9) == 0
    assert groups.observe("user", (3000, 3600), 10) == 1
    assert groups.observe("assistant", (4000, 5500), 11) == 1
    assert groups.observe("assistant", (2100, 2300), 12) == 0
    assert groups.observe("user", (900, 1000), 13) == 0


def test_backchannel_does_not_split_continuing_user_speech():
    groups = LiveCaptionGroups()
    assert groups.observe("user", (100, 700), 1) == 0
    assert groups.observe("assistant", (600, 800), 2) == 0
    assert groups.observe("user", (750, 1100), 3) == 0


def test_live_history_updates_the_same_speaker_message_and_keeps_order():
    chat = Conversation("id", "owner", "rev", 0)
    chat.append_voice_fragment("user", "你能说中文吗？", "s", 0)
    chat.append_voice_fragment("assistant", "可以啊。", "s", 0)
    chat.append_voice_fragment("user", "明天有什么会议？", "s", 1)
    chat.append_voice_fragment("assistant", "没有会议。", "s", 1)
    chat.append_voice_fragment("assistant", "我可以说中文。", "s", 0)
    assert [item["text"] for item in chat.items] == [
        "你能说中文吗？",
        "可以啊。我可以说中文。",
        "明天有什么会议？",
        "没有会议。",
    ]
    assert len(chat.replay()) == 4


def test_transcript_intervals_are_validated_without_inventing_times():
    assert transcript_interval({"start_ms": 1, "end_ms": 2}) == (1, 2)
    for event in [
        {},
        {"start_ms": True, "end_ms": 2},
        {"start_ms": 2, "end_ms": 1},
        {"start_ms": 0, "end_ms": float("inf")},
    ]:
        assert transcript_interval(event) is None
