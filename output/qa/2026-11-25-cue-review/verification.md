# Verification — home initiative cue → Conversation Sources

**Branch** `cursor/cue-review-conversation-e853` · **base** `origin/main` `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d` · **Grok Bot** completed this slice and left the PR open for Codex. No merge, CI trigger, deploy, paid model, live mailbox, or external send.

## Premise

See [premise.md](premise.md). On main, the home Alice initiative cue only offered Got it. This slice adds View in conversation so the owner can expand Conversation and read Sources before dismissing.

## Reading scope

AGENTS.md, product.md, handoff.md, decision-log / work-log tails, proactive-research.md, ui-copy.md, research/2026-11-18-always-on-personal-agent.md, AliceCheckIn / AssistantPanel / InitiativeMessages / AliceHome on main. Open #158–#163 heads checked (no product stack).

## Evidence tier

Local real Chrome at 1440 and 320 on owned ports `5210` / `8850`, fixture owner login, fake initiative generate. Frontend source contract. Not live-account or paid-model acceptance.

## What changed

- Alice home initiative cue: **View in conversation** beside **Got it**; expands Conversation via existing `onExpandedChange` (does not dismiss).
- Finding article `aria-label` Proactive suggestion for the visible card (test + a11y); Sources / Got it unchanged. No Follow up / snooze on this branch.

## Commands and results

```text
npx tsx --test tests/cue-review-conversation.test.ts
→ 1 passed

PYTHONPATH=backend pytest -vv tests/test_cue_review_ui.py
→ 1 passed (Chrome 1440 + 320; horizontal overflow ≤ 1px)

npx tsc --noEmit -p frontend → exit 0
npx vite build → exit 0
git diff --check → exit 0
```

Screenshots: [desktop-1440.png](desktop-1440.png) · [narrow-320.png](narrow-320.png) — Conversation open with Sources · 2 and Got it after View in conversation.

Full multi-package suite not run; change is home-cue UI wiring plus one Playwright journey.

## Honest limits

- Does not stack #161 Follow up or #163 Remind me later.
- Does not prove live Gmail citations or paid research; fixture finding only.
- Cue Got it still dismisses without opening Sources (intentional quick path).
