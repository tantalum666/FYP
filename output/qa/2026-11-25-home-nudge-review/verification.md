# Verification — Home morning/evening check-in opens Today or Tasks

**Branch** `cursor/home-nudge-review-e853` · **base** `origin/main` `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d` · **Grok Bot** completed this slice and left the PR open for Codex. No merge, CI trigger, deploy, paid model, live mailbox, or external send.

## Premise

See [premise.md](premise.md). Gap: home Alice cue for morning_brief / evening_check offered Got it only on main. Inbox View today/tasks is open #170 and was not stacked. This PR adds the same labels on the home cue only.

## Reading (this slice)

AGENTS.md, product.md, handoff.md, decision-log / work-log tails, ui-copy.md, task-tracking.md (daily check-in), research/2026-11-18-always-on-personal-agent.md (skim for journey gaps), open #164/#170 patterns for wiring, main AliceCheckIn / AliceHome / App.

## Change

- `AliceCheckIn`: View today for morning_brief, View tasks for evening_check; Got it unchanged; no dismiss on View.
- Prop `onReviewSurface` App → AliceHome → ConversationWorkspace → AssistantPanel → AliceCheckIn → `goPage("today"|"tasks")`.
- Loopback allowlist ports 5199 / 8840 for this UI harness.
- Docs: ui-copy, task-tracking, handoff, decision-log, work-log.

## Checks run

| Check | Result |
|---|---|
| `node --test tests/home-nudge-review.test.ts` | pass |
| `npx tsc --noEmit` | pass |
| `npx vite build` | pass |
| `git diff --check` | clean |
| `PYTHONPATH=backend pytest -vv tests/test_home_nudge_review_ui.py` | pass (Chrome 1440 + 320) |

## Evidence tier

**Local real Chrome** on owned ports 5199 (Vite) / 8840 (API). Fixture login + rule evening_check with one open task. Screenshots: [desktop-1440.png](desktop-1440.png), [narrow-320.png](narrow-320.png). Not live mailbox, not paid model, not external send. Navigation does not dismiss the evening_check notice.

## Not claimed

Merge, GitHub CI, deploy, Pi/hardware, live Gmail/Google, payment, runtime provider/model/A3 change.
