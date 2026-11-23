"""Resume retained Work from an explicit owner turn, including after loss of RAM chat."""

from dataclasses import dataclass
from sqlite3 import Row

from .agent_runs import TERMINAL, ChatContinuation
from .calendar import iso
from .personal_context import fingerprint
from .store import DomainError, encode


def _scope(session, chat_id):
    return fingerprint([session, chat_id]) if chat_id else None


def _open(row, now):
    if row["deadline"] <= now:
        return False
    if row["state"] == "paused":
        return row["state_reason"] == "RUN_RUNTIME_STOPPED"
    return row["state"] not in TERMINAL | {"blocked"}


@dataclass
class ResumeSelection:
    rows: list[Row]
    chat_scope: str | None
    named: str | None
    version: int | None
    request_hash: str

    def initial_chat_id(self, key):
        # A retry without a client chat ID rejoins the same empty or live chat.
        # The request hash already includes the original login and task.
        return fingerprint([self.request_hash, key])[:32]

    @property
    def linked(self):
        return [r for r in self.rows if self.chat_scope and r["scope"] == self.chat_scope]

    def candidates(self, target, now):
        if target:
            return [r for r in self.rows if r["id"] == target]
        rows = self.linked or self.rows
        active = [r for r in rows if _open(r, now)]
        return active or (rows if len(rows) == 1 else [])

    def saw_goal(self, row):
        return row["plan_revision"] == 1 or (
            self.chat_scope is not None
            and row["scope"] == self.chat_scope
            and row["seen_revision"] == row["plan_revision"]
        )


