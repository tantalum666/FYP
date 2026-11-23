"""Pre-playback check for an A3 readback of one known Chinese HKD fare."""

import re

from . import hkd


class LiveFareSpeech:
    # 12 seconds of 24 kHz mono PCM16, expressed as the base64 received on the wire.
    MAX_AUDIO = 12 * 24000 * 2 * 4 // 3

    def __init__(self, clock):
        self.clock = clock
        self.last_price = None
        self.fare_source = ""
        self.previous_was_fare = False
        self.suppress_tail = False
        self.reset()

    def reset(self):
        self.expected = None
        self.retried = False
        self.review_sentence = None
        self.started = None
        self.audio = []
        self.size = 0
        self.caption = ""
        self.last_caption = {}
        self.overflow = False

    def new_input(self):
        self.suppress_tail = False
        self.reset()

    def remember(self, price, source, *, previous_was_fare=False):
        self.previous_was_fare = previous_was_fare
        self.last_price = price
        self.fare_source = source

    def start(self, review_sentence=None):
        if self.last_price is None:
            return None
        self.reset()
        self.suppress_tail = False
        self.expected = self.last_price
        self.review_sentence = review_sentence
        self.started = self.clock()
        return (
            "For this price, pronounce the following exact amount in the user's current Mandarin or Cantonese: "
            + self.expected["spoken_zh"]
            + "。 Use no other fractional currency units. Keep the other verified details and the same Alice voice."
        )

    def outgoing(self, event):
        kind = event["type"]
        if not self.expected:
            if self.suppress_tail and (
                kind == "audio" or (kind == "transcript" and event.get("role") == "assistant")
            ):
                return []
            return [event]
        if kind == "audio":
            self.size += len(event["audio"])
            if self.size <= self.MAX_AUDIO and len(self.audio) < 1024 and not self.overflow:
                self.audio.append(event)
            else:
                self.audio.clear()
                self.overflow = True
            return []
        if kind == "transcript" and event.get("role") == "assistant":
            self.last_caption = event
            self.caption += event.get("text", "")[: 4096 - len(self.caption)]
            if len(self.caption) >= 4096:
                self.overflow = True
            return []
        if kind == "interrupted":
            self.reset()
        if kind != "turn_complete" or not self.expected:
            return [event]
        # Live transcripts can normalize speech into bare digits. Those do not
        # establish which Chinese currency units were spoken. Require the actual
        # decimal wording before releasing PCM for this readback.
        words = re.sub(r"\s+", "", self.caption).translate(
            str.maketrans({"點": "点", "萬": "万", "兩": "二", "两": "二"})
        )
        correct = (
            bool(self.audio)
            and not self.overflow
            and self.expected["spoken_zh"] in words
            and hkd.last_spoken_amount(words) == self.expected
            and not re.search(r"[零〇一二三四五六七八九十\d][角毫仙分]", words)
        )
        if not correct and not self.retried and self.audio and self.caption and not self.overflow:
            # One correction in the already open A3 session. Never forward the rejected audio.
            instruction = self.start(self.review_sentence)
            self.retried = True
            return [{"type": "retry_fare_speech", "instruction": instruction}]
        text = (
            hkd.display_message(self.caption)
            if correct
            else hkd.display_message(self.review_sentence)
            if self.review_sentence
            else self.fare_source + self.expected["display"] + "。"
        )
        caption = {
            **self.last_caption,
            "type": "transcript",
            "role": "assistant",
            "text": text,
            "final": True,
            "caption_replace": True,
            "_fare_caption": True,
        }
        output = [caption, *self.audio, event] if correct else [caption, event]
        self.reset()
        self.suppress_tail = True
        self.previous_was_fare = True
        return output
