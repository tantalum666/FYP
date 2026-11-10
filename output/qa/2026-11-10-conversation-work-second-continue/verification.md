# Second continue while a verified Work run is still open

10 November 2026. Grok Bot completed this through a Cursor cloud agent. Codex reviews and merges. Merge #95 first, then #96, then [#99](https://github.com/tantalum666/FYP/pull/99). It does not retarget #73, #87, #88, or #94. #94 is already merged and is not reopened.

## Merge note for Codex

| Order | What it added |
|---|---|
| #95, merge first | A later turn in the same conversation re-reads the verified file |
| #96, merge second | An explicit continue ask advances that run once |
| #99, merge third | A later explicit ask advances one more step only while that run is still open |

## What was read

Full files: [AGENTS.md](../../../AGENTS.md), [START_HERE_NEXT_CHAT.md](../../../START_HERE_NEXT_CHAT.md), [handoff.md](../../../handoff.md), [conversation-work.md](../../../desk-companion/docs/conversation-work.md), `desk-companion/backend/desk/conversation_work.py`, and the prior [continue QA](../2026-11-07-conversation-work-continue/verification.md).

Sections, not the whole history: [product.md](../../../product.md) current-requirements section, [decision-log.md](../../../decision-log.md) from the 6 November goal-change entries through the 7 November stack sync, [work-log.md](../../../work-log.md) from the 7 November continue entries, [personal-agent-research-index.md](../../../research/personal-agent-research-index.md) section 4 and the dated engineering updates, [desktop-conversation.md](../../../desk-companion/docs/desktop-conversation.md) goal-change paragraph, [application-work.md](../../../desk-companion/docs/application-work.md) remaining boundary, [agent-loop-handoff.md](../../../desk-companion/docs/agent-loop-handoff.md) persistent-application paragraph, [pr5-integration.md](../../../desk-companion/docs/pr5-integration.md) November gate, and [voice-work.md](../../../desk-companion/docs/voice-work.md) controls paragraph.

Implementation read for this slice: `ConversationWork._continue`, `AgentRunService.advance_one`, `_deterministic`, `_publish`, `_finish`, `_propose`, `_review`, and `refresh_owner`. `JobService` was read for its terminal states, including `expired`, so this slice would not add a second job queue. Nested `AGENTS.md` files: only the repository root.

## Scope

Chosen: each explicit continue remains one owner operation and one `AgentRunService.advance_one` on the run this conversation already showed. A later operation takes the next step only while that run is still open. A run with no requested change still finishes on the first step. A run that already requested a task change stays at `waiting_review` after that step; after the owner decides, the next ask takes one existing review step. A finished, cancelled, failed, or expired run gets a plain reply and does not call the executor. Expired means the run deadline has passed.

Not chosen: a new task store, queue, schema migration, or approval tool; a provider call; a computer job; live mailbox, calendar, or merchant accounts; payment; Pi; retargeting Codex drafts #73, #87, #88, or #94.

## Result

`parse_work_continue` is unchanged. `ConversationWork._continue` still calls `refresh_owner` and then one `advance_one` when the selected run is open. The same operation id does not call it twice. `result.verified` is still true only for `status: verified` and `verification: byte_readback`.

Checked over HTTP:

- English then Chinese: the first continue on a run with a requested change proposes that change and leaves the run at `waiting_review`. A status question re-reads the file and does not step. Before the owner decides, the second ask is not success. After the decision, that same operation id takes one review step, stays open, and a repeat does not step again. A different message with that operation id conflicts. A further ask takes the outcome check and the run becomes `succeeded`. The next ask says it was not started again.
- A finished run's later English and Chinese asks say so. Full access does not create a job or a proposal.
- A cancelled run, a failed run, and a run past its deadline each get a plain reply. None of those asks call the executor or create a job or a proposal.
- `before_continue` on the second ask is not success and the same operation id can then step once. `after_continue` is not success; recovery reads the file and does not step again. Closing the stream is not the receipt.
- Another login receives 404. A paired device receives 403. Neither steps the open run. The owner can still take the next step afterward.
- Several current runs and no run id do nothing. A run id this conversation did not show is not stepped.

No browser session. The owner-visible sentence is the assistant message the existing conversation already renders.

## Commands

From `desk-companion/`. `uv sync --group dev` created `.venv`, and `npm ci` in `frontend/` supplied the frontend tests. Neither install is part of the change. The full backend command is `python -m pytest` so the project root can import `scripts`.

```sh
uv run --no-sync ruff check backend/desk/conversation_work.py tests/test_conversation_work.py
uv run --no-sync python -m pytest tests/test_conversation_work.py tests/test_integration_acceptance.py -q
uv run --no-sync python -m pytest -q --tb=line
```

From `frontend/`:

```sh
npm test
npx tsc --noEmit
```

Results: ruff passed. Conversation-work and integration acceptance: 93 passed. The full backend suite was 2060 passed and 2 failed, in 414.10s. Frontend tests passed 330. Typecheck passed. Paid provider calls: 0. GitHub Actions: not run.

## Pre-existing failures

`tests/test_public_capture_transport.py::test_public_unicast[::ffff:93.184.216.34]` failed. `is_public_unicast` rejects the address. This branch does not modify that transport check.

`tests/test_folder_jobs.py::test_restart_runs_only_the_approved_folder_job` failed with `expired` where the test expects `succeeded`. That is the fixed fixture clock against the wall clock. It is not changed here. Mailbox, shopping, offline calendar, and decide coverage remains inside the 2060 passed tests.

## Docs updated

[handoff.md](../../../handoff.md), [START_HERE_NEXT_CHAT.md](../../../START_HERE_NEXT_CHAT.md), [AGENTS.md](../../../AGENTS.md), [decision-log.md](../../../decision-log.md), [work-log.md](../../../work-log.md), [personal-agent-research-index.md](../../../research/personal-agent-research-index.md), [conversation-work.md](../../../desk-companion/docs/conversation-work.md), [voice-work.md](../../../desk-companion/docs/voice-work.md), [application-work.md](../../../desk-companion/docs/application-work.md), [agent-loop-handoff.md](../../../desk-companion/docs/agent-loop-handoff.md), [pr5-integration.md](../../../desk-companion/docs/pr5-integration.md), [desktop-conversation.md](../../../desk-companion/docs/desktop-conversation.md), and this file.
