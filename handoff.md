# Group 2 · Second continue while a verified Work run is still open

10 November 2026. This review branch is `cursor/conversation-work-second-continue-3b11`, stacked on #96 (`cursor/conversation-work-continue-once-51ee`), which is stacked on #95 (`cursor/conversation-work-reshow-verified-b9a2`). Codex merges #95, then #96, then this pull request. Drafts #73, #87, and #88 stay untouched. #94 is already merged and is not reopened. Paid tests stay closed. Local verification only. No CI.

## Current state

After one explicit continue, a later explicit ask in the same conversation takes one more offline step only while that same Work run is still open. `Continue this work.` or `继续这项工作。` is its own operation. A repeated operation id does not step twice. A finished, cancelled, failed, or expired run stays closed, and the reply says so without a new job or proposal. A status question only re-reads the verified file. `result.verified` is true only for `status: verified` and `verification: byte_readback`.

On the deterministic run with no requested change, the first step is still the outcome check and the run becomes `succeeded`. A requested change leaves the run open at `waiting_review` after that first step. The next ask, after the owner decides, takes one review step through the existing executor. No provider is called.

[PR94](https://github.com/tantalum666/FYP/pull/94) is on main as `a9fb6da54a6ef8fabd7c8739ce97b34b663708b9`. Pi source `d40457fe` is activated. The USD1 live round is closed. JD account takeover remains main's separate next product step and is not this pull request. [Live QA](output/qa/2026-11-07-live-agent-eval/verification.md).

## Done

- A second explicit continue reuses `ConversationWork` and one `AgentRunService.advance_one`. No new store, queue, migration, or approval tool.
- Several current runs still require the run id, and that ask does not step. A run this conversation did not show is not found.
- The same operation id steps at most once. An interruption before the executor commits can be retried once. An unknown result and a closed stream are recovered with that id and are not stepped again.
- Another login cannot open the conversation. A paired device receives 403. Full access creates no job and no proposal on a closed run.
- Mailbox, shopping, and offline calendar decide branches are unchanged.

## Evidence

[Second-continue QA](output/qa/2026-11-10-conversation-work-second-continue/verification.md). [Contract](desk-companion/docs/conversation-work.md). Counts are in that QA. Paid provider calls: 0.

## Not done

Real accounts, payment, native mail, and a new paid round stay separate. This pull request does not implement JD owner takeover. A run that is waiting on the owner does not step until that decision.

## One next step

Codex merges #95, then #96, then this pull request.
