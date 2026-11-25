# Verification — open cited memory from finding Sources

**Branch** `cursor/source-open-memory-e853` · **base** `origin/main` `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d` · **Grok Bot** completed this slice and left the PR open for Codex. No merge, CI trigger, deploy, paid model, live mailbox, or external send.

## Premise

See [premise.md](premise.md). On main, memory citations in finding Sources were plain labels. This slice adds Open memory for the existing cited fact.

## Reading scope

AGENTS.md, product.md, handoff.md, decision-log / work-log tails, proactive-research.md, ui-copy.md, research/2026-11-18-always-on-personal-agent.md, InitiativeMessages / AliceHome / App / MemoryPanel / MemoryFactList / initiative_sources on main. Open #158–#166 heads checked (no product stack; #166 is Open task only).

## Evidence tier

Local real Chrome at 1440 and 320 on owned ports `5195` / `8836` (added to the loopback origin allowlist). Fake initiative + fixture owner login. Not live-account or paid-model acceptance.

## What changed

- Finding Sources: memory citations offer **Open memory:** · fact text → `goPage("memory", id)`.
- Memory focuses that fact (`data-memory-id`, `aria-current`).
- Does not dismiss the finding, create a follow-up, or send mail.
- Finding `aria-label` Proactive suggestion for the visible card.

## Commands and results

```text
npx tsx --test tests/source-open-memory.test.ts → 1 passed
PYTHONPATH=backend pytest -vv tests/test_source_open_memory_ui.py → 1 passed
npx tsc --noEmit -p frontend → exit 0
npx vite build → exit 0
git diff --check → exit 0
```

Screenshots: [desktop-1440.png](desktop-1440.png) · [narrow-320.png](narrow-320.png) — Memory list with the cited January 2025 contract fact focused after Open memory; finding still pending when Conversation reopens.

## Honest limits

- Does not stack #161 Follow up (new task) or #163–#166 (including Open task).
- Task/calendar citations stay labels this slice (task open lives on #166).
- Fixture finding only; not live mailbox or paid model.
