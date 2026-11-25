# Verification — withdrawn finding when Sources change

**Branch** `cursor/finding-withdrawn-e853` · **base** `origin/main` `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d` · **Grok Bot** completed this slice and left the PR open for Codex. No merge, CI trigger, deploy, paid model, live mailbox, or external send.

## Premise

See [premise.md](premise.md). On main, changing cited evidence dropped the finding from Conversation with no owner-facing receipt.

## Reading scope

AGENTS.md, product.md, handoff.md, decision-log / work-log tails, proactive-research.md, ui-copy.md, research/2026-11-18-always-on-personal-agent.md, initiative current/advance, InitiativeMessages, daily_checkin on main. Open #158–#170 heads checked (no product stack; #161 stale Follow up only).

## Evidence tier

Local real Chrome at 1440 and 320 on owned ports `5198` / `8839`. Fake initiative + fixture owner login + memory deletion API. Not live-account or paid-model acceptance.

## What changed

- Pending findings that no longer match (and obsolete rows) appear as **withdrawn** in Conversation.
- Copy: Sources changed; nothing was sent. Got it clears.
- Home cue does not promote withdrawn findings.
- Delivery (`undelivered`) still only uses live matching pending findings.

## Commands and results

```text
npx tsx --test tests/finding-withdrawn.test.ts → 1 passed
PYTHONPATH=backend pytest -vv tests/test_initiative.py::test_changed_cited_memory_keeps_finding_visible_as_withdrawn → 1 passed
PYTHONPATH=backend pytest -vv tests/test_finding_withdrawn_ui.py → 1 passed
npx tsc --noEmit -p frontend → exit 0
npx vite build → exit 0
git diff --check → exit 0
```

Screenshots: [desktop-1440.png](desktop-1440.png) · [narrow-320.png](narrow-320.png) — Withdrawn suggestion after cited memory deleted; Got it clears it.

## Honest limits

- Does not stack #161 Follow up stale refusal or #163–#170.
- Does not re-run model research on withdrawal.
- Fixture finding + local memory delete; not live mailbox or paid model.
