# Verification — open cited local calendar from finding Sources

**Branch** `cursor/source-open-calendar-e853` · **base** `origin/main` `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d` · **Grok Bot** completed this slice and left the PR open for Codex. No merge, CI trigger, deploy, paid model, live mailbox, or external send.

## Premise

See [premise.md](premise.md). On main, local calendar citations in finding Sources were plain labels. This slice adds Open calendar for the existing cited occurrence.

## Reading scope

AGENTS.md, product.md, handoff.md, decision-log / work-log tails, proactive-research.md, ui-copy.md, research/2026-11-18-always-on-personal-agent.md, InitiativeMessages / AliceHome / App / initiative_sources / EventDetail on main. Open #158–#167 heads checked (no product stack; #166/#167 cover task/memory only).

## Evidence tier

Local real Chrome at 1440 and 320 on owned ports `5193` / `8834` (added to the loopback origin allowlist). Fake initiative + fixture owner login + fixed store clock. Not live-account or paid-model acceptance.

## What changed

- Finding Sources: local `calendar:{id}:{occurrence_key}` citations offer **Open calendar:** · title → fetch that day → Event details.
- Google preview refs (`calendar:google:…`) stay labels.
- Does not dismiss the finding, create a follow-up, or send mail.
- Finding `aria-label` Proactive suggestion for the visible card.

## Commands and results

```text
npx tsx --test tests/source-open-calendar.test.ts → 1 passed
PYTHONPATH=backend pytest -vv tests/test_source_open_calendar_ui.py → 1 passed
npx tsc --noEmit -p frontend → exit 0
npx vite build → exit 0
git diff --check → exit 0
```

Screenshots: [desktop-1440.png](desktop-1440.png) · [narrow-320.png](narrow-320.png) — Event details for “Fictional vendor visit” after Open calendar; finding still pending when Conversation reopens.

## Honest limits

- Does not stack #161 Follow up or #163–#167 (including Open task / Open memory).
- Google Calendar preview citations stay labels this slice.
- Fixture finding only; not live mailbox, live Google Calendar, or paid model.
