"""The ordinary chat projection of an owner-confirmed Google Calendar refresh."""

import re
from datetime import UTC, datetime

from .store import DomainError

KIND = "google_calendar_refresh"
QUERY = {"service": "google_calendar", "view": "last_refresh"}
COUNTS = ("updated", "removed", "kept", "unavailable", "conflicts", "unresolved")


def asks_last_refresh(message):
    if not re.search(r"(?:google|谷歌)\s*(?:calendar|日[历曆])", message, re.I):
        return False
    return bool(
        re.search(
            r"\bwhat(?:['’]s| has| was| just| recently| got)*\s+(?:changed|updated|refreshed)\b"
            r"|\bwhat (?:did|changes|updates)\b[^?!.]{0,85}\b(?:change|update|refresh|sync|made|did|were)\b"
            r"|\b(?:summari[sz]e|show|when was)\b[^?!.]{0,85}\b(?:last|latest|recent)\s+(?:refresh|sync)\b"
            r"|(?:更新|刷新|同步|变更|變更)了?(?:什么|什麼|甚麼|哪些)"
            r"|(?:什么|哪些|什麼)(?:变化|變化|改动|更新|變更|变更)",
            message,
            re.I,
        )
    )


def projection(runtime, principal):
    if not principal or principal.get("kind") != "owner":
        raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
    status = runtime.google.import_status(principal.get("session"))
    summary = status["last_refresh"]
    return {
        **QUERY,
        "review_version": status["review_version"],
        "last_refresh_ref": status["last_refresh_ref"],
        "last_refresh": (
            {k: summary[k] for k in ("at", *COUNTS) if k in summary} if summary else None
        ),
    }


def reference(result):
    # Only this opaque reference enters the durable reply cache and the retry path.
    return {
        "mode": "local_rules", "kind": KIND, "refresh_ref": result.get("last_refresh_ref"),
        "saved": False,
    }


def present(runtime, principal, stored, language):
    zh = language == "zh"
    reply = {
        "mode": "local_rules",
        "kind": "reply",
        "saved": False,
        "message": "当前没有可查看的 Google 日历刷新确认记录。"
        if zh else "There’s no confirmed Google Calendar refresh available in this session.",
    }
    if not stored.get("refresh_ref"):
        return reply
    result = projection(runtime, principal)
    if stored["refresh_ref"] != result["last_refresh_ref"]:
        return reply
    row = result["last_refresh"]
    at = datetime.fromisoformat(row["at"]).astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
    if "unavailable" in row:
        unavailable = row["unavailable"]
        details = [
            f"其中 {unavailable} 项在 Google 暂不可用" if zh else f"{unavailable} unavailable from Google"
        ]
        other = row["unresolved"] - unavailable
        if other:
            details.append(f"另有 {other} 项未能核实" if zh else f"{other} otherwise unresolved")
    else:
        details = [
            "旧记录未单列其中在 Google 不可用的数量" if zh else "unavailable copies weren’t counted separately"
        ]
        if row["unresolved"]:
            details.append(f'{row["unresolved"]} 项未能核实' if zh else f'{row["unresolved"]} unresolved')
    if row["conflicts"]:
        details.append(f'{row["conflicts"]} 项有冲突' if zh else f'{row["conflicts"]} conflicting')
    updated, removed, kept = row["updated"], row["removed"], row["kept"]
    message = (
        f"Google 日历副本上次于 {at} 确认刷新，更新 {updated} 项、移除 {removed} 项、"
        f"保留 {kept} 项（{'，'.join(details)}）。"
        if zh
        else f"Your last confirmed Google Calendar refresh ({at}) updated {updated} local "
        f"{'copy' if updated == 1 else 'copies'}, "
        f"removed {removed} and kept {kept} ({', '.join(details)})."
    )
    return {
        **reply, "message": message,
        "google_refresh_scope": {
            "review_version": result["review_version"], "last_refresh_ref": result["last_refresh_ref"],
        },
    }
