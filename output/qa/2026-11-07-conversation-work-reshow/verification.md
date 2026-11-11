# Later ask re-shows one verified offline result

7 November 2026. Grok Bot completed this through a Cursor cloud agent. Codex reviews and merges. #89–#92 are already on main (`f2dbb79`). This pull request is against main. It does not re-open that stack and it does not retarget #73, #87, #88, or #94.

## Merge note for Codex

| Already on main | What it added |
|---|---|
| #89 | Explicit text goal change steers one current Work run |
| #90 | Held-out phrases and a reviewed voice snapshot use that steer |
| #91 | The voice review screen updates one current run |
| #92 | The same turn shows one verified offline result |

This pull request is the next slice #92 named: a later turn in the same conversation asks about that work and is shown the same verified file again. The assistant completed the implementation. Codex reviews and merges.

## What was read

Full files: [AGENTS.md](../../../AGENTS.md), [handoff.md](../../../handoff.md), [conversation-work.md](../../../desk-companion/docs/conversation-work.md), `desk-companion/backend/desk/conversation_work.py`, and the prior [QA](../2026-11-06-conversation-work-verified-result/verification.md).

Sections, not the whole history: [product.md](../../../product.md) through the 30 October application section, [decision-log.md](../../../decision-log.md) from the 6 November goal-change entries, [work-log.md](../../../work-log.md) from the 6 November goal-change entries, [START_HERE_NEXT_CHAT.md](../../../START_HERE_NEXT_CHAT.md), [personal-agent-research-index.md](../../../research/personal-agent-research-index.md) section 4, [desktop-conversation.md](../../../desk-companion/docs/desktop-conversation.md) goal-change section, [application-work.md](../../../desk-companion/docs/application-work.md) remaining boundary, [agent-loop-handoff.md](../../../desk-companion/docs/agent-loop-handoff.md) persistent-application section, [pr5-integration.md](../../../desk-companion/docs/pr5-integration.md) November gate, and [voice-work.md](../../../desk-companion/docs/voice-work.md) controls section.

Implementation read for this slice: `TextAssistant._scoped_message`, the in-memory `Conversations` owner scope, `remember_exchange`, `AgentRunService.advance_one` / `detail` / `session`, `ArtifactService.read`, and the assistant reply cache.

## Scope

Chosen: after one verified offline result is already in a conversation, a later owner turn in that same conversation that asks about the work re-reads that Markdown file. The `Goal:` line is the same line. `result.verified` is true only for `status: verified` and `verification: byte_readback`.

Not chosen: a new task store, queue, schema migration, or approval tool; a second executor run; a provider call; a computer job or proposal; live mailbox, calendar, or merchant accounts; payment; Pi; retargeting Codex drafts #73, #87, #88, or #94.

## Result

`parse_work_followup` accepts one closed list of asks. `ConversationWork.turn` finds the verified reply already stored for this conversation and reads that artifact again through `ArtifactService.read`. It does not call `AgentRunService.advance_one`. Contract: [conversation-work.md](../../../desk-companion/docs/conversation-work.md).

Checked behavior:

- English and Chinese asks in the same conversation return the same artifact id, the same `Goal:` line, and `result.verified` / `verification: byte_readback`. Repeating the operation id returns the stored reply. A different message with that operation id conflicts. No provider call and no second advance.
- A question outside the list, a quote, a mail header, a second line, and a new conversation do not re-show the file.
- Closing the follow-up stream is not the success receipt. Recovery uses the same operation id and does not advance the run.
- A reviewed voice steer’s verified file is re-shown by a later text ask in that conversation.
- Another login receives 404 for that conversation and does not get the goal line on a fresh turn. A paired device receives 403. Full access creates no job and no proposal.
- An interrupted result is not re-shown and does not run the executor. The original operation id can still show the result once. A failed result is not re-shown. A file that no longer reads back as verified is `CONVERSATION_WORK_RESULT_UNVERIFIED`, not a success, and restoring the read shows the same file without a second publish.

No browser session. The owner-visible sentence is the assistant message the existing conversation already renders.

## Commands

From `desk-companion/`. `uv sync --group dev` created `.venv`, and `npm ci` in `frontend/` supplied the frontend tests and the integration stream check. Neither install is part of the change. The full backend command is `python -m pytest` so the project root can import `scripts`.

```sh
uv run --no-sync ruff check backend/desk/conversation_work.py backend/desk/text_ai.py tests/test_conversation_work.py
uv run --no-sync python -m pytest tests/test_conversation_work.py tests/test_integration_acceptance.py -q
uv run --no-sync python -m pytest -q --tb=line
```

From `frontend/`:

```sh
npm test
npx tsc --noEmit
```

Results: ruff passed. Conversation-work collected 68 tests and they passed inside the full backend run. Integration acceptance collected 7 tests and they passed inside that same run. The full backend suite was 1956 passed and 1 failed, in 372.72s. Frontend tests passed 328. Typecheck passed. Paid provider calls: 0. GitHub Actions: not run.

The first integration run, before `npm ci`, failed only `test_interrupted_assistant_stream_recovers_once_through_sse` because `@capacitor/core` was not installed. After `npm ci`, that test passed in the full suite.

## Pre-existing failure

`tests/test_public_capture_transport.py::test_public_unicast[::ffff:93.184.216.34]` failed. `is_public_unicast` rejects the address. This branch does not modify `public_capture_transport.py` or that test. Mailbox, shopping, offline calendar, and decide coverage remains inside the 1956 passed tests.

## Docs updated

[handoff.md](../../../handoff.md), [START_HERE_NEXT_CHAT.md](../../../START_HERE_NEXT_CHAT.md), [AGENTS.md](../../../AGENTS.md), [decision-log.md](../../../decision-log.md), [work-log.md](../../../work-log.md), [personal-agent-research-index.md](../../../research/personal-agent-research-index.md), [conversation-work.md](../../../desk-companion/docs/conversation-work.md), [voice-work.md](../../../desk-companion/docs/voice-work.md), [application-work.md](../../../desk-companion/docs/application-work.md), [agent-loop-handoff.md](../../../desk-companion/docs/agent-loop-handoff.md), [pr5-integration.md](../../../desk-companion/docs/pr5-integration.md), [desktop-conversation.md](../../../desk-companion/docs/desktop-conversation.md), and this file.
