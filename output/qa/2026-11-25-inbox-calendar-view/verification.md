# Verification — Inbox calendar update opens Calendar

**Branch** `cursor/inbox-calendar-view-e853` · **base** `origin/main` `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d` · **Grok Bot** completed this slice and left the PR open for Codex. No merge, CI trigger, deploy, paid model, live Google, live mailbox, or external send.

## Premise

See [premise.md](premise.md). Gap: calendar update Inbox receipts had only Dismiss. Sources Open calendar is open #168 and was not stacked.

## Reading (this slice)

AGENTS.md, product.md, handoff.md, ui-copy.md, offline-calendar-journey.md, research/2026-11-18-always-on-personal-agent.md (skim), NoticeInbox vs open #158–#175 titles, offline calendar notice kinds.

## Change

- Inbox calendar_* receipts: **View calendar** → Calendar; does not dismiss.
- `reviewNotice` / ReminderDialog / Phone plan accept `calendar`.
- Loopback allowlist ports 5203 / 8844.
- Docs: ui-copy, offline-calendar-journey, handoff, decision-log, work-log.

## Checks run

| Check | Result |
|---|---|
| `node --test tests/inbox-calendar-view.test.ts` | pass |
| `pytest -vv tests/test_inbox_calendar_view_ui.py` | pass (Chrome 1440 + 320) |
| `tsc --noEmit` / `vite build` / `git diff --check` | pass / pass / clean |

## Evidence tier

**Local real Chrome** on owned ports 5203 (Vite) / 8844 (API). Fixture login + fixture-published `calendar_deadline` notice (not a live Google sync). Screenshots: [desktop-1440.png](desktop-1440.png), [narrow-320.png](narrow-320.png). Notice stays open after View calendar.

## Not claimed

Merge, GitHub CI, deploy, Pi/hardware, live Google/mailbox, payment, runtime provider/model/A3 change. Does not open a specific Event details sheet (#168).