class SavedWork:
    def __init__(self, runtime):
        self.runtime, self.store, self.runs = runtime, runtime.store, runtime.agent_runs
        with self.store.connection(write=True) as db:
            # One content-free pointer per retained run. Old runs need no backfill.
            db.execute("""CREATE TABLE IF NOT EXISTS work_chat_links(
                run_id TEXT PRIMARY KEY, scope TEXT, task_id TEXT,
                plan_revision INTEGER NOT NULL, reply_id TEXT)""")
            # A chat awaiting a choice has no selected run to link yet.
            db.execute("""CREATE TABLE IF NOT EXISTS work_chat_prompts(
                scope TEXT PRIMARY KEY, task_id TEXT,
                reply_id TEXT NOT NULL REFERENCES assistant_replies(id) ON DELETE CASCADE)""")

    @staticmethod
    def _link(db, chat, run_id, plan_revision, reply_id):
        scope = _scope(chat.owner, chat.id)
        db.execute(
            "INSERT OR REPLACE INTO work_chat_links VALUES(?,?,?,?,?)",
            (run_id, scope, chat.task_id, plan_revision, reply_id),
        )
        db.execute("DELETE FROM work_chat_prompts WHERE scope=?", (scope,))

    def remember(self, db, chat, key, reply):
        if reply.get("kind") == "work_result" and (reply.get("result") or {}).get(
            "goal"
        ) != reply.get("goal"):
            # A readback of a historical report did not show the revised goal.
            return
        if chat and reply.get("kind") in {"work_resume", "work_result", "work_goal"}:
            if run_id := reply.get("work_run_id"):
                self._link(db, chat, run_id, reply["plan_revision"], key)
            elif reply["kind"] == "work_resume":
                db.execute(
                    "INSERT OR REPLACE INTO work_chat_prompts VALUES(?,?,?)",
                    (_scope(chat.owner, chat.id), chat.task_id, key),
                )

    def forget(self, session, chat_id):
        scope = _scope(session, chat_id)
        with self.store.connection(write=True) as db:
            db.execute("UPDATE work_chat_links SET scope=NULL WHERE scope=?", (scope,))
            db.execute("DELETE FROM work_chat_prompts WHERE scope=?", (scope,))

    def can_reopen(self, payload, principal):
        selection = self.select(payload, principal, {"run_id": None})
        if selection.linked:
            return True
        with self.store.connection() as db:
            return (
                db.execute(
                    """SELECT 1 FROM work_chat_prompts p JOIN assistant_replies a ON a.id=p.reply_id
                   WHERE p.scope=? AND p.task_id IS ?""",
                    (selection.chat_scope, payload.task_id),
                ).fetchone()
                is not None
            )

    def _reserve(self, db, row, key, request_hash):
        self.runs.check_control_limit(db, row["id"])
        binding = f"{request_hash}/{row['version']}"
        db.execute("INSERT INTO agent_run_operations VALUES(?,?,?)", (key, binding, row["id"]))
        return ChatContinuation(key, binding, row["version"])

    def select(self, payload, principal, command):
        session = self.runs.session(principal)
        privacy = encode(self.runtime.personal_context.revision())
        with self.store.connection() as db:
            rows = db.execute(
                """SELECT r.id,r.version,r.state,r.data->>'$.goal' AS goal,
                    r.data->>'$.plan_revision' AS plan_revision,
                    r.data->>'$.deadline' AS deadline,r.data->>'$.state_reason' AS state_reason,
                    l.plan_revision AS seen_revision, CASE WHEN l.task_id IS ? THEN l.scope END AS scope
                FROM agent_runs r LEFT JOIN work_chat_links l ON l.run_id=r.id
                LEFT JOIN assistant_replies a ON a.id=l.reply_id
                WHERE r.session_hash=? AND r.data->'$.privacy_revision'=?
                  AND (l.run_id IS NULL OR
                       (l.scope IS NOT NULL AND (l.reply_id IS NULL OR a.id IS NOT NULL)))
                  AND (? IS NULL OR EXISTS (
                    SELECT 1 FROM json_each(r.data,'$.task_ids') WHERE value=?))
                ORDER BY r.updated_at DESC,r.id""",
                (payload.task_id, session, privacy, payload.task_id, payload.task_id),
            ).fetchall()
        return ResumeSelection(
            rows,
            _scope(session, payload.conversation_id),
            command["run_id"],
            command.get("version"),
            "resume:" + fingerprint([session, payload.model_dump(exclude_defaults=True)]),
        )

    def turn(self, payload, principal, chat, key, selection, *, cached=None):
        zh = payload.language == "zh" or "继续" in payload.message
        with self.runs.lock:
            with self.store.connection() as db:
                receipt = db.execute(
                    "SELECT run_id,request_hash FROM agent_run_operations WHERE id=?", (key,)
                ).fetchone()
            binding = receipt["request_hash"].split("/") if receipt else []
            if receipt and binding[0] != selection.request_hash:
                raise DomainError("OPERATION_ID_CONFLICT")
            claimed = binding[-1:] == ["claimed"]
            target = (
                receipt["run_id"] if receipt else (cached or {}).get("work_run_id", selection.named)
            )
            # Re-read membership, privacy and control state after waiting for another turn.
            now = iso(self.store.clock())
            current = self.select(payload, principal, {"run_id": target})
            rows = current.candidates(target, now)
            if not rows:
                return _reply(
                    "没有可接续的工作。" if zh else "I couldn’t find saved work to continue."
                )
            if len(rows) > 1:
                return _choices(rows, zh)
            row = rows[0]
            if not _open(row, now) and not (claimed and row["state"] in {"succeeded", "partial"}):
                return _closed(row, now, zh)
            if receipt and not claimed and row["version"] != int(binding[1]):
                raise DomainError("VERSION_CONFLICT")
            selected = row
            if receipt is None and cached is None:
                before = selection.candidates(target, now)
                if len(before) != 1 or before[0]["id"] != row["id"]:
                    message = (
                        "可接续的工作已改变，请重新选择。"
                        if zh
                        else "The available work changed. Please choose again."
                    )
                    return _reply(message)
                selected = before[0]
                if selected["version"] != row["version"]:
                    # A later retry with the same key must still refer to the old version.
                    with self.store.connection(write=True) as db:
                        self._reserve(db, selected, key, selection.request_hash)
                    raise DomainError("VERSION_CONFLICT")

            run = self.runs.inspect_continuation(row["id"], principal)
            if claimed:
                return self._result(run, key, zh)
            if selection.version is not None:
                if selection.version != run["version"]:
                    return _changed(run, zh)
            elif receipt is None and not selection.saw_goal(selected):
                return _changed(run, zh)
            if cached and cached.get("plan_revision", run["plan_revision"]) != run["plan_revision"]:
                return _changed(run, zh)
            if waiting := self._waiting(run, zh):
                return waiting
            if cached and cached.get("work_version") == run["version"] and "proposal" not in cached:
                # Re-deliver the same clarification if its first response was lost.
                return cached
            if cached is not None or run["mode"] != "deterministic":
                return _reply(
                    "请在「工作」中查看当前步骤。"
                    if zh
                    else "Open this run in Work to review its current step.",
                    run,
                )

            # Bind even if the first reply is interrupted. Explicitly forgetting
            # this conversation can now retire the pointer before any later retry.
            with self.store.connection(write=True) as db:
                claim = (
                    ChatContinuation(key, receipt["request_hash"], run["version"])
                    if receipt
                    else self._reserve(db, row, key, selection.request_hash)
                )
                self._link(db, chat, run["id"], run["plan_revision"], None)

        # The worker checks this version when reserving the step. Its generation
        # and publication fences remain effective during a concurrent stop or steer.
        if not self.runs.advance_one(run["id"], continuation=claim):
            raise DomainError("CONVERSATION_WORK_RESULT_INTERRUPTED")
        with self.runs.lock:
            run = self.runs.inspect_continuation(run["id"], principal)
            if run["state"] in {"cancelled", "paused", "blocked", "failed"}:
                return _closed(run, iso(self.store.clock()), zh)
            return self._result(run, key, zh)

    def _waiting(self, run, zh):
        if question := run.get("question"):
            return _reply(question + (" 请在「工作」中回答。" if zh else " Answer in Work."), run)
        if run["state"] != "waiting_review":
            return None
        pending = {e.get("proposal_id") for e in run["effects"] if e["state"] == "pending"}
        for proposal in self.runtime.assistant.proposals():
            if proposal["id"] in pending:
                message = (
                    "请核对这份待确认的草稿。" if zh else "Review the pending draft to continue."
                )
                return {**_reply(message, run), "proposal": proposal}
        if run["mode"] == "model":
            return _reply(
                "请在「工作」中核对此步骤的决定。"
                if zh
                else "Review this step’s decision in Work.",
                run,
            )
        return None

    def _result(self, run, key, zh):
        with self.store.connection() as db:
            step = db.execute(
                "SELECT kind,plan_revision FROM agent_steps WHERE id=? AND run_id=?",
                (key, run["id"]),
            ).fetchone()
        if not step:
            raise DomainError("CONVERSATION_WORK_RESULT_UNKNOWN")
        if step["plan_revision"] != run["plan_revision"]:
            return _changed(run, zh)
        waiting = self._waiting(run, zh)
        if waiting:
            return {**waiting, "step_id": key}
        en, cn = {
            "read": ("Read one selected record", "已读取一条选定资料"),
            "compose": ("Prepared the report", "已整理报告"),
            "artifacts": ("Saved and verified the report files", "已保存并核验报告文件"),
            "proposal": ("Prepared the requested draft", "已准备所需草稿"),
            "review_observed": ("Checked the recorded decision", "已核对记录的决定"),
            "outcome": ("Checked the required outputs", "已核对所需产物"),
        }[step["kind"]]
        message = f"「{run['goal']}」：{cn}。" if zh else f"{en} for “{run['goal']}”."
        return {**_reply(message, run), "step_id": key}


