"""Read-only owner status. The report is an allowlist: secrets are not copied in."""

import html
import platform

from .calendar import iso

# Same ceiling as TextAssistant.enrich_one: follow-up rows from this UTC date.
FOLLOWUP_DAILY_CAP = 20
_PROVIDERS = {"none", "qwen", "gemini"}
_HEALTH = {"idle", "ready", "retrying_after_error"}


def diagnostics_report(runtime, service_version: str) -> dict:
    config = runtime.text_ai.config
    provider = config.provider if config.provider in _PROVIDERS else "none"
    today = iso(runtime.store.clock())[:10]
    with runtime.store.connection() as conn:
        used = conn.execute(
            "SELECT COUNT(*) FROM text_ai_usage WHERE purpose='followup' AND at>=?",
            (today,),
        ).fetchone()[0]
    ticks = {}
    for name, status in runtime.worker_health.items():
        ticks[str(name)] = status if status in _HEALTH else "retrying_after_error"
    backup = runtime.backups.health
    return {
        "versions": {"service": service_version, "python": platform.python_version()},
        "provider": {
            "configured": bool(config.valid()),
            "name": provider,
            "background": bool(config.valid() and config.background),
            "cap_used": used,
            "cap_limit": FOLLOWUP_DAILY_CAP,
        },
        "backup": runtime.backups.describe(),
        "database": {"bytes": runtime.store.path.stat().st_size},
        "scheduler": {
            "ticks": ticks,
            "backup": backup if backup in _HEALTH else "retrying_after_error",
        },
    }


def diagnostics_html(report: dict) -> str:
    rows = [
        ("Service", report["versions"]["service"]),
        ("Python", report["versions"]["python"]),
        ("Provider", report["provider"]["name"]),
        ("Provider configured", "yes" if report["provider"]["configured"] else "no"),
        ("Background advice", "yes" if report["provider"]["background"] else "no"),
        ("Daily cap used", f"{report['provider']['cap_used']} / {report['provider']['cap_limit']}"),
        ("Last backup", report["backup"]["last_at"] or "none"),
        ("Backup file", report["backup"]["file_name"] or "none"),
        ("Backup bytes", report["backup"]["bytes"] if report["backup"]["bytes"] is not None else "none"),
        ("Backups retained", report["backup"]["retained"]),
        ("Database bytes", report["database"]["bytes"]),
        ("Backup tick", report["scheduler"]["backup"]),
    ]
    body = "".join(
        f"<dt>{html.escape(str(label))}</dt><dd>{html.escape(str(value))}</dd>" for label, value in rows
    )
    ticks = "".join(
        f"<li>{html.escape(str(name))}: {html.escape(str(status))}</li>"
        for name, status in sorted(report["scheduler"]["ticks"].items())
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Desk Companion diagnostics</title>
</head>
<body>
<h1>Diagnostics</h1>
<p>Read only. This page does not show keys, passwords, or tokens.</p>
<dl>{body}</dl>
<h2>Scheduler ticks</h2>
<ul>{ticks or "<li>none yet</li>"}</ul>
</body>
</html>
"""
