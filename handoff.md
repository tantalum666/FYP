# Group 2 · Continue one verified Work run, synced with main after #94

7 November 2026. This review branch is `cursor/conversation-work-continue-once-51ee`, stacked on #95 (`cursor/conversation-work-reshow-verified-b9a2`). Codex reviews and merges #95 first, then this branch. Drafts #73, #87, and #88 stay untouched. #94 is already merged and is not reopened. Paid tests stay closed. Local verification only. No CI.

## Current state

After a verified offline Work report is in a conversation, the owner can explicitly ask to continue that same run. `Continue this work.` or `继续这项工作。` takes one `AgentRunService.advance_one` step when a single current run is clear. Several current runs require the run id. The reply shows the verified Markdown `Goal:` line. No provider is called.

On this deterministic run that one step is the outcome check. The run becomes `succeeded` and the same verified file is shown. A later continue does not start it again. A cancelled run is not reopened. A status question only re-reads the verified file.

[PR94](https://github.com/tantalum666/FYP/pull/94) is on main as `a9fb6da54a6ef8fabd7c8739ce97b34b663708b9`; that tree equals the reviewed `7043510a` head. Pi source `d40457fe` is activated. The USD1 live round is closed: 31 requests, USD0.37970163, zero unknown receipts. FYP still has no native mail sender. JD account takeover remains main's separate next product step and is not this pull request. [Live QA](output/qa/2026-11-07-live-agent-eval/verification.md). [Publication receipt](output/qa/2026-11-07-live-agent-eval/publication-receipt.json).

## Done

- Explicit continue phrases in [continue.json](desk-companion/fixtures/conversation-work/continue.json) go through `ConversationWork` and the existing offline executor. No new store, queue, migration, or approval tool.
- Status questions, quotes, source headers, a new conversation, and an unnamed ask when several runs are current do not take the step.
- The same operation id steps at most once. An interruption before the executor commits can be retried once. An unknown result is recovered with that id and is not stepped again. A stream close is not the receipt.
- Unverified, failed, and interrupted results are not shown as success. Another login cannot open the conversation. A paired device receives 403. Full access creates no job and no proposal.
- The updated #95 branch, including its normal merge of current main, is merged here. OpenAI text defaults, the browser/VPS code, and the live-agent records from #94 stay.

## Evidence

[Continue QA](output/qa/2026-11-07-conversation-work-continue/verification.md). [Sync QA](output/qa/2026-11-07-conversation-work-stack-sync/verification.md). [Contract](desk-companion/docs/conversation-work.md). Ruff passed. Conversation-work and integration acceptance: 86 passed. Full backend pytest: 2053 passed, 2 failed. One failure is the existing `test_public_unicast[::ffff:93.184.216.34]`. The other, `test_restart_runs_only_the_approved_folder_job`, fails the same way on current `origin/main` and is not a change from this merge. Frontend tests 330 passed. `tsc --noEmit` passed. Paid provider calls: 0.

## Not done

A run that is still open after one step does not yet accept a second explicit step. Real accounts, payment, native mail, and a new paid round stay separate. This sync does not implement JD owner takeover.

## One next step

Codex merges #95, then this pull request.
