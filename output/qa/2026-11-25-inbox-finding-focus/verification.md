# Verification — Inbox initiative opens bound finding Sources

**Branch** `cursor/inbox-finding-focus-e853` · **base** `origin/main` `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d` · **Grok Bot** completed this slice and left the PR open for Codex. No merge, CI trigger, deploy, paid model, live mailbox, or external send.

## Premise

See [premise.md](premise.md). On main, Inbox View in conversation only switched pages; it did not focus the bound finding or open Sources.

## Reading scope

AGENTS.md, product.md, handoff.md, decision-log / work-log tails, proactive-research.md, ui-copy.md, research/2026-11-18-always-on-personal-agent.md, NoticeInbox / ReminderDialog / App / InitiativeMessages / initiative notice binding on main. Open #158–#168 heads checked (no product stack; #164 is home cue only; #165 is Dismiss heal).

## Evidence tier

Local real Chrome at 1440 and 320 on owned ports `5196` / `8837` (added to the loopback origin allowlist). Fake initiative + fixture owner login. Not live-account or paid-model acceptance.

## What changed

- Inbox initiative **View in conversation** passes the notice id.
- Conversation expands, focuses the bound finding (`data-finding-id`), opens Sources.
- Does not dismiss the inbox receipt or the finding.
- Pending findings expose `notice_id` for binding.

## Commands and results

```text
npx tsx --test tests/inbox-finding-focus.test.ts → 1 passed
PYTHONPATH=backend pytest -vv tests/test_inbox_finding_focus_ui.py → 1 passed
npx tsc --noEmit -p frontend → exit 0
npx vite build → exit 0
git diff --check → exit 0
```

Screenshots: [desktop-1440.png](desktop-1440.png) · [narrow-320.png](narrow-320.png) — Conversation finding with Sources open after Inbox View in conversation; notice and finding remain pending.

## Honest limits

- Does not stack #164 home cue View, #165 Dismiss heal, or #166–#168 source opens.
- Batched multi-finding notices focus each finding that shares the notice id; Chrome acceptance uses the common single-finding receipt.
- Fixture finding only; not live mailbox or paid model.
