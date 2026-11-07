# Group 2 · Pi software handoff

7 November 2026. #89–#92 are already on main (`f2dbb79`). This review branch is `cursor/conversation-work-continue-once-51ee`, stacked on #95 (`cursor/conversation-work-reshow-verified-b9a2`). Codex reviews and merges #95 first, then this branch. Drafts #73, #87, #88, and #94 stay untouched. Paid tests stay closed. Local verification only. No CI.

## Current state

After a verified offline Work report is in a conversation, the owner can explicitly ask to continue that same run. `Continue this work.` or `继续这项工作。` takes one `AgentRunService.advance_one` step when a single current run is clear. Several current runs require the run id. The reply shows the verified Markdown `Goal:` line. No provider is called.

On this deterministic run that one step is the outcome check. The run becomes `succeeded` and the same verified file is shown. A later continue does not start it again. A cancelled run is not reopened.

Pi still runs the previous passwordless/application checkpoint. Only red-LED investigation is paused. No live mailbox, calendar, or merchant account is connected.

## Done

- Explicit continue phrases in [continue.json](desk-companion/fixtures/conversation-work/continue.json) go through `ConversationWork` and the existing offline executor. No new store, queue, migration, or approval tool.
- Status questions, quotes, source headers, a new conversation, and an unnamed ask when several runs are current do not take the step.
- The same operation id steps at most once. An interruption before the executor commits can be retried once. An unknown result is recovered with that id and is not stepped again. A stream close is not the receipt.
- Unverified, failed, and interrupted results are not shown as success. Another login cannot open the conversation. A paired device receives 403. Full access creates no job and no proposal.

## Evidence

[QA](output/qa/2026-11-07-conversation-work-continue/verification.md). [Contract](desk-companion/docs/conversation-work.md). Ruff passed. Conversation-work 79 passed. Integration acceptance 7 passed. Full backend pytest: 1967 passed, 1 failed. The failure is the existing `test_public_unicast[::ffff:93.184.216.34]`. Frontend tests 328 passed. `tsc --noEmit` passed. Paid provider calls: 0.

## Not done

A run that is still open after one step does not yet accept a second explicit step. Real accounts, payment, Pi update, and paid model comparison stay separate.

## One next step

When one explicit continuation leaves the run open, accept a later explicit ask for the next offline step, still one step per operation id and still with no provider call. Leave a finished or cancelled run closed, and leave Codex draft #94 on its own OpenAI browser track.
