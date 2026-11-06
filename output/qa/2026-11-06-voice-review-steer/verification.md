# Voice review screen steers one current Work run

6 November 2026. Grok Bot completed this through a Cursor cloud agent. Codex reviews and merges. This branch is stacked on PR #90 (`cursor/conversation-work-unseen-voice-4185`). Merge order is #89, then #90, then this PR.

## What was read

Full files: [AGENTS.md](../../../AGENTS.md), [handoff.md](../../../handoff.md), [conversation-work.md](../../../desk-companion/docs/conversation-work.md), [voice-work.md](../../../desk-companion/docs/voice-work.md), `conversation_work.py`, `VoiceWorkPanel.tsx`, `useVoiceWorkHandoff.tsx`, `voiceWork/types.ts`, and the prior [QA](../2026-11-06-conversation-work-unseen-voice/verification.md).

Sections, not the whole history: [product.md](../../../product.md) lines 1–40, [decision-log.md](../../../decision-log.md) from the 6 November goal-change entries, [work-log.md](../../../work-log.md) from the 6 November goal-change entries, [START_HERE_NEXT_CHAT.md](../../../START_HERE_NEXT_CHAT.md), [personal-agent-research-index.md](../../../research/personal-agent-research-index.md) sections 1 and 4, [desktop-conversation.md](../../../desk-companion/docs/desktop-conversation.md) goal-change section, [application-work.md](../../../desk-companion/docs/application-work.md) remaining boundary, [agent-loop-handoff.md](../../../desk-companion/docs/agent-loop-handoff.md) persistent-application section, and [pr5-integration.md](../../../desk-companion/docs/pr5-integration.md) November gate.

Implementation read for this slice: `assistant.py` message model, `text_ai.py` message and fingerprint path, `agent_runs.py` listing and steer, `assistant_routes.py`, the voice panel lifecycle test, and `api.ts` request and pending-write behavior.

## Scope

Chosen: the voice review screen submits the reviewed snapshot through `ConversationWork.turn` with `voice_origin_ref` and `voice_steer`. One current run is the target. Several require `steer_run_id`. None keeps new-run admission.

Not chosen: a new task store, queue, schema migration, or approval tool; a second steer implementation; live mailbox, calendar, or merchant accounts; payment; Pi; paid provider calls; merging Codex drafts #73, #87, and #88.

## Result

The review screen reads `/agent/runs` and offers “Update this work” only for current runs: not cancelled, and still on the first goal. The request is `POST /api/assistant/messages` with the frozen snapshot text, `voice_origin_ref`, `voice_steer: true`, and the run id the owner is shown. An edit stays on “End voice and review work”. Contract: [conversation-work.md](../../../desk-companion/docs/conversation-work.md).

Checked behavior:

- One current run on the task can omit `steer_run_id`. The snapshot text becomes the goal. No new run, job, proposal, or provider call. The other task's run stays. Naming that other run on this task does not steer. The same operation id does not steer again.
- One remaining run and no task id steers that run.
- Two current runs and no run id do not steer. The chosen id steers only that run.
- A task with no runs returns “No current work” and creates nothing. Cancelled runs are not current and do not create a run.
- A plain snapshot without `voice_steer` does not steer. `voice_steer` without a snapshot is `VOICE_STEER_REQUIRES_SNAPSHOT`. Numeric `1` is `VALIDATION_FAILED`.
- `before_commit` leaves the goal unchanged. The same operation id then steers once.
- A different message while the snapshot is live is `VOICE_INPUT_CHANGED`. `after_commit` is not success. After the snapshot is gone, the same goal recovers and a different goal is `OPERATION_ID_CONFLICT`. Neither steers a second time.
- Closing the SSE body is not JSON success. Recovery through the same operation id steers once.
- A paired device receives 403. Full access adds no proposal and no computer job. The task `next_step` stays.
- The screen shows one run as the target, requires a radio choice when several are current, and keeps the new-work button when none are current. An interruption does not count as success and the retry reuses the operation id. An edited wording does not steer.

No browser session. The screen was checked with the frontend protocol harness and `tsc --noEmit`.

## Commands

From `desk-companion/`. `uv` was installed and `uv sync --group dev` created `.venv` because this machine had no project environment. `npm ci` in `frontend/` supplied the frontend tests. Neither install is part of the change.

```sh
uv run --no-sync ruff check backend/desk/conversation_work.py backend/desk/assistant.py backend/desk/voice_work.py backend/desk/text_ai.py backend/desk/runtime.py tests/test_conversation_work.py
uv run --no-sync pytest tests/test_conversation_work.py -q
uv run --no-sync pytest tests/test_integration_acceptance.py -q
uv run --no-sync pytest tests/test_integration_acceptance.py tests/test_text_conversation_scope.py tests/test_goals.py tests/test_permissions.py tests/test_shopping_fixtures.py tests/test_mailbox_journey.py tests/test_offline_calendar_journey.py tests/test_agent_runs.py tests/test_voice_work.py -q
```

From `frontend/`:

```sh
node --experimental-strip-types --test tests/voice-work.test.ts tests/voice-work-lifecycle.test.ts tests/voice-work-render.test.ts
npx tsc --noEmit
```

Results: ruff passed. Conversation-work 54 passed. Integration acceptance 7 passed. The combined regression command passed 148, which is those 7, the previous 97, and voice-work 44. Voice frontend tests passed 19. Typecheck passed. Paid provider calls: 0. GitHub Actions: not run.

## Docs updated

[handoff.md](../../../handoff.md), [START_HERE_NEXT_CHAT.md](../../../START_HERE_NEXT_CHAT.md), [product.md](../../../product.md), [decision-log.md](../../../decision-log.md), [work-log.md](../../../work-log.md), [personal-agent-research-index.md](../../../research/personal-agent-research-index.md), [conversation-work.md](../../../desk-companion/docs/conversation-work.md), [voice-work.md](../../../desk-companion/docs/voice-work.md), [application-work.md](../../../desk-companion/docs/application-work.md), [agent-loop-handoff.md](../../../desk-companion/docs/agent-loop-handoff.md), [pr5-integration.md](../../../desk-companion/docs/pr5-integration.md), [desktop-conversation.md](../../../desk-companion/docs/desktop-conversation.md), and this file.
