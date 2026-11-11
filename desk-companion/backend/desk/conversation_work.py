"""Admit an ordinary Alice turn into an existing Work run when the goal changes.

The owner names the change in the conversation, or in one reviewed voice
snapshot of that same wording. The voice review screen can also apply that
snapshot to one current run. This module calls the existing ``AgentRunService``
steer action, then one verified result from the existing offline deterministic
executor. A later turn in that same conversation can ask about the work and is
shown that same verified file again. An explicit continue ask advances that
same run once through ``AgentRunService.advance_one`` and shows the verified
file. A later explicit ask, with its own operation id, advances that same run
one more step only while it is still open. A finished, cancelled, failed, or
expired run stays closed. It does not create a task, a run, a queue, or a
model approval tool, and it does not call a provider.

An interruption before the steer commits leaves the goal unchanged and is not a
successful reply. A commit whose conversation receipt is lost is recovered by
the same operation id; the goal is not applied a second time. An unverified,
failed, or interrupted executor result is not shown as success. A verified
result is shown once for that operation id, and a later status ask reads it
back without running the executor again. Each continue operation advances at
most once. A different operation can take the next step only while the run
remains open.
"""

import hashlib
import json

from .agent_run_schemas import RunAction
from .agent_runs import TERMINAL
from .calendar import iso
from .store import DomainError, encode

# One matcher. Source labels and quote marks are closed lists, not extra patterns.
_IMPLICIT_LEADS = ("change the goal", "调整目标")
_EXPLICIT_LEADS = ("change work", "调整工作")
_SOURCE_LABELS = (
    "from:",
    "subject:",
    "date:",
    "to:",
    "cc:",
    "sender:",
    "location:",
    "notes:",
    "title:",
    "snippet:",
    "发件人：",
    "发件人:",
    "主题：",
    "主题:",
    "日期：",
    "日期:",
    "收件人：",
    "收件人:",
    "抄送：",
    "抄送:",
    "地点：",
    "地点:",
    "备注：",
    "备注:",
    "标题：",
    "标题:",
)
_QUOTE_WRAPS = (('"', '"'), ("'", "'"), ("“", "”"), ("「", "」"), ("『", "』"))
# Closed asks. A later turn uses one of these; other questions stay on the short chat path.
_FOLLOWUP_ASKS = frozenset(
    {
        "how is this work going",
        "what was the verified result",
        "show the verified result",
        "这项工作进行得怎么样",
        "核验结果是什么",
    }
)
# Closed continue asks. Status questions stay on the follow-up read above.
_CONTINUE_BARE = frozenset({"continue this work", "继续这项工作"})
_CONTINUE_LEADS = ("continue work", "继续工作")
_CLOSED = TERMINAL | {"paused", "blocked"}
_RESULT_KINDS = frozenset({"work_goal", "work_result"})

