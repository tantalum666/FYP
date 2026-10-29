# Group 2 Current Handoff

29 October 2026, Asia/Hong_Kong. Current checkpoint: **shared assistant permissions/action UX and verified task/file/phone continuity**. Workspace `/Users/tantalum/.codex/worktrees/grok-reviewed-fixes/FYP`, branch `codex/assistant-permissions-20261029`, based on open [PR64](https://github.com/tantalum666/FYP/pull/64) head `b02d92b132a83dccb4674abb25f33d7613fbcd28`. Published as draft [PR65](https://github.com/tantalum666/FYP/pull/65), verified implementation commit `4c6b8911ae19862a44b9d68450aaed4f2615ccdb`; [receipt](output/qa/2026-10-29-assistant-permissions/publication.json). Both PR64 and PR65 remain open/unmerged.

## Completed

- Web and App share contextual ProposalActionCard/JobActionCard and Ask first / Full access controls by the composer and in Settings. Phone Calendar/Tasks/More are full-screen pages with back/draft protection; Alice remains the home. Task results continue in the same selected-task conversation.
- Independent PermissionService defaults to Ask. New eligible owner requests may use versioned Full access; old pending work, background/internal/paired requests and physical outputs do not acquire that grant. Automatic provenance differs from a one-time user click. Revocation fences delayed Full requests and queued automatic execution.
- Fixed all local file commands' task binding, terminal-task fresh read-only verification, current task-result refresh and crash-after-effect confirmation recovery. Real web task→approved file→independent readback→API restart/lost-response recovery→phone verification/cancel/progress/manual completion passed without duplicate writes.
- Inline response recovery preserves unrelated unsent text and does not block permission revocation. Forgetting now preserves content-free retired request identities, so old retries cannot restore the original user text to a new RAM conversation or recreate a fact.
- [QA](output/qa/2026-10-29-assistant-permissions/verification.md):489 backend,89 frontend, Ruff, TypeScript/Vite and frontend formatting; actual desktop/393/320px phone checks, Chinese labels, short viewport and independent API/file proofs. Current source rebuilt/installed/launched on iPhone17Pro/iOS26.5 with new permission entry visible. **Native taps/soft keyboard remain unaccepted:** the fresh mirror Plan tap did not produce a transition.

## Current preview and preserved data

- Browser `http://localhost:5190/`, phone `http://localhost:5190/?surface=phone`; Vite exec19902. API `127.0.0.1:8833`, exec64926. Recheck listeners before reuse; IDs are a recorded checkpoint, not a permanent service guarantee.
- Isolated runtime `desk-companion/.runtime/task-journey-20261028`; fictional task/files only. Providersnone, background AI/extraction/push/Linux executor off, fixed local-note executor on. Final policy **Ask, version5**; [readback](output/qa/2026-10-29-assistant-permissions/final-preview-readback.json). Use localhost for Vite to avoid prior127.0.0.1 cookie collision.
- Simulator UDID `F57B6381-6448-434C-AE61-A2663F3458A7`, bundle `dev.group2.deskcompanion`, launch-only API8833 override. Saved native server/TLS policy unchanged. Live mirror `http://localhost:3200/`, original exec56630. No other simulator touched.
- Previous API8832/Vite5191 processes were checked and stopped; their42-fact memory runtime remains intact. Prior dirty worktrees, original school files, historical QA and private backups are preserved. No migration or data deletion.

## Boundaries and entry points

**Local validation only; no GitHub CI.** Pi paused; old paid budgets closed; no live media or external account work. Qwen remains the measured baseline, alternatives stay open. Full access here means already connected software capabilities, not arbitrary OS access, new model spend or hardware control.

Read [permission contract](desk-companion/docs/assistant-permissions.md), [maintenance](desk-companion/docs/software-maintenance.md), [delivery gates](desk-companion/docs/delivery-readiness.md) and current QA. The [first journey evidence](output/qa/2026-10-28-task-journey/reading-record.json) precedes the owner's UX correction; its old nested layout is superseded. Grok20–59/#60 integration is already merged throughPR61; do not redo it or merge unrelated PRs.

## One next step

Define and validate one mixed calendar/memory/file task with an offline/scripted provider: partial success, permission revocation between effects and restart/recovery from existing receipts. The current HTTP loop still ends after one effect-producing tool; do not assume a complete multi-step autonomous agent or add a second queue/transcript store. Native keyboard acceptance remains a separate open gate.
