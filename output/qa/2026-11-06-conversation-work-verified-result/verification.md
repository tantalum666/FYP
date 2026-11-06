# One verified offline result after a goal change

6 November 2026. Grok Bot completed this through a Cursor cloud agent. Codex reviews and merges. This branch is stacked on PR #91 (`cursor/voice-review-steer-current-work-e7d6`). Merge order is #89, then #90, then #91, then this PR.

## Merge note for Codex

| Order | PR | Branch | What it adds |
|---|---|---|---|
| 1 | #89 | `cursor/conversation-work-changed-goal-4bf4` | Explicit text goal change steers one current Work run |
| 2 | #90 | `cursor/conversation-work-unseen-voice-4185` | Held-out phrases and a reviewed voice snapshot use that steer |
| 3 | #91 | `cursor/voice-review-steer-current-work-e7d6` | The voice review screen updates one current run |
| 4 | this PR | `cursor/conversation-work-verified-result-0291` | The same conversation shows one verified offline result |

Merge #89 into its base first, then #90, then #91, then this PR. This PR's diff is only the verified-result slice. It does not retarget #73, #87, or #88.

## What was read

Full files: [AGENTS.md](../../../AGENTS.md), [handoff.md](../../../handoff.md), [conversation-work.md](../../../desk-companion/docs/conversation-work.md), `conversation_work.py`, and the prior [QA](../2026-11-06-voice-review-steer/verification.md).

Sections, not the whole history: [product.md](../../../product.md) lines 1–40, [decision-log.md](../../../decision-log.md) from the 6 November goal-change entries, [work-log.md](../../../work-log.md) from the 6 November goal-change entries, [START_HERE_NEXT_CHAT.md](../../../START_HERE_NEXT_CHAT.md), [personal-agent-research-index.md](../../../research/personal-agent-research-index.md) sections 1 and 4, [desktop-conversation.md](../../../desk-companion/docs/desktop-conversation.md) goal-change section, [application-work.md](../../../desk-companion/docs/application-work.md) remaining boundary, [agent-loop-handoff.md](../../../desk-companion/docs/agent-loop-handoff.md) persistent-application section, [pr5-integration.md](../../../desk-companion/docs/pr5-integration.md) November gate, and [voice-work.md](../../../desk-companion/docs/voice-work.md) controls section.

Implementation read for this slice: `AgentRunService.advance_one`, `_deterministic`, `_publish`, `artifact_payloads`, `ArtifactService.read`, the assistant reply cache, and the conversation session scope.

## Scope

Chosen: after text or voice steer commits, drive the existing deterministic executor for that run only and show one byte-readback of the published Markdown in the same conversation. The `Goal:` line is the changed goal.

Not chosen: a new task store, queue, schema migration, or approval tool; a computer job or proposal; a provider call; stepping model mode; live mailbox, calendar, or merchant accounts; payment; Pi; merging Codex drafts #73, #87, and #88.

## Result

`ConversationWork` calls `AgentRunService.advance_one(run_id)` after the steer. The worker's no-argument path is unchanged. The reply keeps the existing goal-change wording and adds the verified `Goal:` line. `result.verified` is true only when the artifact status is `verified` and `verification` is `byte_readback`. Contract: [conversation-work.md](../../../desk-companion/docs/conversation-work.md).

Checked behavior:

- A text change and a review-screen voice update each show one verified result for the new goal. The old goal is not that line. No provider call, no application execution, and the other run is not advanced.
- The same operation id returns the stored reply. The Markdown id does not change, and the conversation keeps one verified turn.
- `before_result` is not success. The goal is already changed and no report exists. The same operation id then shows the result once.
- `after_result` is `CONVERSATION_WORK_RESULT_UNKNOWN`, not success. Recovery shows the existing file and does not publish another.
- An unverified readback is `CONVERSATION_WORK_RESULT_UNVERIFIED`. A failed executor step is `CONVERSATION_WORK_RESULT_FAILED`. Neither response is success, and the failed retry stays failed.
- A second login cannot open the conversation and does not receive the verified line. A paired device receives 403. Full access creates no job and no proposal.

No browser session. The owner-visible sentence is the assistant message the existing conversation and voice review screen already render.

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

Results: ruff passed. Conversation-work 60 passed. Integration acceptance 7 passed. The combined command passed 67. The full backend suite was 1828 passed and 1 failed, in 443.82s. Frontend tests passed 323. Typecheck passed. Paid provider calls: 0. GitHub Actions: not run.

## Pre-existing failure

`tests/test_public_capture_transport.py::test_public_unicast[::ffff:93.184.216.34]` failed. The other three addresses in that test passed. `is_public_unicast` rejects the address because Python 3.12 reports `IPv6Address.is_reserved` for `::ffff:93.184.216.34` before the embedded IPv4 check. This branch does not modify `public_capture_transport.py` or that test. Mailbox, shopping, offline calendar, and decide coverage remains inside the 1828 passed tests, and the integration-acceptance file passed 7.

## Docs updated

[handoff.md](../../../handoff.md), [START_HERE_NEXT_CHAT.md](../../../START_HERE_NEXT_CHAT.md), [product.md](../../../product.md), [decision-log.md](../../../decision-log.md), [work-log.md](../../../work-log.md), [personal-agent-research-index.md](../../../research/personal-agent-research-index.md), [conversation-work.md](../../../desk-companion/docs/conversation-work.md), [voice-work.md](../../../desk-companion/docs/voice-work.md), [application-work.md](../../../desk-companion/docs/application-work.md), [agent-loop-handoff.md](../../../desk-companion/docs/agent-loop-handoff.md), [pr5-integration.md](../../../desk-companion/docs/pr5-integration.md), [desktop-conversation.md](../../../desk-companion/docs/desktop-conversation.md), and this file.
