# Verification — Inbox morning/evening check-in opens the cited surface

**Branch** `cursor/nudge-inbox-review-e853` · **base** `origin/main` `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d` · **Grok Bot** completed this slice and left the PR open for Codex. No merge, CI trigger, deploy, paid model, live mailbox, or external send.

## Premise

See [premise.md](premise.md). On main, morning briefing and evening check-in Inbox receipts had no View action to Today or Tasks.

## Reading scope

AGENTS.md, product.md, handoff.md, decision-log / work-log tails, task-tracking.md, ui-copy.md, research/2026-11-18-always-on-personal-agent.md, NoticeInbox / nudges / App on main. Open #158–#169 heads checked (no product stack).

## Evidence tier

Local real Chrome at 1440 and 320 on owned ports `5197` / `8838` (added to the loopback origin allowlist). Rule-based evening check-in + fixture owner login. Not live-account or paid-model acceptance.

## What changed

- Inbox **Morning briefing** → **View today** → Today page.
- Inbox **Evening check-in** → **View tasks** → Tasks page.
- Does not dismiss the receipt.

## Commands and results

```text
npx tsx --test tests/nudge-inbox-review.test.ts → 1 passed
PYTHONPATH=backend pytest -vv tests/test_nudge_inbox_review_ui.py → 1 passed
npx tsc --noEmit -p frontend → exit 0
npx vite build → exit 0
git diff --check → exit 0
```

Screenshots: [desktop-1440.png](desktop-1440.png) · [narrow-320.png](narrow-320.png) — Tasks page after Inbox View tasks from Evening check-in; notice remains open.

## Honest limits

- Does not stack #164/#165/#169 initiative inbox journeys.
- Chrome acceptance covers evening → Tasks; morning → Today is the same wiring covered by the frontend contract.
- Rule nudge only; not live mailbox or paid model.
