"""Admit an ordinary Alice turn into an existing Work run when the goal changes.

The owner names the change in the conversation. This module calls the existing
``AgentRunService`` steer action. It does not create a task, a run, a queue, or
a model approval tool, and it does not call a provider.

An interruption before the steer commits leaves the goal unchanged and is not a
successful reply. A commit whose conversation receipt is lost is recovered by
the same operation id; the goal is not applied a second time.
"""

import hashlib
import re

from .agent_run_schemas import RunAction
from .store import DomainError

_EXPLICIT = re.compile(
    r"^(?:change work|调整工作)\s+([0-9a-f]{32})\s*[:：]\s*(.*)$",
    re.I | re.S,
)
_IMPLICIT = re.compile(
    r"^(?:change the goal|调整目标)\s*[:：]\s*(.*)$",
    re.I | re.S,
)

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
    },
}


def parse_changed_goal(message: str) -> dict | None:
    text = message.strip()
    explicit = _EXPLICIT.match(text)
    if explicit:
        return {"run_id": explicit.group(1).lower(), "goal": explicit.group(2).strip()}
    implicit = _IMPLICIT.match(text)
    if implicit:
        return {"run_id": None, "goal": implicit.group(1).strip()}
    return None


class ConversationWork:
    def __init__(self, runtime):
        self.runtime = runtime
        self.store = runtime.store
        # Offline fixture control. Production leaves this unset. It is not an HTTP field.
        self.offline_interrupt = None

    def turn(self, payload, key, principal):
        parsed = parse_changed_goal(payload.message)
        if parsed is None:
            return None
        self.runtime.agent_runs.session(principal)
        language = payload.language if payload.language in _TEXT else "en"
        goal = parsed["goal"]
        if not goal:
            return _reply(language, "empty", admitted=False)
        if len(goal) > 4000:
            return _reply(language, "too_long", admitted=False)
        action_key = "wg/" + hashlib.sha256(key.encode()).hexdigest()
        existing = self._operation_run(action_key)
        if existing:
            current = self.runtime.agent_runs.detail(existing, principal)["run"]
            if current["goal"] != goal:
                raise DomainError("OPERATION_ID_CONFLICT")
            return _reply(
                language,
                "recovered",
                admitted=True,
                recovered=True,
                run=current,
            )
        resolved = self._resolve(principal, parsed, payload.task_id, language)
        if resolved.get("kind") == "clarify":
            return resolved
        if resolved["goal"] == goal:
            return _reply(language, "unchanged", admitted=False, run=resolved)
        self._fence("before_commit")
        try:
            updated = self.runtime.agent_runs.action(
                resolved["id"],
                RunAction(action="steer", expected_version=resolved["version"], goal=goal),
                action_key,
                principal,
            )["run"]
        except DomainError as error:
            if error.code == "RUN_STEER_NOT_AVAILABLE":
                return _reply(language, "unavailable", admitted=False)
            raise
        self._fence("after_commit")
        return _reply(language, "admitted", admitted=True, run=updated)

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
