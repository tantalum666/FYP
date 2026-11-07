# Group 2 · Pi software handoff

7 November 2026. #89–#92 are already on main (`f2dbb79`). This review branch is `cursor/conversation-work-reshow-verified-b9a2`. Codex reviews and merges. Draft #94 (`codex/openai-computer-use-20261106`) and drafts #73, #87, and #88 stay untouched. Paid tests stay closed. Local verification only. No CI.

## Current state

A goal change that already showed one verified offline Work result can be asked about again in that same conversation. The later turn shows the same Markdown `Goal:` line. `result.verified` is true only when the file status is `verified` and `verification` is `byte_readback`. The offline executor does not run again. No provider is called.

Pi still runs the previous passwordless/application checkpoint. Only red-LED investigation is paused. No live mailbox, calendar, or merchant account is connected.

## Done

- Closed asks in [follow-up.json](desk-companion/fixtures/conversation-work/follow-up.json) re-read the verified file through `ConversationWork` and `AgentRunService`. No new store, queue, migration, or approval tool.
- Unverified, failed, and interrupted results are not shown as success. The original operation id can still show a `before_result` outcome once.
- Another login cannot open the conversation. A paired device receives 403. Full access creates no job and no proposal. The same operation id is idempotent. A stream close is not the success receipt.

## Evidence

[QA](output/qa/2026-11-07-conversation-work-reshow/verification.md). [Contract](desk-companion/docs/conversation-work.md). Ruff passed. Conversation-work 68 passed. Integration acceptance 7 passed. Full backend pytest: 1956 passed, 1 failed. The failure is the existing `test_public_unicast[::ffff:93.184.216.34]`. Frontend tests 328 passed. `tsc --noEmit` passed. Paid provider calls: 0.

## Not done

The later ask does not continue the run. Real accounts, payment, Pi update, and paid model comparison stay separate.

## One next step

Add an explicit owner request that continues the same Work run after the verified report, still offline and without a provider call. Leave Codex draft #94 on its own OpenAI browser track.
