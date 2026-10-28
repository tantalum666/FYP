"""A daily or weekly count of what the desk already stored. No model call.

The owner page may name open goals. The device hears counts only, because a
shared screen should not read private titles aloud. Optional polish is a
separate, capped adapter call and is off unless the owner asks.
"""

from datetime import datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from pydantic import Field

from .notify import Notice
from .schemas import StrictModel
from .store import DomainError
from .workspace_data import is_quiet


class DigestPolish(StrictModel):
    text: str = Field(min_length=1, max_length=500)


def _aware(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=ZoneInfo("UTC"))


def _in_window(value: str | None, start: datetime, end: datetime) -> bool:
    if not value:
        return False
    parsed = _aware(value)
    return parsed is not None and start <= parsed <= end


class DigestService:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store

    def _now(self):
        with self.store.connection() as conn:
            zone = ZoneInfo(self.store.settings(conn)["timezone"])
        now = self.store.clock().astimezone(zone)
        return now, zone

    def view(self, period: str, *, polish: bool = False) -> dict:
        if period not in {"day", "week"}:
            raise DomainError("DIGEST_PERIOD_INVALID", 422)
        now, zone = self._now()
        start = (
            now.replace(hour=0, minute=0, second=0, microsecond=0)
            if period == "day"
            else now - timedelta(days=7)
        )
        start_utc, end_utc = start.astimezone(ZoneInfo("UTC")), now.astimezone(ZoneInfo("UTC"))
        tasks = self.runtime.tasks.listing(include_closed=True)["tasks"]
        done = [
            task["title"]
            for task in tasks
            if task["status"] == "completed" and _in_window(task["updated_at"], start_utc, end_utc)
        ]
        goals = [
            goal["title"]
            for goal in self.runtime.goals.listing()["goals"]
            if goal["state"] != "closed"
        ]
        with self.store.connection() as conn:
            memories = conn.execute(
                "SELECT created_at, updated_at FROM owner_memories WHERE state!='deleted'"
            ).fetchall()
            nudges = conn.execute("SELECT created_at FROM owner_nudges").fetchall()
        memory_changes = sum(
            _in_window(row["created_at"], start_utc, end_utc)
            or _in_window(row["updated_at"], start_utc, end_utc)
            for row in memories
        )
        nudge_count = sum(_in_window(row["created_at"], start_utc, end_utc) for row in nudges)
        label = "Today" if period == "day" else "The last seven days"
        label_zh = "今天" if period == "day" else "最近七天"
        goal_text = ", ".join(goals[:5]) if goals else "none"
        goal_text_zh = "、".join(goals[:5]) if goals else "无"
        spoken_en = (
            f"{label}: {len(done)} task(s) completed, {len(goals)} open goal(s), "
            f"{memory_changes} memory change(s), {nudge_count} check-in(s)."
        )
        spoken_zh = (
            f"{label_zh}：完成事务 {len(done)} 件，未完成目标 {len(goals)} 个，"
            f"记忆变更 {memory_changes} 条，检查 {nudge_count} 次。"
        )
        text_en = spoken_en if self.runtime.data.preferences().get("verbosity") == "brief" else (
            f"{label}: {len(done)} task(s) completed. Open goals: {goal_text}. "
            f"{memory_changes} memory change(s). {nudge_count} check-in(s)."
        )
        text_zh = spoken_zh if self.runtime.data.preferences().get("verbosity") == "brief" else (
            f"{label_zh}：完成事务 {len(done)} 件。未完成目标：{goal_text_zh}。"
            f"记忆变更 {memory_changes} 条。检查 {nudge_count} 次。"
        )
        polished = False
        if polish:
            spoken_en, polished = self._polish(spoken_en)
        return {
            "period": period,
            "timezone": zone.key,
            "completed": len(done),
            "open_goals": goals,
            "memory_changes": memory_changes,
            "check_ins": nudge_count,
            "text_en": text_en,
            "text_zh": text_zh,
            "spoken_en": spoken_en,
            "spoken_zh": spoken_zh,
            "polished": polished,
        }

    def _polish(self, text: str) -> tuple[str, bool]:
        """One optional rewrite. Failure leaves the deterministic sentence."""
        ai = self.runtime.text_ai
        if not ai.config.valid() or ai._purpose_count("digest_polish") >= 2:
            return text, False
        try:
            result = ai.generate(
                "Shorten the desk digest. Do not add events, names, or claims that are not in the text.",
                {"text": text},
                DigestPolish,
                "digest_polish",
            )
        except DomainError:
            return text, False
        return result.text, True

    def announce(self, period: str) -> dict:
        """Queue counts for the device. Quiet hours and proactivity off send nothing."""
        digest = self.view(period)
        now, _zone = self._now()
        prefs = self.runtime.data.preferences()
        quiet = is_quiet(prefs, now) or prefs.get("proactivity") == "off"
        notice = Notice(
            f"digest-{period}-{now.date().isoformat()}",
            "digest",
            "Daily reflection" if period == "day" else "Weekly review",
            "每日反省" if period == "day" else "每周回顾",
            digest["spoken_en"],
            digest["spoken_zh"],
            "This is a count of saved records. It does not add new facts.",
            "这是已保存记录的数量，不会新增事实。",
        )
        deliveries = self.runtime.notify.publish(notice, quiet=quiet)
        return {"digest": digest, "deliveries": deliveries}


def digest_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/digests", dependencies=[Depends(owner)])

    @router.get("")
    def view(period: Literal["day", "week"] = "day", polish: bool = False):
        return runtime.digests.view(period, polish=polish)

    @router.post("/{period}/announcements")
    def announce(period: str, key=Depends(operation_id)):
        del key
        if period not in {"day", "week"}:
            raise DomainError("DIGEST_PERIOD_INVALID", 422)
        return runtime.digests.announce(period)

    return router
