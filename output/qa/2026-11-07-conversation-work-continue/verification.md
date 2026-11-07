# Explicit continue advances one verified offline Work run

7 November 2026. Grok Bot completed this through a Cursor cloud agent. Codex reviews and merges. #89–#92 are already on main (`f2dbb79`). This pull request is stacked on #95 (`cursor/conversation-work-reshow-verified-b9a2`). Merge #95 first, then this pull request. It does not retarget #73, #87, #88, or #94.

## Merge note for Codex

| Order | What it added |
|---|---|
| #89, already on main | Explicit text goal change steers one current Work run |
| #90, already on main | Held-out phrases and a reviewed voice snapshot use that steer |
| #91, already on main | The voice review screen updates one current run |
| #92, already on main | The same turn shows one verified offline result |
| #95, merge first | A later turn in the same conversation re-reads that verified file |
| This pull request | An explicit continue ask advances that run once and shows the verified file |

## What was read

Full files: [AGENTS.md](../../../AGENTS.md), [handoff.md](../../../handoff.md), [conversation-work.md](../../../desk-companion/docs/conversation-work.md), `desk-companion/backend/desk/conversation_work.py`, and the prior [QA](../2026-11-07-conversation-work-reshow/verification.md).

Sections, not the whole history: [product.md](../../../product.md) through the current-requirements section, [decision-log.md](../../../decision-log.md) from the 6 November goal-change entries through the 7 November re-show entry, [work-log.md](../../../work-log.md) from the 6 November goal-change entries, [START_HERE_NEXT_CHAT.md](../../../START_HERE_NEXT_CHAT.md), [personal-agent-research-index.md](../../../research/personal-agent-research-index.md) section 4, [desktop-conversation.md](../../../desk-companion/docs/desktop-conversation.md) goal-change section, [application-work.md](../../../desk-companion/docs/application-work.md) remaining boundary, [agent-loop-handoff.md](../../../desk-companion/docs/agent-loop-handoff.md) persistent-application section, [pr5-integration.md](../../../desk-companion/docs/pr5-integration.md) November gate, and [voice-work.md](../../../desk-companion/docs/voice-work.md) controls section.

Implementation read for this slice: `ConversationWork.turn` and the follow-up read, `AgentRunService.advance_one`, `_deterministic`, `_publish`, `_finish`, and `action`, plus the assistant reply cache in `TextAssistant._scoped_message`.

## Scope

Chosen: after one verified offline result is already in a conversation, an explicit owner line can continue that same run. `Continue this work.` and `继续这项工作。` take one offline step when a single current run is clear. `Continue work <run id>.` and `继续工作 <run id>。` name the run when several current runs exist. The reply shows the verified Markdown the same way #92 and #95 do.

Not chosen: a new task store, queue, schema migration, or approval tool; a provider call; a computer job or proposal; live mailbox, calendar, or merchant accounts; payment; Pi; retargeting Codex drafts #73, #87, #88, or #94.

## Result

`parse_work_continue` accepts one closed list. `ConversationWork.turn` calls `AgentRunService.refresh_owner` and then one `advance_one` for that run. `refresh_owner` binds the current owner session and privacy revision, which steer already does, and does not change the goal. On this deterministic fixture the next step is the outcome check: the run becomes `succeeded`, and the reply reads the Markdown already published. `result.verified` is true only for `status: verified` and `verification: byte_readback`.

Checked behavior:

- English and Chinese continue asks return the same artifact id, the `Goal:` line, and `result.verified` / `verification: byte_readback`. The executor is called once. Repeating the operation id does not call it again. A different message with that operation id conflicts. No provider call and no second report.
- A status question re-reads the file and does not step. A quote, a wrapped quote, a mail header, a second line, a question, a `Goal:` draft, a near phrase, and a new conversation do not step.
- Several current runs and no run id do not choose. Naming the shown run steps only that run. Naming a run this conversation did not show does not step it.
- Closing the stream is not the success receipt. Recovery uses the same operation id and does not step again.
- An interruption before the executor commits is not success and can be retried once with the same operation id. An unknown result after the step is committed is recovered with the same id and is not stepped again.
- A finished run and a cancelled run get a clear reply and are not reopened. A failed step and an unverified read are not shown as success.
- Another login receives 404 for that conversation and does not get the goal line on a fresh turn. A paired device receives 403. Full access creates no job and no proposal. The task `next_step` stays unchanged.

No browser session. The owner-visible sentence is the assistant message the existing conversation already renders.

## Commands

From `desk-companion/`. `uv sync --group dev` created `.venv`, and `npm ci` in `frontend/` supplied the frontend tests. Neither install is part of the change. The full backend command is `python -m pytest` so the project root can import `scripts`.

```sh
uv run --no-sync ruff check backend/desk/conversation_work.py backend/desk/agent_runs.py tests/test_conversation_work.py
uv run --no-sync python -m pytest tests/test_conversation_work.py tests/test_integration_acceptance.py -q
uv run --no-sync python -m pytest -q --tb=line
```

From `frontend/`:

```sh
npm test
npx tsc --noEmit
```

Results: ruff passed. Conversation-work collected 79 tests and they passed. Integration acceptance collected 7 tests and they passed in the same command, 86 passed in 42.57s. The full backend suite was 1967 passed and 1 failed, in 390.64s. Frontend tests passed 328. Typecheck passed. Paid provider calls: 0. GitHub Actions: not run.

## Pre-existing failure

`tests/test_public_capture_transport.py::test_public_unicast[::ffff:93.184.216.34]` failed. `is_public_unicast` rejects the address. This branch does not modify `public_capture_transport.py` or that test. Mailbox, shopping, offline calendar, and decide coverage remains inside the 1967 passed tests.

## Docs updated

[handoff.md](../../../handoff.md), [START_HERE_NEXT_CHAT.md](../../../START_HERE_NEXT_CHAT.md), [AGENTS.md](../../../AGENTS.md), [decision-log.md](../../../decision-log.md), [work-log.md](../../../work-log.md), [personal-agent-research-index.md](../../../research/personal-agent-research-index.md), [conversation-work.md](../../../desk-companion/docs/conversation-work.md), [voice-work.md](../../../desk-companion/docs/voice-work.md), [application-work.md](../../../desk-companion/docs/application-work.md), [agent-loop-handoff.md](../../../desk-companion/docs/agent-loop-handoff.md), [pr5-integration.md](../../../desk-companion/docs/pr5-integration.md), [desktop-conversation.md](../../../desk-companion/docs/desktop-conversation.md), and this file.
