"""Quiet-hour outcomes share the notice inbox. Their original records own access."""

import json
from zoneinfo import ZoneInfo

from .calendar import iso
from .store import encode
from .workspace_data import is_quiet


# Only these persisted outcomes have conversation copy. No source text is projected.
OUTCOMES = {
    "shop.completed": ("A shopping payment was verified.", "一笔购物付款已核实。"),
    "shop.partially_refunded": ("A partial shopping refund was verified.", "一笔购物订单的部分退款已核实。"),
    "shop.refunded": ("A shopping refund was verified.", "一笔购物退款已核实。"),
    "shop.reprice": ("A shop changed its quote and needs your review.", "一笔购物报价有变，等你核对。"),
    "shop.cancel_unavailable": ("A merchant could not accept a cancellation.", "商户未能受理一笔撤单。"),
    "shop.refund_review": ("A refund needs merchant review.", "一笔退款需要商户核查。"),
    "shop.refund_retry": ("A shopping cancellation is still unconfirmed.", "一笔购物撤单尚未确认。"),
    "shop.retry": ("A shopping payment is still unconfirmed.", "一笔购物付款仍待核实。"),
    "shop.unverified": ("A shopping receipt could not be verified.", "一笔购物回执未能核实。"),
    "shop.failed": ("A shopping payment failed.", "一笔购物付款失败。"),
    "flight.completed": ("A flight booking was confirmed.", "一笔航班预订已确认。"),
    "flight.reprice": ("A fare changed and needs your review.", "一笔机票报价有变，等你核对。"),
    "flight.stopped": ("A flight booking was stopped.", "一笔航班预订已停止。"),
    "flight.manual": ("A flight booking needs supplier review.", "一笔航班预订需要供应商核查。"),
    "flight.failed": ("A flight booking failed.", "一笔航班预订失败。"),
    "flight.unverified": ("A flight booking could not be verified.", "一笔航班预订未能核实。"),
    "flight.submit_unknown": ("A flight submission is still unconfirmed.", "一笔航班预订的提交结果仍待核实。"),
    "work.succeeded": ("A work run finished.", "一项工作已完成。"),
    "work.partial": ("A work run finished with some requirements unmet.", "一项工作已结束，仍有要求未达成。"),
    "work.waiting_input": ("A work run has a question for you.", "一项工作有问题等你回答。"),
    "work.waiting_review": ("A work run is ready for your review.", "一项工作等你审核。"),
    "work.blocked": ("A work run needs attention before it can continue.", "一项工作遇到阻碍，需要处理。"),
}


def _commerce_outcome(kind, row):
    state = row["state"]
    if state == "completed" and row.get("cancel_unavailable"):
        state = "cancel_unavailable"
    code = f"{kind.lower()}.{state}"
    if row.get("approved") is None or code not in OUTCOMES:
        return None, None
    if state == "partially_refunded":
        return code, (row.get("receipt") or {}).get("refunded_minor")
    if state == "reprice":
        # Renewing a deadline alone does not change the fare awaiting a decision.
        if kind == "FLIGHT":
            question = row.get("question") or {}
            return code, (question.get("round"), question.get("old"), question.get("new"))
        return code, row["quote"]["terms"]
    return code, None


def observe_commerce(runtime, db, kind, original, row):
    current = _commerce_outcome(kind, row)
    if current == _commerce_outcome(kind, json.loads(original["data"])):
        return
    row.pop("quiet_update", None)
    if _record(
        runtime, db, f"{kind.lower()}/{row['id']}", row["_serial"] + 1, original["owner"], current[0]
    ):
        row["quiet_update"] = True


def _record(runtime, db, source, revision, login, code):
    """Retire the old outcome and tell the passive surface whether to stay silent."""
    db.execute("DELETE FROM notice_inbox WHERE source=?", (source,))
    if code not in OUTCOMES:
        return False
    now = runtime.store.clock()
    settings = runtime.store.settings(db)
    prefs = runtime.data.preferences(db)
    if (
        settings["hide_private"]
        or prefs["proactivity"] == "off"
        or not db.execute(
            "SELECT 1 FROM sessions WHERE token_hash=? AND expires>?", (login, iso(now))
        ).fetchone()
    ):
        return True
    if not is_quiet(prefs, now.astimezone(ZoneInfo(settings["timezone"]))):
        return False
    db.execute(
        "INSERT INTO notice_inbox(id,source,created_at,state,content) VALUES(?,?,?,'open',?)",
        (f"quiet/{source}/{revision}", source, iso(now), encode({"change": code})),
    )
    return True


def observe_work(runtime, db, run, event):
    previous = db.execute(
        "SELECT state,session_hash FROM agent_runs WHERE id=?", (run["id"],)
    ).fetchone()
    state, login = run["state"], run["session_hash"]
    if tuple(previous) == (state, login):
        return
    # Worker checkpoints establish progress. Owner actions and lifecycle/configuration
    # events can retire a previous question but do not announce new work.
    observed = event in {
        "outcome", "question", "proposal", "tool_prepared", "application_wait", "blocked"
    }
    _record(
        runtime, db, "work/" + run["id"], run["version"], login, f"work.{state}" if observed else None
    )


def unread(db, chat, *, notice_ids=None, limit):
    return db.execute(
        """WITH scoped(source) AS (
               SELECT 'shop/' || id FROM sandbox_shop_orders
               WHERE owner=:login AND chat=:chat AND json_extract(data,'$.task_id') IS :task
               UNION ALL
               SELECT 'flight/' || id FROM sandbox_flight_bookings
               WHERE owner=:login AND chat=:chat AND json_extract(data,'$.task_id') IS :task
               UNION ALL
               SELECT 'work/' || id FROM agent_runs
               WHERE session_hash=:login AND (:task IS NULL OR :task IN
                   (SELECT value FROM json_each(agent_runs.data,'$.task_ids')))
           )
           SELECT n.id,json_extract(n.content,'$.change') AS change
           FROM scoped JOIN notice_inbox n USING(source)
           WHERE n.state='open' AND (:ids IS NULL OR n.id IN (SELECT value FROM json_each(:ids)))
           ORDER BY n.created_at DESC,n.id LIMIT :limit""",
        {
            "login": chat.owner,
            "chat": chat.id,
            "task": chat.task_id,
            "ids": None if notice_ids is None else encode(notice_ids),
            "limit": limit,
        },
    ).fetchall()
