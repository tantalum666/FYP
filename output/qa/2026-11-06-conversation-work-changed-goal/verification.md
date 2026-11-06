# Ordinary text goal change into existing Work

6 November 2026. Grok Bot completed this through a Cursor cloud agent. Codex reviews and merges. Base is current `main` at `abf6387` after the PR74–77 and Grok journey merge.

## What was read

Full files: [AGENTS.md](../../../AGENTS.md), [handoff.md](../../../handoff.md), [START_HERE_NEXT_CHAT.md](../../../START_HERE_NEXT_CHAT.md), [application-work.md](../../../desk-companion/docs/application-work.md), [voice-work.md](../../../desk-companion/docs/voice-work.md), [agent-loop-handoff.md](../../../desk-companion/docs/agent-loop-handoff.md), [agent-runs.md](../../../desk-companion/docs/agent-runs.md), [integration-acceptance.md](../../../desk-companion/docs/integration-acceptance.md), [desktop-conversation.md](../../../desk-companion/docs/desktop-conversation.md), [shopping-fixtures.md](../../../desk-companion/docs/shopping-fixtures.md).

Sections, not the whole history: [product.md](../../../product.md) opening and the current-status table, [decision-log.md](../../../decision-log.md) from 31 October through 4 November, [work-log.md](../../../work-log.md) from the 31 October personal-agent entry through the PR85 closeout, [pr5-integration.md](../../../desk-companion/docs/pr5-integration.md) shared UI and the November gate, [personal-agent-research-index.md](../../../research/personal-agent-research-index.md) sections 1 and 4.

Implementation read for this slice: `text_ai.py` message and stream path, `assistant.py` local message and tool list, `agent_runs.py` create, steer, unknown provider outcome and advance, `goals.py` turn, `runtime.py` service wiring, `permissions.py` reply application, and the conversation task-note path in `assistant.py`.

## Scope

Chosen: offline explicit goal changes from ordinary Alice text into an existing Work run, plus interruption before commit, unknown receipt recovery, and stream close on that path.

Not chosen: a new task store, queue, schema migration, or approval tool; live mailbox, calendar, or merchant accounts; payment; Pi; paid provider calls; merging Codex drafts #73, #87, and #88; unseen phrase or layout variants; voice-snapshot steering.

## Result

`ConversationWork.turn` runs before the model loop. A matching phrase calls `AgentRunService.action` with `steer`. The fixture is [changed-goal.json](../../../desk-companion/fixtures/conversation-work/changed-goal.json). Contract: [conversation-work.md](../../../desk-companion/docs/conversation-work.md).

Checked behavior:

- A mid-flow run keeps its id. One ordinary turn does not steer. The changed goal does, then the same deterministic run finishes with `model_calls == 0`.
- A second run on another task stays unchanged. Two current runs on one task are not guessed. An explicit run id changes only that run.
- The same goal, a bare prefix, a cancelled run, a run that already changed once, a missing run, and a run on another task do not steer.
- `Goal: …` still prepares a new task draft and does not create a Work run.
- `before_commit` returns `CONVERSATION_WORK_INTERRUPTED`, leaves the goal, and the same operation id then admits once.
- `after_commit` returns `CONVERSATION_WORK_RESULT_UNKNOWN` after the steer. A different goal on that operation id conflicts. The original goal recovers once. A later phrase does not steer again.
- Closing the SSE body is not treated as JSON success. Recovery through the same operation id steers once.
- A configured fake provider is not called. Full access adds no proposal and no computer job. The task `next_step` stays. A paired device receives 403.
- No tool named `steer`, `approve`, or `work_goal` was added.

No UI file changed, so this pass did not include a browser session.

## Commands

From `desk-companion/`:

```sh
uv run --no-sync ruff check backend/desk/conversation_work.py backend/desk/text_ai.py backend/desk/runtime.py tests/test_conversation_work.py
uv run --no-sync pytest tests/test_conversation_work.py -q
uv run --no-sync pytest tests/test_integration_acceptance.py -q
uv run --no-sync pytest tests/test_text_conversation_scope.py tests/test_goals.py tests/test_permissions.py tests/test_shopping_fixtures.py tests/test_mailbox_journey.py tests/test_offline_calendar_journey.py tests/test_agent_runs.py -q
```

Results: ruff passed. Conversation-work 9 passed. Integration acceptance 7 passed, including the production stream client after `npm ci` in `frontend/`. Related regressions 97 passed. Paid provider calls: 0. GitHub Actions: not run.

The first integration run failed only because `frontend/node_modules` was absent (`@capacitor/core`). After `npm ci`, the same stream test passed. That dependency install is local and is not part of the change.

## Docs updated

[handoff.md](../../../handoff.md), [START_HERE_NEXT_CHAT.md](../../../START_HERE_NEXT_CHAT.md), [AGENTS.md](../../../AGENTS.md), [product.md](../../../product.md), [decision-log.md](../../../decision-log.md), [work-log.md](../../../work-log.md), [personal-agent-research-index.md](../../../research/personal-agent-research-index.md), [application-work.md](../../../desk-companion/docs/application-work.md), [agent-loop-handoff.md](../../../desk-companion/docs/agent-loop-handoff.md), [pr5-integration.md](../../../desk-companion/docs/pr5-integration.md), [voice-work.md](../../../desk-companion/docs/voice-work.md), [desktop-conversation.md](../../../desk-companion/docs/desktop-conversation.md), and this file.
