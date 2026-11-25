# Verification — Home task cue opens the cited task

**Branch** `cursor/home-task-open-e853` · **base** `origin/main` `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d` · **Grok Bot** completed this slice and left the PR open for Codex. No merge, CI trigger, deploy, paid model, live mailbox, or external send.

## Premise

See [premise.md](premise.md). Gap: home Alice task follow-up cue offered Done / Still working / In an hour only. Sources Open task is open #166 and was not stacked. This PR adds Open task on the home cue only.

## Reading (this slice)

AGENTS.md, product.md, handoff.md, decision-log / work-log tails, ui-copy.md, task-tracking.md (follow-ups), research/2026-11-18-always-on-personal-agent.md (skim), open #166 Sources Open task and #172 home morning/evening patterns, main AliceCheckIn / daily_checkin / App.

## Change

- `AliceCheckIn`: Open task for kind `task` when `task_id` is present; Done / Still working / In an hour unchanged; Open task does not complete, snooze, or dismiss.
- Prop `onOpenTask` App → AliceHome → ConversationWorkspace → AssistantPanel → AliceCheckIn → `goPage("tasks", id)`.
- Loopback allowlist ports 5200 / 8841 for this UI harness.
- Docs: ui-copy, task-tracking, handoff, decision-log, work-log.

## Checks run

| Check | Result |
|---|---|
| `node --test tests/home-task-open.test.ts` | pass |
| `./node_modules/.bin/tsc --noEmit` | pass |
| `./node_modules/.bin/vite build` | pass |
| `git diff --check` | clean |
| `PYTHONPATH=backend pytest -vv tests/test_home_task_open_ui.py` | pass (Chrome 1440 + 320) |

## Evidence tier

**Local real Chrome** on owned ports 5200 (Vite) / 8841 (API). Fixture login + rule task follow-up after interval. Screenshots: [desktop-1440.png](desktop-1440.png), [narrow-320.png](narrow-320.png). Not live mailbox, not paid model, not external send. Opening the task leaves status open (not done / not paused).

## Not claimed

Merge, GitHub CI, deploy, Pi/hardware, live Gmail/Google, payment, runtime provider/model/A3 change.
