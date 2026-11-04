# Group 2 Current Handoff

3 November 2026. **Offline mailbox journey is implemented and locally tested.** It is not a real Gmail or Outlook acceptance. PR5 remains merged (reviewed head `112f912` as main `9b655e1`); [publication receipt](output/qa/2026-10-31-pr5-repair/publication.json). This slice branches from main `dac527b386c268caa96d9388d0c11d206b4f6856`.


## Current implementation

Retained Work/source/artifact/watch/routine services compose with current TaskService, JobService, PermissionService and owner_memories. Alice/mobile/Omni and the real office executor remain authoritative. Old A1 and demo-record application code are superseded and remain in Git history. Normal ephemeral conversations and explicitly saved threads have separate endpoints/IDs. [Compatibility/migration contract](desk-companion/docs/pr5-integration.md), [research/current product gaps](research/personal-agent-research-index.md).

Mac migration identity, canonical fact visibility/conversion, deletion retry barriers, Work approval after redaction, bounded JSON, transport privacy and lifecycle cleanup are repaired. Old user stores require explicit stopped-store upgrades; no real data was migrated. A schema1 fixture made by unmodified main preserved all45 original tables through schema3, including fact history/expiry/aliases/policy/unapproved jobs.

## Evidence

Final backend1,686 and frontend300 checks, Ruff, TypeScript/Vite, lock metadata and model/image hashes passed. Actual web Work produced files, waited for a typed task-note approval, then independently verified the same task effect. The watch created one review and stayed quiet after acknowledgment. Actual download SHA and restart readback match; phone393px reads the note and preserves Alice. Explicit saved-chat create/approve/refresh uses the same facts and one history rendering. No provider call, native/keyboard or hardware acceptance was claimed.

3 November 2026: the 28 October Codex integration lessons now have a standing pytest harness, [integration acceptance](desk-companion/docs/integration-acceptance.md). Seven checks pass on main `dac527b386c268caa96d9388d0c11d206b4f6856`. This does not change the mailbox gate below.

The isolated localhost:8832 fixture service was stopped and test tabs/viewports cleared. Prior runtime/API8854/Vite5191/application VM and existing keys/data in older worktrees were not changed; recheck before reuse. All paid rounds remain closed; no CI or Pi work.

## Offline mailbox slice (3 November)

Owner instruction for this slice: offline fixtures only. No real mailbox, no credentials, no paid API. Open [PR79](https://github.com/tantalum666/FYP/pull/79) (not merged). [Contract](desk-companion/docs/mailbox-journey.md), [fixtures](desk-companion/fixtures/mailbox/README.md), [QA](output/qa/2026-11-03-mailbox-offline/verification.md).

Done: one fixture thread maps to one existing task; duplicate, out-of-order, interrupt/restart, revoke, and disconnect leave a consistent cursor; sourced drafts cite mail id and observation time and confirm only through the existing owner proposal path (`send` stays false); notices fire only on a meaningful change, an approaching deadline, or a decision. A notice held for quiet hours is delivered by the existing rules tick when quiet hours end. Portable JSON backup includes the cursor and ingest state, validates it before import, and a restored mailbox does not create a second task on the next sync. HTTP tests exercise the task list, notice inbox, proposal decisions, and backup preview/apply routes.

Not done: live account authorization and sending. Reconnect after revoke or disconnect is out of scope.

## One next step

Obtain an explicit real-account scope before connecting Gmail or Outlook. Do not start shopping, travel booking, or a paid model round from this slice.
Implement the authorized-mailbox journey through the current task/Work core: incrementally ingest messages, map a thread to the same task, produce sourced advice/drafts and notify only on meaningful change. Start with offline duplicate/out-of-order/revoke/restart fixtures; obtain an explicit real-account scope before connecting a mailbox. Reuse the recovered [research](research/personal-agent-research-index.md); do not create another task/job/memory core or restart a paid budget.

## Offline shopping fixtures (3 November 2026)

A separate slice maps offline cart, price, stock and shipment fixtures onto the existing task, one paused Work run per tracked product or order, owner-confirmed drafts and notices. Duplicate, out-of-order, disconnect, revoke and restart stay on that same task. The owner portable backup now includes the shopping cursor and subject mapping; restoring it and syncing the same fixture does not open a second task. No store account, payment or checkout. Contract: [shopping-fixtures.md](desk-companion/docs/shopping-fixtures.md). The mailbox journey above is unchanged.
## Offline calendar fixture (3 November 2026)

Branch `cursor/offline-calendar-journey-3bf1` maps local schedule fixtures through TaskService, the calendar event store, proposals, and NoticeInbox. One event or series stays one task. Quiet-hour notices wait for the existing rules tick. Portable JSON backup restores the cursor so the next sync keeps that task. Advice does not accept invites or send RSVPs. Mailbox stays on PR #79; shopping stays on its own branch. No Google, Outlook, or paid call. [Contract](desk-companion/docs/offline-calendar-journey.md).

## One next step

Review this offline calendar fixture PR. Do not connect Google or Outlook. Mailbox (PR #79) and shopping remain separate. A live mailbox or calendar account still needs an explicit scope before any real connection.
