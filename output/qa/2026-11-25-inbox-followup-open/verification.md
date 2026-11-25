# Verification — Inbox task follow-up opens the cited task

**Branch** `cursor/inbox-followup-open-e853` · **base** `origin/main` `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d` · **Grok Bot** completed this slice and left the PR open for Codex. No merge, CI trigger, deploy, paid model, live mailbox, or external send.

## Premise

See [premise.md](premise.md). Gap: Inbox follow-up receipts offered View tasks (list only) and notices lacked `task_id`. Home Open task is open #173 and was not stacked.

## Reading (this slice)

AGENTS.md, product.md, handoff.md, ui-copy.md, task-tracking.md, research/2026-11-18-always-on-personal-agent.md (skim), NoticeInbox / notify Notice / tasks.tick follow-up publish, open #170/#173 patterns.

## Change

- Follow-up `Notice` payloads include `task_id` for the cited task.
- Inbox follow-up receipt: **Open task** → `goPage("tasks", taskId)`; does not dismiss.
- Loopback allowlist ports 5201 / 8842.
- Docs: ui-copy, task-tracking, handoff, decision-log, work-log.

## Checks run

| Check | Result |
|---|---|
| `node --test tests/inbox-followup-open.test.ts` | pass |
| `pytest -vv tests/test_inbox_followup_open.py` | pass |
| `pytest -vv tests/test_inbox_followup_open_ui.py` | pass (Chrome 1440 + 320) |
| `tsc --noEmit` / `vite build` / `git diff --check` | pass / pass / clean |

## Evidence tier

**Local real Chrome** on owned ports 5201 (Vite) / 8842 (API). Fixture login + rule follow-up. Screenshots: [desktop-1440.png](desktop-1440.png), [narrow-320.png](narrow-320.png). Notice stays open after Open task. Not live mailbox or paid model.

## Not claimed

Merge, GitHub CI, deploy, Pi/hardware, live accounts, payment, runtime provider/model/A3 change.