_TEXT = {
    "en": {
        "admitted": ("The goal of this work is now “{goal}”. {result}Nothing was sent or bought."),
        "recovered": "This work already has that goal. {result}The earlier change was kept.",
        "shown": "This work still has that verified report. {result}Nothing was sent or bought.",
        "continued": "This work continued. {result}Nothing was sent or bought.",
        "finished": "This work is already finished. It was not started again.",
        "cancelled": "This work was cancelled. It was not started again.",
        "failed": "This work failed. It was not started again.",
        "expired": "This work has expired. It was not started again.",
        "cannot_continue": "This work cannot continue from here.",
        "unchanged": "That is already the goal of this work.",
        "none": "No current work is linked to this task.",
        "no_report": "This conversation has no verified work to continue.",
        "name_work": "Name the work to change.",
        "name_continue": "Name the work to continue.",
        "ambiguous": "This task has more than one current work. Name the work to change.",
        "unavailable": "This work cannot take another goal change.",
        "not_found": "That work was not found.",
        "wrong_task": "That work is not on this task.",
        "empty": "Say the new goal after the colon.",
        "too_long": "That goal is too long to save.",
        "not_a_change": "That does not change this work.",
        "source_text": "This looks like copied source text. State the work change separately.",
    },
    "zh": {
        "admitted": "这项工作的目标已改为「{goal}」。{result}没有发送或购买。",
        "recovered": "这项工作已经是这个目标。{result}先前的更改仍在。",
        "shown": "这项工作仍有这份已核验报告。{result}没有发送或购买。",
        "continued": "这项工作已继续。{result}没有发送或购买。",
        "finished": "这项工作已经结束，没有重新开始。",
        "cancelled": "这项工作已取消，没有重新开始。",
        "failed": "这项工作已失败，没有重新开始。",
        "expired": "这项工作已过期，没有重新开始。",
        "cannot_continue": "这项工作不能从这里继续。",
        "unchanged": "这已经是这项工作的目标。",
        "none": "这个事务没有关联的当前工作。",
        "no_report": "这条对话里没有可以继续的已核验工作。",
        "name_work": "请写明要改的工作。",
        "name_continue": "请写明要继续的工作。",
        "ambiguous": "这个事务有多项当前工作。请写明要改的工作。",
        "unavailable": "这项工作不能再改目标。",
        "not_found": "没有找到这项工作。",
        "wrong_task": "这项工作不属于当前事务。",
        "empty": "请在冒号后写上新目标。",
        "too_long": "这个目标太长，没有保存。",
        "not_a_change": "这没有改这项工作。",
        "source_text": "这段内容像是复制的资料。请单独说明要怎样修改工作。",
    },
}


def _quoted_line(line: str) -> bool:
    if line.startswith((">", "＞")):
        return True
    return any(line.startswith(open_) and line.endswith(close) for open_, close in _QUOTE_WRAPS)


def _source_header(line: str) -> bool:
    folded = line.casefold()
    return any(folded.startswith(label.casefold()) for label in _SOURCE_LABELS)


def _owner_lines(message: str) -> list[str] | None:
    """Owner lines only. None when a source header is mixed in.

    Quoted lines are skipped. A source header is not stripped, because that
    would promote the unquoted body to an owner command.
    """
    own = []
    normalized = message.replace("\r\n", "\n").replace("\r", "\n")
    for line in normalized.strip().split("\n"):
        line = line.strip()
        if not line or _quoted_line(line):
            continue
        if _source_header(line):
            return None
        own.append(line)
    return own


def owner_instruction(message: str) -> str | None:
    """The one owner line. Quoted lines, source headers, and questions are not instructions."""
    own = _owner_lines(message)
    if own is None or len(own) != 1 or own[0].endswith(("?", "？")):
        return None
    return own[0]


def _followup_key(line: str) -> str:
    return line.casefold().strip().rstrip(" ?？.。")


def parse_work_followup(message: str) -> bool:
    """True when the one owner line asks to see the work already shown here."""
    own = _owner_lines(message)
    if own is None or len(own) != 1:
        return False
    return _followup_key(own[0]) in _FOLLOWUP_ASKS


def parse_work_continue(message: str) -> dict | None:
    """The one owner line that continues work, or None.

    A bare ask continues only when one current run is clear. Naming the run id
    selects that run. Questions, quotes, and source headers are not this line.
    """
    own = _owner_lines(message)
    if own is None or len(own) != 1 or own[0].endswith(("?", "？")):
        return None
    line = own[0]
    if _followup_key(line) in _CONTINUE_BARE:
        return {"run_id": None}
    for lead in _CONTINUE_LEADS:
        rest = _after_lead(line, lead)
        if rest is None or not rest[:1].isspace():
            continue
        token = rest.lstrip().rstrip(" .。")
        if len(token) == 32 and all(c in "0123456789abcdef" for c in token.casefold()):
            return {"run_id": token.casefold()}
    return None


def _continue_request(message: str, language: str) -> str:
    body = encode(
        {
            "type": "continue",
            "message": message.strip(),
            "language": language if language in _TEXT else "en",
        }
    )
    return "continue:" + hashlib.sha256(body.encode()).hexdigest()


