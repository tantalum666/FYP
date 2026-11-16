"""One current, owner-visible cue. Existing task/nudge/posture stores own state."""

from datetime import datetime
from zoneinfo import ZoneInfo

from .workspace_data import is_quiet


def current_checkin(runtime, principal, tasks, posture):
    if principal.get("kind") != "owner" or not runtime.personal_context.visible(principal):
        return None
    prefs = runtime.data.preferences()
    with runtime.store.connection() as conn:
        zone = ZoneInfo(runtime.store.settings(conn)["timezone"])
    now = runtime.store.clock().astimezone(zone)
    if prefs["proactivity"] == "off" or is_quiet(prefs, now):
        return None
    feedback = posture.get("feedback")
    if (
        feedback
        and posture["connected"]
        and posture["source"] == "live"
        and posture["preferences"]["enabled"]
        and not posture["paused"]
        and now.timestamp() >= posture["snooze_until"]
    ):
        age = now.timestamp() - feedback["created_at"]
        if 0 <= age < (20 if feedback["outcome"] == "adjusted" else 120) and feedback[
            "outcome"
        ] in {"waiting", "adjusted", "still_deviated"}:
            return {
                "id": f"posture-{feedback['created_at']}-{feedback['outcome']}",
                "kind": "posture",
                "position": feedback["kind"],
                "outcome": feedback["outcome"],
            }
    movement = posture.get("movement_feedback")
    if (
        movement
        and movement.get("source") == "live"
        and movement["outcome"] == "notice"
        and posture["connected"]
        and posture["preferences"]["enabled"]
        and not posture["paused"]
        and now.timestamp() >= posture["snooze_until"]
        and 0 <= now.timestamp() - movement["created_at"] < 180
    ):
        return {
            "id": f"movement-{movement['created_at']}",
            "kind": "posture",
            "position": "movement",
            "outcome": "notice",
        }
    for task in tasks.get("attention", []):
        if not task.get("redacted") and task.get("followup") and not task["paused"]:
            return {
                "id": "task-" + task["followup"]["id"],
                "kind": "task",
                "task_id": task["id"],
                "version": task["version"],
                "title": task["title"],
                "next_step": task["next_step"]
                or next((step["title"] for step in task.get("steps", []) if not step["done"]), ""),
                "waiting_for": task["waiting_for"],
                "status": task["status"],
                "due_at": task.get("due_at"),
            }
    for nudge in runtime.nudges.listing()["nudges"]:
        if (
            nudge["state"] != "open"
            or datetime.fromisoformat(nudge["created_at"].replace("Z", "+00:00"))
            .astimezone(zone)
            .date()
            != now.date()
        ):
            continue
        if nudge["kind"] == "morning_brief" and not prefs["daily_brief_enabled"]:
            continue
        if nudge["kind"] == "evening_check" and not prefs["evening_check_enabled"]:
            continue
        if not tasks.get("followed_count"):
            continue
        return {
            "id": nudge["id"],
            "kind": nudge["kind"],
            "open_count": tasks["followed_count"],
            "tasks": [
                {"title": t["title"], "due_at": t.get("due_at")}
                for t in tasks.get("followed_preview", [])
                if not t.get("redacted")
            ][:2],
        }
    return None
