"""Per-utterance deadlines and content-free timing metadata.

Post-tool audio is a useful operational progress signal, not proof that the first
spoken word is semantically grounded. Only a labelled replay/human review can
certify the stricter five-second useful-answer SLO.
"""

import math
import re
import time
from dataclasses import dataclass, field


@dataclass
class Turn:
    id: int
    started: float
    ended: float | None = None
    input_end_ms: float | None = None
    needs_tool: bool = False
    tool_delivered: bool = False
    pending: set = field(default_factory=set)
    issued: dict = field(default_factory=dict)
    first_received_ms: float | None = None
    first_text_ms: float | None = None
    first_played_ms: float | None = None
    post_tool_played_ms: float | None = None
    playback_source: str | None = None
    endpoint_source: str | None = None
    progress_at: float | None = None
    slow_sent: bool = False
    review_ready: bool = False


class VoiceTurns:
    def __init__(self, clock=time.monotonic, target=5.0, cutoff=10.0):
        self.clock, self.target, self.cutoff = clock, target, cutoff
        self.current = None
        self.sequence = 0
        self.history = []

    def start(self):
        if self.current and self.current.ended is None:
            return self.current
        self.finish("interrupted")
        self.sequence += 1
        self.current = Turn(self.sequence, self.clock())
        return self.current

    def end(self, input_end_ms=None):
        turn = self.current or self.start()
        if turn.ended is None:
            turn.ended = self.clock()
            if isinstance(input_end_ms, (float, int)) and math.isfinite(input_end_ms):
                turn.input_end_ms = max(0, input_end_ms)
        return {
            "type": "turn_waiting",
            "turn_id": turn.id,
            "input_end_ms": turn.input_end_ms,
            "target_ms": round(self.target * 1000),
            "timeout_ms": round(self.cutoff * 1000),
        }

    def transcript(self, value, *, visual_context=False):
        turn = self.current or self.start()
        visual_question = visual_context and re.search(
            r"image|screen|picture|photo|截图|图片|画面|屏幕|照片|相片", value, re.I
        )
        if visual_question and not turn.pending and not turn.tool_delivered:
            turn.needs_tool = False
        creation_request = re.search(
            r"(?:创建|新建|添加|新增).{0,12}(?:日程|会议|會議)|\b(?:create|add)\b.*\b(?:meeting|event|appointment)",
            value,
            re.I,
        )
        # A schedule question must not be satisfied by a pre-query filler sound.
        # Creation may legitimately ask for a missing date/duration before any tool.
        # Once a tool is issued, tool() independently gates its claimed result.
        if (
            not visual_question
            and not creation_request
            and re.search(
                r"日程|行程|日历|日曆|会议|會議|calendar|schedule|meeting|appointment", value, re.I
            )
        ):
            turn.needs_tool = True
            if turn.post_tool_played_ms is None:
                turn.progress_at = None

    def tool(self, call_id):
        turn = self.current or self.start()
        turn.needs_tool = True
        turn.progress_at = None
        turn.review_ready = False
        turn.pending.add(call_id)
        return turn.id

    def delivered(self, turn_id, call_id, result):
        turn = self.current
        if not turn or turn.id != turn_id:
            return
        turn.pending.discard(call_id)
        if not result.get("error"):
            turn.tool_delivered = True
            proposal = result.get("proposal")
            if isinstance(proposal, dict) and isinstance(proposal.get("id"), str):
                turn.review_ready = True

    def review_waiting(self, turn_id):
        turn = self.current
        if turn and turn.id == turn_id and turn.review_ready and not turn.pending:
            return {"type": "turn_review", "turn_id": turn.id}
        return None

    def audio(self):
        turn = self.current or self.start()
        if turn.ended is None:
            self.end()
        audio_id = len(turn.issued) + 1
        # Bound metadata even if a provider emits tiny packets indefinitely.
        if audio_id > 10000:
            raise ValueError("Too many audio packets")
        turn.issued[audio_id] = turn.tool_delivered and not turn.pending
        if turn.first_received_ms is None:
            turn.first_received_ms = round((self.clock() - turn.ended) * 1000, 1)
        return {"turn_id": turn.id, "audio_id": audio_id, "after_tool": turn.issued[audio_id]}

    def text(self, value):
        turn = self.current
        if not turn or turn.ended is None or not value.strip():
            return None
        if turn.first_text_ms is None:
            turn.first_text_ms = round((self.clock() - turn.ended) * 1000, 1)
        if not turn.needs_tool or (turn.tool_delivered and not turn.pending):
            turn.progress_at = self.clock()
        return {"type": "turn_timing", **self.summary("text")}

    def playback(self, message):
        turn = self.current
        if (
            not turn
            or type(message.get("turn_id")) is not int
            or message.get("turn_id") != turn.id
            or turn.ended is None
        ):
            return None
        audio_id = message.get("audio_id")
        if type(audio_id) is not int or audio_id not in turn.issued:
            return None
        elapsed = message.get("elapsed_ms")
        source = message.get("timing_source")
        endpoint = message.get("endpoint_source")
        if (
            isinstance(elapsed, bool)
            or not isinstance(elapsed, (float, int))
            or not math.isfinite(elapsed)
            or not 0 <= elapsed <= 120000
            or source not in {"output_timestamp", "audio_context_estimate", "portaudio_dac"}
            or endpoint
            not in {"capture_energy", "provider_event", "fixture_annotation", "text_submit"}
        ):
            return None
        if turn.first_played_ms is None:
            turn.first_played_ms = round(elapsed, 1)
        if turn.issued[audio_id] and turn.post_tool_played_ms is None:
            turn.post_tool_played_ms = round(elapsed, 1)
        turn.playback_source, turn.endpoint_source = source, endpoint
        if elapsed < self.cutoff * 1000 and (not turn.needs_tool or turn.issued[audio_id]):
            turn.progress_at = self.clock()
        return {"type": "turn_timing", **self.summary("playing")}

    def poll(self):
        turn = self.current
        if (
            not turn
            or turn.ended is None
            or turn.progress_at is not None
            or (turn.review_ready and not turn.pending)
        ):
            return None
        elapsed = self.clock() - turn.ended
        if elapsed >= self.cutoff:
            return {"type": "error", "code": "VOICE_TURN_TIMEOUT", "turn_id": turn.id}
        if elapsed >= self.target and not turn.slow_sent:
            turn.slow_sent = True
            return {"type": "turn_slow", "turn_id": turn.id}
        return None

    def summary(self, outcome):
        t = self.current
        if not t:
            return {}
        return {
            "turn_id": t.id,
            "outcome": outcome,
            "server_wait_ms": round((self.clock() - (t.ended or t.started)) * 1000, 1),
            "first_received_ms": t.first_received_ms,
            "first_text_ms": t.first_text_ms,
            "first_played_ms": t.first_played_ms,
            "post_tool_played_ms": t.post_tool_played_ms,
            "timing_source": t.playback_source,
            "endpoint_source": t.endpoint_source,
            "semantic_verified": False,
            "response_started": t.progress_at is not None,
            "review_ready": t.review_ready,
        }

    def finish(self, outcome):
        if self.current:
            self.history.append(self.summary(outcome))
            self.history = self.history[-60:]
        self.current = None
