# Verification — Inbox Dismiss clears bound initiative findings

**Branch** `cursor/inbox-initiative-dismiss-e853` · **base** `origin/main` `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d` · **Grok Bot** completed this slice and left the PR open for Codex. No merge, CI trigger, deploy, paid model, live mailbox, or external send.

## Premise

See [premise.md](premise.md). On main, Inbox Dismiss for an initiative notice only marked the notice dismissed; pending findings and the home cue remained (`BUG_CONFIRMED` on pristine main).

## Reading scope

AGENTS.md, product.md, handoff.md, decision-log / work-log tails, proactive-research.md, ui-copy.md, research/2026-11-18-always-on-personal-agent.md, notify.py / NoticeInbox / ReminderDialog on main. Open #158–#164 heads checked (no product stack).

## Evidence tier

API fixture + local real Chrome at 1440 and 320 on owned ports `5193` / `8834` (added to the loopback origin allowlist). Fake initiative + fixture owner login. Not live-account or paid-model acceptance.

## What changed

- `Notifier.dismiss`: for `kind=initiative`, also mark pending `initiative_findings` with that `notice_id` dismissed and clear browser/device notice rows (heal + match Got it cleanup).
- Regression: Got it on one of two batched findings still leaves the other and keeps the batch notice open.
- Allowlist ports `:5193`, `:8834` for this harness.

## Commands and results

```text
PYTHONPATH=backend pytest -q tests/test_initiative.py \
  tests/test_notify.py::test_open_notice_pages_keep_history_after_one_dismissal
→ 24 passed

PYTHONPATH=backend pytest -vv tests/test_inbox_initiative_dismiss_ui.py
→ 1 passed (Chrome 1440 + 320)

ruff check backend/desk/notify.py tests/test_initiative.py tests/test_inbox_initiative_dismiss_ui.py → clean
npx tsc --noEmit -p frontend → exit 0
npx vite build → exit 0
git diff --check → exit 0
```

Screenshots: [desktop-1440.png](desktop-1440.png) · [narrow-320.png](narrow-320.png) — Inbox **All caught up.** after Dismiss; Conversation no longer shows the finding.

## Honest limits

- Does not stack #161 Follow up, #163 snooze, or #164 cue View in conversation.
- Does not prove live Gmail or paid research; fixture finding only.
- Inbox empty copy is ReminderDialog’s All caught up (NoticeInbox unmounts at total 0).