def _after_lead(line: str, lead: str) -> str | None:
    if not line.casefold().startswith(lead.casefold()):
        return None
    return line[len(lead) :]


def _match_command(line: str) -> dict | None:
    for lead in _EXPLICIT_LEADS:
        rest = _after_lead(line, lead)
        if rest is None or not rest[:1].isspace():
            continue
        rest = rest.lstrip()
        token, tail = rest[:32], rest[32:]
        if len(token) != 32 or any(c not in "0123456789abcdef" for c in token.casefold()):
            continue
        tail = tail.lstrip()
        if tail.startswith((":", "：")):
            return {"run_id": token.casefold(), "goal": tail[1:].strip()}
    for lead in _IMPLICIT_LEADS:
        rest = _after_lead(line, lead)
        if rest is None:
            continue
        rest = rest.lstrip(" \t")
        if rest.startswith((":", "：")):
            return {"run_id": None, "goal": rest[1:].strip()}
    return None


def parse_changed_goal(message: str) -> dict | None:
    line = owner_instruction(message)
    if line is None:
        return None
    return _match_command(line)


class ConversationWork:
    def __init__(self, runtime):
        self.runtime = runtime
        self.store = runtime.store
        # Offline fixture control. Production leaves this unset. It is not an HTTP field.
        self.offline_interrupt = None

    def turn(self, payload, key, principal, conversation=None):
        action_key = _action_key(key)
        self._require_snapshot(payload, action_key, principal)
        language = payload.language if payload.language in _TEXT else "en"
        self._reject_other_continue(action_key, payload.message, language)
        if getattr(payload, "voice_steer", False) is True:
            return self._steer_snapshot(payload, action_key, principal, language)
        parsed = parse_changed_goal(payload.message)
        if parsed is None:
            continued = self._continue(payload, action_key, principal, language, conversation)
            if continued is not None:
                return continued
            if parse_work_followup(payload.message):
                shown = self._reshow(payload, principal, language, conversation)
                if shown is not None:
                    return shown
            lines = [line.strip() for line in payload.message.splitlines()]
            if any(_source_header(line) for line in lines) and any(
                _match_command(line) for line in lines
            ):
                return _reply(language, "source_text", admitted=False)
            if getattr(payload, "voice_origin_ref", None):
                return _reply(language, "not_a_change", admitted=False)
            return None
        self.runtime.agent_runs.session(principal)
        goal = parsed["goal"]
        if not goal:
            return _reply(language, "empty", admitted=False)
        if len(goal) > 4000:
            return _reply(language, "too_long", admitted=False)
        recovered = self._recovered(action_key, goal, principal, language)
        if recovered is not None:
            return recovered
        resolved = self._resolve(principal, parsed, payload.task_id, language)
        if resolved.get("kind") == "clarify":
            return resolved
        return self._commit(resolved, goal, action_key, principal, language)

    def _steer_snapshot(self, payload, action_key, principal, language):
        """Apply the reviewed wording to one current run. The same steer commits it."""
        self.runtime.agent_runs.session(principal)
        goal = payload.message.strip()
        if not goal:
            return _reply(language, "empty", admitted=False)
        if len(goal) > 4000:
            return _reply(language, "too_long", admitted=False)
        recovered = self._recovered(action_key, goal, principal, language)
        if recovered is not None:
            return recovered
        resolved = self._snapshot_run(
            principal, getattr(payload, "steer_run_id", None), payload.task_id, language
        )
        if resolved.get("kind") == "clarify":
            return resolved
        return self._commit(resolved, goal, action_key, principal, language)

    def _recovered(self, action_key, goal, principal, language):
        existing = self._operation_run(action_key)
        if not existing:
            return None
        current = self.runtime.agent_runs.detail(existing, principal)["run"]
        if current["goal"] != goal:
            raise DomainError("OPERATION_ID_CONFLICT")
        result = self._one_verified_result(current, principal, goal)
        return _reply(
            language, "recovered", admitted=True, recovered=True, run=current, result=result
        )

    def _commit(self, run, goal, action_key, principal, language):
        if run["goal"] == goal:
            return _reply(language, "unchanged", admitted=False, run=run)
        self._fence("before_commit")
        try:
            updated = self.runtime.agent_runs.action(
                run["id"],
                RunAction(action="steer", expected_version=run["version"], goal=goal),
                action_key,
                principal,
            )["run"]
        except DomainError as error:
            if error.code == "RUN_STEER_NOT_AVAILABLE":
                return _reply(language, "unavailable", admitted=False)
            raise
        self._fence("after_commit")
        result = self._one_verified_result(updated, principal, goal)
        return _reply(language, "admitted", admitted=True, run=updated, result=result)

    def _reshow(self, payload, principal, language, conversation):
        """Read the verified file this conversation already showed.

        The offline executor is not called. A provider is not called. A stored
        flag is not enough: the Markdown is read again, and ``verified`` is
        returned only for ``status: verified`` plus ``verification: byte_readback``.
        """
        prior = self._prior_verified_reply(conversation)
        if prior is None:
            return None
        self.runtime.agent_runs.session(principal)
        result = prior["result"]
        try:
            run = self.runtime.agent_runs.detail(prior["work_run_id"], principal)["run"]
        except DomainError as error:
            if error.code == "RUN_NOT_FOUND":
                return None
            raise
        if payload.task_id and payload.task_id not in (run.get("task_ids") or []):
            return None
        session_hash = hashlib.sha256(principal["session"].encode()).hexdigest()
        reading = self._markdown_reading(result["artifact_id"], result["goal"], session_hash)
        if reading is None:
            raise DomainError("CONVERSATION_WORK_RESULT_UNKNOWN", 409)
        verified = _require_verified(reading)
        if verified["artifact_id"] != result["artifact_id"] or verified["goal"] != result["goal"]:
            raise DomainError("CONVERSATION_WORK_RESULT_UNVERIFIED", 409)
        return _reply(
            language, "shown", admitted=False, run=run, result=verified, publish_result=True
        )

    def _prior_verified_reply(self, conversation):
        if conversation is None:
            return None
        for item in reversed(conversation.items):
            if item.get("role") != "assistant" or not item.get("operation_id"):
                continue
            reply = _verified_work_reply(self._stored_reply(item["operation_id"]))
            if reply is not None:
                return reply
        return None

    def _stored_reply(self, operation_id):
        with self.store.connection() as conn:
            row = conn.execute(
                "SELECT result FROM assistant_replies WHERE id=?",
                (operation_id,),
            ).fetchone()
        if row is None:
            return None
        try:
            reply = json.loads(row["result"])
        except json.JSONDecodeError:
            return None
        return reply if isinstance(reply, dict) else None

    def _continue(self, payload, action_key, principal, language, conversation):
        """Advance one shown run once. A provider is not called.

        The ask has to be an explicit continue phrase. Status questions stay on
        the read-only follow-up. Each operation id calls ``advance_one`` at most
        once. A later operation takes one more step only while that run is still
        open. A finished, cancelled, failed, paused, blocked, or expired run is
        not reopened and does not create a job or proposal.
        """
        parsed = parse_work_continue(payload.message)
        if parsed is None:
            return None
        self.runtime.agent_runs.session(principal)
        request = _continue_request(payload.message, language)
        recovered = self._recovered_continue(action_key, request, principal, language)
        if recovered is not None:
            return recovered
        shown = self._shown_runs(conversation, principal, payload.task_id)
        if not shown:
            return _reply(language, "no_report", admitted=False)
        selected = self._select_continue(shown, parsed, principal, payload.task_id, language)
        if selected.get("kind") == "clarify":
            return selected
        now = iso(self.store.clock())
        closed = _closed_reply(language, selected, now=now)
        if closed is not None:
            return closed
        if selected.get("mode") != "deterministic":
            return _reply(language, "cannot_continue", admitted=False)
        self._fence("before_continue")
        bound = self.runtime.agent_runs.refresh_owner(selected["id"], principal)
        closed = _closed_reply(language, bound, now=now)
        if closed is not None:
            return closed
        self._record_continue(action_key, request, selected["id"], pending=True)
        try:
            stepped = self.runtime.agent_runs.advance_one(selected["id"])
        except Exception:
            raise DomainError("CONVERSATION_WORK_RESULT_UNKNOWN", 409) from None
        if not stepped:
            with self.store.connection(write=True) as conn:
                conn.execute(
                    "DELETE FROM agent_run_operations WHERE id=? AND request_hash=?",
                    (action_key, "pending/" + request),
                )
            raise DomainError("CONVERSATION_WORK_RESULT_INTERRUPTED", 409)
        self._record_continue(action_key, request, selected["id"])
        self._fence("after_continue")
        return self._continued_result(selected["id"], principal, language, recovered=False)

    def _recovered_continue(self, action_key, request, principal, language):
        row = self._operation_row(action_key)
        if row is None or not str(row["request_hash"]).removeprefix("pending/").startswith(
            "continue:"
        ):
            return None
        if row["request_hash"].removeprefix("pending/") != request:
            raise DomainError("OPERATION_ID_CONFLICT")
        if row["request_hash"].startswith("pending/"):
            raise DomainError("CONVERSATION_WORK_RESULT_UNKNOWN", 409)
        return self._continued_result(row["run_id"], principal, language, recovered=True)

    def _continued_result(self, run_id, principal, language, *, recovered):
        try:
            current = self.runtime.agent_runs.detail(run_id, principal)["run"]
        except DomainError as error:
            if error.code == "RUN_NOT_FOUND":
                raise DomainError("CONVERSATION_WORK_RESULT_UNKNOWN", 409) from None
            raise
        if current["state"] in {"failed", "blocked"}:
            raise DomainError(_result_error(current), 409)
        if current["state"] in {"cancelled", "partial"}:
            return _closed_reply(language, current)
        session_hash = hashlib.sha256(principal["session"].encode()).hexdigest()
        reading = self._read_verified(current, current["goal"], session_hash)
        if reading is None:
            raise DomainError("CONVERSATION_WORK_RESULT_UNKNOWN", 409)
        verified = _require_verified(reading)
        return _reply(
            language,
            "continued",
            admitted=False,
            recovered=recovered,
            run=current,
            result=verified,
            publish_result=True,
        )

    def _select_continue(self, shown, parsed, principal, task_id, language):
        if parsed["run_id"]:
            match = next((run for run in shown if run["id"] == parsed["run_id"]), None)
            if match is None:
                return _reply(language, "not_found", admitted=False)
            return match
        current = self._current_runs(principal, task_id)
        open_shown = [run for run in shown if run["state"] not in _CLOSED]
        if len(current) > 1 or len(open_shown) > 1:
            return _reply(language, "name_continue", admitted=False)
        if len(open_shown) == 1:
            return open_shown[0]
        if len(shown) == 1:
            return shown[0]
        return _reply(language, "name_continue", admitted=False)

    def _shown_runs(self, conversation, principal, task_id):
        if conversation is None:
            return []
        found, seen = [], set()
        for item in conversation.items:
            if item.get("role") != "assistant" or not item.get("operation_id"):
                continue
            reply = _verified_work_reply(self._stored_reply(item["operation_id"]))
            run_id = None if reply is None else reply.get("work_run_id")
            if not isinstance(run_id, str) or run_id in seen:
                continue
            try:
                run = self.runtime.agent_runs.detail(run_id, principal)["run"]
            except DomainError as error:
                if error.code == "RUN_NOT_FOUND":
                    continue
                raise
            if task_id and task_id not in (run.get("task_ids") or []):
                continue
            seen.add(run_id)
            found.append(run)
        return found

    def _current_runs(self, principal, task_id):
        rows = self.runtime.agent_runs.listing(principal)["runs"]
        current = []
        for row in rows:
            if row.get("private_hidden") or row.get("state") in _CLOSED:
                continue
            if task_id and task_id not in (row.get("task_ids") or []):
                continue
            current.append(row)
        return current

    def _reject_other_continue(self, action_key, message, language):
        row = self._operation_row(action_key)
        if row is None or not str(row["request_hash"]).removeprefix("pending/").startswith(
            "continue:"
        ):
            return
        if row["request_hash"].removeprefix("pending/") != _continue_request(message, language):
            raise DomainError("OPERATION_ID_CONFLICT")

    def _record_continue(self, action_key, request, run_id, *, pending=False):
        """Reserve before dispatch so a crash cannot repeat the next Work step."""
        with self.store.connection(write=True) as conn:
            old = conn.execute(
                "SELECT request_hash, run_id FROM agent_run_operations WHERE id=?",
                (action_key,),
            ).fetchone()
            if old:
                if (
                    old["request_hash"].removeprefix("pending/") != request
                    or old["run_id"] != run_id
                ):
                    raise DomainError("OPERATION_ID_CONFLICT")
                if pending:
                    raise DomainError("CONVERSATION_WORK_RESULT_UNKNOWN", 409)
                conn.execute(
                    "UPDATE agent_run_operations SET request_hash=? WHERE id=?",
                    (request, action_key),
                )
                return
            conn.execute(
                "INSERT INTO agent_run_operations VALUES(?,?,?)",
                (action_key, "pending/" + request if pending else request, run_id),
            )

    def _operation_row(self, action_key):
        with self.store.connection() as conn:
            return conn.execute(
                "SELECT request_hash, run_id FROM agent_run_operations WHERE id=?",
                (action_key,),
            ).fetchone()

    def _one_verified_result(self, run, principal, goal):
        """One offline executor result for this goal. A provider is never called.

        Deterministic mode reuses ``AgentRunService.advance_one`` for this run
        only, then reads the published Markdown back. Model mode is not stepped,
        because that step would call a provider. An existing verified readback
        is returned without a second publish.
        """
        if run.get("mode") != "deterministic":
            return None
        session_hash = hashlib.sha256(principal["session"].encode()).hexdigest()
        existing = self._read_verified(run, goal, session_hash)
        if existing is not None:
            return _require_verified(existing)
        self._fence("before_result")
        for _ in range(_OFFLINE_STEPS):
            stepped = self.runtime.agent_runs.advance_one(run["id"])
            current = self.runtime.agent_runs.detail(run["id"], principal)["run"]
            reading = self._read_verified(current, goal, session_hash)
            if reading is not None:
                verified = _require_verified(reading)
                self._fence("after_result")
                return verified
            if not stepped or current["state"] in _HALT:
                raise DomainError(_result_error(current), 409)
        raise DomainError("CONVERSATION_WORK_RESULT_UNKNOWN", 409)

    def _read_verified(self, run, goal, session_hash):
        for artifact_id in run.get("current_artifact_ids") or []:
            reading = self._markdown_reading(artifact_id, goal, session_hash)
            if reading is not None:
                return reading
        return None

    def _markdown_reading(self, artifact_id, goal, session_hash):
        """Byte-read one Markdown artifact. Missing files are skipped by the caller."""
        goal_line = "Goal: " + goal
        try:
            reading = self.runtime.artifacts.read(artifact_id, session_hash=session_hash)
        except DomainError as error:
            if error.code == "FILE_NOT_FOUND":
                return None
            raise DomainError("CONVERSATION_WORK_RESULT_UNKNOWN", 409) from None
        artifact = reading["artifact"]
        if artifact.get("format") != "markdown":
            return None
        content = reading.get("content") or ""
        verified = (
            artifact.get("status") == "verified"
            and artifact.get("verification") == "byte_readback"
            and goal_line in content.splitlines()
        )
        excerpt = goal_line if len(goal_line) <= 240 else goal_line[:240]
        return {
            "verified": verified,
            "state": "verified" if verified else artifact.get("status") or "unverified",
            "verification": artifact.get("verification") or "unverified",
            "goal": goal if verified else "",
            "artifact_id": artifact_id,
            "format": "markdown",
            "excerpt": excerpt if verified else "",
        }

    def _snapshot_run(self, principal, run_id, task_id, language):
        if run_id:
            return self._resolve(principal, {"run_id": run_id, "goal": ""}, task_id, language)
        rows = self.runtime.agent_runs.listing(principal)["runs"]
        if task_id:
            rows = [row for row in rows if task_id in (row.get("task_ids") or [])]
        eligible = [row for row in rows if _steerable(row)]
        if len(eligible) == 1:
            return self.runtime.agent_runs.detail(eligible[0]["id"], principal)["run"]
        if len(eligible) > 1:
            return _reply(language, "ambiguous", admitted=False)
        if rows:
            return _reply(language, "unavailable", admitted=False)
        return _reply(language, "none", admitted=False)

    def _require_snapshot(self, payload, action_key, principal) -> None:
        """A reviewed voice snapshot must match its text. Steer stays in ``turn``."""
        ref = getattr(payload, "voice_origin_ref", None)
        if getattr(payload, "voice_steer", False) is True and not ref:
            raise DomainError("VOICE_STEER_REQUIRES_SNAPSHOT", 422)
        if not ref:
            return
        text = self.runtime.voice.work.reviewed_text(ref, principal)
        if text is None:
            if self._operation_run(action_key):
                return
            raise DomainError("VOICE_DRAFT_EXPIRED", 410)
        if payload.message.strip() != text.strip():
            raise DomainError("VOICE_INPUT_CHANGED", 409)

    def _fence(self, phase: str) -> None:
        if self.offline_interrupt != phase:
            return
        code = {
            "before_commit": "CONVERSATION_WORK_INTERRUPTED",
            "before_result": "CONVERSATION_WORK_RESULT_INTERRUPTED",
            "before_continue": "CONVERSATION_WORK_RESULT_INTERRUPTED",
            "after_commit": "CONVERSATION_WORK_RESULT_UNKNOWN",
            "after_result": "CONVERSATION_WORK_RESULT_UNKNOWN",
            "after_continue": "CONVERSATION_WORK_RESULT_UNKNOWN",
        }[phase]
        raise DomainError(code, 409)

    def _operation_run(self, action_key):
        with self.store.connection() as conn:
            row = conn.execute(
                "SELECT run_id FROM agent_run_operations WHERE id=?",
                (action_key,),
            ).fetchone()
        return row["run_id"] if row else None

    def _resolve(self, principal, parsed, task_id, language):
        if parsed["run_id"]:
            try:
                run = self.runtime.agent_runs.detail(parsed["run_id"], principal)["run"]
            except DomainError as error:
                if error.code == "RUN_NOT_FOUND":
                    return _reply(language, "not_found", admitted=False)
                raise
            if task_id and task_id not in (run.get("task_ids") or []):
                return _reply(language, "wrong_task", admitted=False)
            if not _steerable(run):
                return _reply(language, "unavailable", admitted=False, run=run)
            return run
        if not task_id:
            return _reply(language, "name_work", admitted=False)
        rows = [
            row
            for row in self.runtime.agent_runs.listing(principal)["runs"]
            if task_id in (row.get("task_ids") or [])
        ]
        eligible = [row for row in rows if _steerable(row)]
        if len(eligible) == 1:
            return self.runtime.agent_runs.detail(eligible[0]["id"], principal)["run"]
        if len(eligible) > 1:
            return _reply(language, "ambiguous", admitted=False)
        if rows:
            return _reply(language, "unavailable", admitted=False)
        return _reply(language, "none", admitted=False)


