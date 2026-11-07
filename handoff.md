# Group 2 · Conversation-work re-show, synced with main after #94

7 November 2026. This review branch is `cursor/conversation-work-reshow-verified-b9a2`. Codex reviews and merges #95, then #96 (`cursor/conversation-work-continue-once-51ee`). Drafts #73, #87, and #88 stay untouched. #94 is already merged and is not reopened. Paid tests stay closed. Local verification only. No CI.

## Current state

A goal change that already showed one verified offline Work result can be asked about again in that same conversation. The later turn shows the same Markdown `Goal:` line. `result.verified` is true only when the file status is `verified` and `verification` is `byte_readback`. The offline executor does not run again. No provider is called.

[PR94](https://github.com/tantalum666/FYP/pull/94) is on main as `a9fb6da54a6ef8fabd7c8739ce97b34b663708b9`; that tree equals the reviewed `7043510a` head. Pi source `d40457fe` is activated. The USD1 live round is closed: 31 requests, USD0.37970163, zero unknown receipts. FYP still has no native mail sender. JD account takeover remains main's separate next product step and is not this pull request. [Live QA](output/qa/2026-11-07-live-agent-eval/verification.md). [Publication receipt](output/qa/2026-11-07-live-agent-eval/publication-receipt.json).

## Done

- Closed asks in [follow-up.json](desk-companion/fixtures/conversation-work/follow-up.json) re-read the verified file through `ConversationWork` and `AgentRunService`. No new store, queue, migration, or approval tool.
- Unverified, failed, and interrupted results are not shown as success. The original operation id can still show a `before_result` outcome once.
- Another login cannot open the conversation. A paired device receives 403. Full access creates no job and no proposal. The same operation id is idempotent. A stream close is not the success receipt.
- Current main is merged in with a normal merge commit. The re-show call still passes the open conversation into `ConversationWork.turn`. OpenAI text defaults, the browser/VPS code, and the live-agent records from #94 stay.

## Evidence

[Slice QA](output/qa/2026-11-07-conversation-work-reshow/verification.md). [Sync QA](output/qa/2026-11-07-conversation-work-stack-sync/verification.md). [Contract](desk-companion/docs/conversation-work.md). Ruff passed. Conversation-work and integration acceptance: 75 passed. Full backend pytest: 2042 passed, 2 failed. One failure is the existing `test_public_unicast[::ffff:93.184.216.34]`. The other, `test_restart_runs_only_the_approved_folder_job`, fails the same way on current `origin/main` and is not a change from this merge. Frontend tests 330 passed. `tsc --noEmit` passed. Paid provider calls: 0.

## Not done

The later ask does not continue the run. That continuation is #96, stacked on this branch. Real accounts, payment, native mail, and a new paid round stay separate. This sync does not implement JD owner takeover.

## One next step

Codex merges #95, then #96: an explicit owner request that continues the same Work run after the verified report, still offline and without a provider call.