def _choices(rows, zh):
    lines = [
        "请选择要继续的工作，回复对应的指令。"
        if zh
        else "Which work did you mean? Reply with its command."
    ]
    command = "继续工作" if zh else "Continue work"
    for row in rows[:3]:
        goal = " ".join(row["goal"].split())[:80]
        lines.append(f"{goal} — {command} {row['id']} v{row['version']}")
    if len(rows) > 3:
        lines.append("其余工作可在「工作」中查看。" if zh else "See Work for the remaining runs.")
    return _reply("\n".join(lines))


def _changed(run, zh):
    goal = run["goal"]
    message = (
        f"当前目标是「{goal}」。要按这个目标继续，请再告诉我。"
        if zh
        else f"The current goal is “{goal}”. Ask again to continue with this goal."
    )
    return _reply(message, run)


def _closed(run, now, zh):
    if run["deadline"] <= now:
        return _reply("这项工作已到期。" if zh else "This work has expired.", run)
    message = (
        "这项工作已停止。详情可在「工作」中查看。"
        if zh
        else f"This work is {run['state']}. See Work for details."
    )
    return _reply(message, run)


def _reply(message, run=None):
    reply = {"mode": "local_rules", "kind": "work_resume", "saved": False, "message": message}
    if run is not None:
        reply.update(
            work_run_id=run["id"], plan_revision=run["plan_revision"], work_version=run["version"]
        )
    return reply
