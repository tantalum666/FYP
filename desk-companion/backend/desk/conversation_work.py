"""Admit an ordinary Alice turn into an existing Work run when the goal changes.

The owner names the change in the conversation, or in one reviewed voice
snapshot of that same wording. The voice review screen can also apply that
snapshot to one current run. This module calls the existing ``AgentRunService``
steer action. It does not create a task, a run, a queue, or a model approval
tool, and it does not call a provider.

An interruption before the steer commits leaves the goal unchanged and is not a
successful reply. A commit whose conversation receipt is lost is recovered by
the same operation id; the goal is not applied a second time.
"""

import hashlib

from .agent_run_schemas import RunAction
from .store import DomainError

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

_TEXT = {
    "en": {
        "admitted": (
            "The goal of this work is now “{goal}”. Earlier results stay. Nothing was sent or bought."
        ),
        "recovered": "This work already has that goal. The earlier change was kept.",
        "unchanged": "That is already the goal of this work.",
        "none": "No current work is linked to this task.",
        "name_work": "Name the work to change.",
        "ambiguous": "This task has more than one current work. Name the work to change.",
        "unavailable": "This work cannot take another goal change.",
        "not_found": "That work was not found.",
        "wrong_task": "That work is not on this task.",
        "empty": "Say the new goal after the colon.",
        "too_long": "That goal is too long to save.",
        "not_a_change": "That does not change this work.",
    },
    "zh": {
        "admitted": "这项工作的目标已改为「{goal}」。已有结果还在。没有发送或购买。",
        "recovered": "这项工作已经是这个目标。先前的更改仍在。",
        "unchanged": "这已经是这项工作的目标。",
        "none": "这个事务没有关联的当前工作。",
        "name_work": "请写明要改的工作。",
        "ambiguous": "这个事务有多项当前工作。请写明要改的工作。",
        "unavailable": "这项工作不能再改目标。",
        "not_found": "没有找到这项工作。",
        "wrong_task": "这项工作不属于当前事务。",
        "empty": "请在冒号后写上新目标。",
        "too_long": "这个目标太长，没有保存。",
        "not_a_change": "这没有改这项工作。",
    },
}


def _quoted_line(line: str) -> bool:
    if line.startswith((">", "＞")):
        return True
    return any(line.startswith(open_) and line.endswith(close) for open_, close in _QUOTE_WRAPS)


def _source_header(line: str) -> bool:
    folded = line.casefold()
    return any(folded.startswith(label.casefold()) for label in _SOURCE_LABELS)


def owner_instruction(message: str) -> str | None:
    """The one owner line. Quoted lines and source headers are not instructions."""
    own = []
    normalized = message.replace("\r\n", "\n").replace("\r", "\n")
    for line in normalized.strip().split("\n"):
        line = line.strip()
        if not line or _quoted_line(line) or _source_header(line):
            continue
        own.append(line)
    if len(own) != 1 or own[0].endswith(("?", "？")):
        return None
    return own[0]


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

    def turn(self, payload, key, principal):
        action_key = _action_key(key)
        self._require_snapshot(payload, action_key, principal)
        language = payload.language if payload.language in _TEXT else "en"
        if getattr(payload, "voice_steer", False) is True:
            return self._steer_snapshot(payload, action_key, principal, language)
        parsed = parse_changed_goal(payload.message)
        if parsed is None:
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
        return _reply(language, "recovered", admitted=True, recovered=True, run=current)

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
        return _reply(language, "admitted", admitted=True, run=updated)

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
        code = (
            "CONVERSATION_WORK_INTERRUPTED"
            if phase == "before_commit"
            else "CONVERSATION_WORK_RESULT_UNKNOWN"
        )
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


def _action_key(key: str) -> str:
    return "wg/" + hashlib.sha256(key.encode()).hexdigest()


def _steerable(run) -> bool:
    return run.get("state") != "cancelled" and run.get("plan_revision", 2) < 2


def _reply(language, code, *, admitted, recovered=False, run=None):
    body = {
        "mode": "local_rules",
        "kind": "work_goal" if admitted else "clarify",
        "saved": False,
        "admitted": admitted,
        "recovered": recovered,
        "message": _TEXT[language][code].format(goal=(run or {}).get("goal", "")),
    }
    if run is not None and admitted:
        body["work_run_id"] = run["id"]
        body["goal"] = run["goal"]
        body["plan_revision"] = run["plan_revision"]
    return body
