# Verification — Inbox memory follow-up opens Memory

**Branch** `cursor/inbox-memory-followup-e853` · **base** `origin/main` `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d` · **Grok Bot** completed this slice and left the PR open for Codex. No merge, CI trigger, deploy, paid model, live mailbox, or external send.

## Premise

See [premise.md](premise.md). Gap: individual `memory_followup` Inbox receipts had no action despite “Open Memory” copy. Morning check-in already had View memories. Sources Open memory is open #167 and was not stacked.

## Reading (this slice)

AGENTS.md, product.md, handoff.md, ui-copy.md, memory-followups.md, research/2026-11-18-always-on-personal-agent.md (skim), NoticeInbox kinds vs open #158–#174 titles.

## Change

- Inbox `memory_followup` receipt: **View memories** → Memory; does not dismiss.
- Loopback allowlist ports 5202 / 8843.
- Docs: ui-copy, memory-followups, handoff, decision-log, work-log.

## Checks run

| Check | Result |
|---|---|
| `node --test tests/inbox-memory-followup.test.ts` | pass |
| `pytest -vv tests/test_inbox_memory_followup_ui.py` | pass (Chrome 1440 + 320) |
| `tsc --noEmit` / `vite build` / `git diff --check` | pass / pass / clean |

## Evidence tier

**Local real Chrome** on owned ports 5202 (Vite) / 8843 (API). Fixture login + owner-approved memory follow-up. Screenshots: [desktop-1440.png](desktop-1440.png), [narrow-320.png](narrow-320.png). Notice stays open after View memories. Not live mailbox or paid model.

## Not claimed

Merge, GitHub CI, deploy, Pi/hardware, live accounts, payment, runtime provider/model/A3 change. Does not focus a specific memory fact (#167).