_HALT = TERMINAL | {"blocked", "paused", "waiting_review", "waiting_input", "waiting_effect"}
# Existing read budget is 32. Compose and the verified publish sit after those reads.
_OFFLINE_STEPS = 40


def _action_key(key: str) -> str:
    return "wg/" + hashlib.sha256(key.encode()).hexdigest()


def _steerable(run) -> bool:
    return run.get("state") != "cancelled" and run.get("plan_revision", 2) < 2


def _closed_reply(language, run, *, now=None):
    """A clear refusal. Closed runs are not started again and create no work."""
    state = run.get("state")
    if state == "cancelled":
        return _reply(language, "cancelled", admitted=False)
    if state == "failed":
        return _reply(language, "failed", admitted=False)
    if state in TERMINAL:
        return _reply(language, "finished", admitted=False)
    if state in {"paused", "blocked"}:
        return _reply(language, "cannot_continue", admitted=False)
    deadline = run.get("deadline")
    if now is not None and isinstance(deadline, str) and deadline and deadline <= now:
        return _reply(language, "expired", admitted=False)
    return None


def _result_error(run):
    """A busy or uncertain step stays recoverable. A failed run does not."""
    reason = run.get("state_reason") or ""
    if "UNKNOWN" in reason:
        return "CONVERSATION_WORK_RESULT_UNKNOWN"
    if run.get("state") in {"failed", "partial", "cancelled", "blocked"}:
        return "CONVERSATION_WORK_RESULT_FAILED"
    return "CONVERSATION_WORK_RESULT_UNKNOWN"


