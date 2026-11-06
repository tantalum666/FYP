# Held-out phrases and voice-snapshot steering

6 November 2026. Grok Bot completed this through a Cursor cloud agent. Codex reviews and merges. This branch is stacked on PR #89 (`cursor/conversation-work-changed-goal-4bf4`) and should merge after it.

## What was read

Full files: [AGENTS.md](../../../AGENTS.md), [handoff.md](../../../handoff.md), [START_HERE_NEXT_CHAT.md](../../../START_HERE_NEXT_CHAT.md), [conversation-work.md](../../../desk-companion/docs/conversation-work.md), [voice-work.md](../../../desk-companion/docs/voice-work.md), [integration-acceptance.md](../../../desk-companion/docs/integration-acceptance.md), [changed-goal.json](../../../desk-companion/fixtures/conversation-work/changed-goal.json), `conversation_work.py`, `voice_work.py`, and `tests/test_conversation_work.py`.

Sections, not the whole history: [product.md](../../../product.md) lines 1–80, [decision-log.md](../../../decision-log.md) from the 2 November web entry through the 6 November goal-change entry, [work-log.md](../../../work-log.md) from the 2 November conversation entry through the 6 November goal-change entry, [personal-agent-research-index.md](../../../research/personal-agent-research-index.md) sections 1 and 4, [application-work.md](../../../desk-companion/docs/application-work.md) remaining boundary, [agent-loop-handoff.md](../../../desk-companion/docs/agent-loop-handoff.md) persistent-application section, [pr5-integration.md](../../../desk-companion/docs/pr5-integration.md) November gate, [desktop-conversation.md](../../../desk-companion/docs/desktop-conversation.md) goal-change section.

Implementation read for this slice: `text_ai.py` message and stream path, `assistant.py` message model and local-message order, `goals.py` goal draft parse, `agent_runs.py` steer, `voice.py` draft route and config validity, `assistant_routes.py`, `personal_context.py` destinations, `style.py` reply shaping, and `permissions.py` reply application.

## Scope

Chosen: held-out English and Chinese phrases and source layouts outside the changed-goal fixture, including near-misses that must stay off Work, then a reviewed voice snapshot that steers through the same turn.

Not chosen: a new task store, queue, schema migration, or approval tool; a second steer implementation; live mailbox, calendar, or merchant accounts; payment; Pi; paid provider calls; merging Codex drafts #73, #87, and #88; changing the voice review screen, which still starts a new run only.

## Result

`owner_instruction` keeps one owner line. `parse_changed_goal` matches the same four leads. Quoted lines and source headers are not instructions. The fixture is [unseen-variants.json](../../../desk-companion/fixtures/conversation-work/unseen-variants.json). Contract: [conversation-work.md](../../../desk-companion/docs/conversation-work.md).

Checked behavior:

- Mail and calendar labels in English and Chinese steer when the only remaining line is one explicit phrase. A quote after that line stays out of the saved goal.
- A CSV row, a Notes or 备注 field, chatter before the phrase, and two commands do not steer.
- `Goal:` and `目标：` still prepare a task draft and leave the Work goal unchanged.
- Questions, including a command that ends in `?` or `？`, do not steer. Two current runs and no run id do not steer. An explicit run id steers only that run.
- A reviewed snapshot uses `voice_origin_ref` on the ordinary assistant message. `ConversationWork.turn` steers. A forged reference is `VOICE_DRAFT_EXPIRED`. A different message while the snapshot is live is `VOICE_INPUT_CHANGED`.
- `before_commit` leaves the goal unchanged and the same operation id then steers once. `after_commit` is not success. After the snapshot is gone, the same goal recovers and a different goal is `OPERATION_ID_CONFLICT`. A later phrase does not steer again.
- Closing the SSE body is not JSON success. Recovery through the same operation id steers once.
- A quote, a `Goal:` snapshot, and a question snapshot do not steer and do not create a task draft. Chinese snapshot text uses the same turn.
- A paired device receives 403. Full access adds no proposal and no computer job. The task `next_step` stays. No new run is created. A configured generate hook is not called.

No UI file changed, so this pass did not include a browser session.

## Commands

From `desk-companion/`. `uv` was installed and `uv sync --group dev` created `.venv` because this machine had no project environment. `npm ci` in `frontend/` supplied the acceptance stream client. Neither install is part of the change.

```sh
uv run --no-sync ruff check backend/desk/conversation_work.py backend/desk/assistant.py backend/desk/voice_work.py backend/desk/text_ai.py backend/desk/runtime.py tests/test_conversation_work.py
uv run --no-sync pytest tests/test_conversation_work.py -q
uv run --no-sync pytest tests/test_integration_acceptance.py -q
uv run --no-sync pytest tests/test_text_conversation_scope.py tests/test_goals.py tests/test_permissions.py tests/test_shopping_fixtures.py tests/test_mailbox_journey.py tests/test_offline_calendar_journey.py tests/test_agent_runs.py tests/test_voice_work.py -q
```

Results: ruff passed. Conversation-work 47 passed. Integration acceptance 7 passed. The last command passed 141 tests: the previous 97 regressions plus voice-work 44. Paid provider calls: 0. GitHub Actions: not run.

## Docs updated

[handoff.md](../../../handoff.md), [START_HERE_NEXT_CHAT.md](../../../START_HERE_NEXT_CHAT.md), [product.md](../../../product.md), [decision-log.md](../../../decision-log.md), [work-log.md](../../../work-log.md), [personal-agent-research-index.md](../../../research/personal-agent-research-index.md), [conversation-work.md](../../../desk-companion/docs/conversation-work.md), [voice-work.md](../../../desk-companion/docs/voice-work.md), [application-work.md](../../../desk-companion/docs/application-work.md), [agent-loop-handoff.md](../../../desk-companion/docs/agent-loop-handoff.md), [pr5-integration.md](../../../desk-companion/docs/pr5-integration.md), [desktop-conversation.md](../../../desk-companion/docs/desktop-conversation.md), and this file.