def _require_verified(reading):
    if reading.get("verified") is True and reading.get("verification") == "byte_readback":
        return reading
    code = (
        "CONVERSATION_WORK_RESULT_UNVERIFIED"
        if reading.get("verification") != "byte_readback" or reading.get("state") != "verified"
        else "CONVERSATION_WORK_RESULT_FAILED"
    )
    raise DomainError(code, 409)


def _result_sentence(language, result):
    if not result or result.get("verified") is not True:
        return ""
    excerpt = result.get("excerpt") or ""
    if language == "zh":
        if not excerpt.endswith("。"):
            excerpt += "。"
        return f"报告文件已核验：{excerpt}"
    if not excerpt.endswith("."):
        excerpt += "."
    return f"Report file verified: {excerpt} "


def _verified_work_reply(reply):
    """A stored conversation reply that already claimed one verified Markdown file."""
    if not isinstance(reply, dict) or reply.get("kind") not in _RESULT_KINDS:
        return None
    result = reply.get("result")
    run_id = reply.get("work_run_id")
    if not isinstance(result, dict) or not isinstance(run_id, str) or not run_id:
        return None
    goal, artifact_id = result.get("goal"), result.get("artifact_id")
    if (
        result.get("verified") is True
        and result.get("state") == "verified"
        and result.get("verification") == "byte_readback"
        and result.get("format") == "markdown"
        and isinstance(goal, str)
        and goal
        and isinstance(artifact_id, str)
        and artifact_id
    ):
        return reply
    return None


def _reply(
    language, code, *, admitted, recovered=False, run=None, result=None, publish_result=None
):
    message = _TEXT[language][code].format(
        goal=(run or {}).get("goal", ""),
        result=_result_sentence(language, result),
    )
    if publish_result is None:
        publish_result = admitted
    shown = publish_result and not admitted
    body = {
        "mode": "local_rules",
        "kind": "work_goal" if admitted else "work_result" if shown else "clarify",
        "saved": False,
        "admitted": admitted,
        "recovered": recovered,
        "message": message,
    }
    if run is not None and (admitted or shown):
        body["work_run_id"] = run["id"]
        body["goal"] = run["goal"]
        body["plan_revision"] = run["plan_revision"]
    if result and result.get("verified") is True and (admitted or shown):
        body["result"] = {
            "verified": True,
            "state": "verified",
            "verification": "byte_readback",
            "quality": "not_semantically_checked",
            "goal": result["goal"],
            "artifact_id": result["artifact_id"],
            "format": "markdown",
        }
    return body
