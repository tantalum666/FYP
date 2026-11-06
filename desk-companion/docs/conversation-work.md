# Group 2 · Conversation goal changes into existing Work

6 November 2026. An ordinary Alice turn can change the goal of a Work run that already exists. Typed text and a reviewed voice snapshot both use `ConversationWork.turn`, which calls `AgentRunService` steer. It does not create a task, a run, a queue, or a model approval tool, and it does not call a provider.

The first phrases and interruption cases live in [changed-goal.json](../fixtures/conversation-work/changed-goal.json). Held-out phrases and source layouts live in [unseen-variants.json](../fixtures/conversation-work/unseen-variants.json). [QA](../../output/qa/2026-11-06-conversation-work-unseen-voice/verification.md).

## What the owner can say

`parse_changed_goal` is the only matcher. `owner_instruction` keeps one owner line. Quoted lines and source headers are not that line. Any other message stays on the existing short chat path.

| Phrase | What it selects |
|---|---|
| `Change the goal: …` or `调整目标：…` | The one current Work run on the message's `task_id` |
| `Change work <run id>: …` or `调整工作 <run id>：…` | That run. A `task_id` on the message must be one of the run's tasks |

The colon may be `:` or `：`. English leads ignore case. The run id is 32 hex characters. The goal is the exact text after the colon on that one owner line, up to 4,000 characters. The ordinary assistant message still caps the whole turn at 3,000 characters.

Mail/calendar-style headers do not authorize their unquoted body. A copied block containing a goal-change phrase asks the owner to state the instruction separately and is not forwarded to the planner. Quoted source lines may accompany one separate direct command; a bare source header cannot simply be stripped to manufacture that command.

The short chat path also keeps:

- `Goal: …` or `目标：…`, which still prepares a new task draft and leaves Work untouched.
- A question, including a line that ends in `?` or `？`, and a sentence that only asks about the goal.
- Quoted text: a `>` line, or a line wrapped in `「」`, `『』`, or quotation marks. A quote after a real command is left out of the goal.
- More than one current run when the phrase has no run id.
- A missing task with no run id, a cancelled run, or a run that already used its goal change.

A goal that already matches is left as it is. The task's other fields, including an omitted `next_step`, stay as they are. Full access does not turn this reply into a proposal or a computer job. A paired device receives 403.

## Voice snapshot

Freezing a snapshot still does not steer and does not start work. The owner sends that reviewed text on the ordinary assistant message together with `voice_origin_ref`. The server accepts the turn only when the text is the live snapshot. `ConversationWork.turn` then steers. There is no second steer implementation.

A snapshot that is a question, a quote, or a `Goal:` draft gets a normal reply when the message is not an explicit review-screen update. It does not steer, and it does not continue into a task draft or a model call. Two current runs and no run id stay unresolved. Steering leaves the snapshot in place until its existing expiry.

## Review screen

The voice review screen can apply that same snapshot to current work. It posts the ordinary assistant message with the live snapshot text, `voice_origin_ref`, and `voice_steer: true`. `ConversationWork.turn` steers. There is no second steer.

The snapshot text is the goal. It does not need the phrases above. Without `voice_steer`, those phrases are still the only way a message steers.

Current work is not cancelled and has not already changed its goal.

| Current runs | What the turn does |
|---|---|
| One on the message's task, or one in total when the message names no task | That run. `steer_run_id` may be omitted |
| More than one | The owner must send `steer_run_id`. Omitting it does not choose |
| None on that task | No run is created. The screen keeps “End voice and review work” |

A named run must be on the message's task when a task is present. `voice_steer` without `voice_origin_ref` is `VOICE_STEER_REQUIRES_SNAPSHOT`. A numeric `1` is not `voice_steer: true`. An edited wording is `VOICE_INPUT_CHANGED`; the screen uses an edit only to start new work.

The operation id, interruption, lost receipt, and stream close rules below apply unchanged. A paired device receives 403. Full access creates no job and no proposal. Freezing a snapshot still does not steer, and new-run admission is unchanged.

## Verified report file

After the steer commits, the same conversation shows the report file produced and byte-checked by the existing offline Work executor. Deterministic mode reuses `AgentRunService.advance_one` for that run only, then reads the published Markdown back. The reply includes the file's `Goal:` line, so the owner sees the changed goal. The structured `result` uses the existing artifact contract: `verified`, `state: verified`, and `verification: byte_readback` and `quality: not_semantically_checked`. File integrity is not evidence that a shopping, booking or other real-world goal was achieved. No computer job or proposal is created. Model mode is not stepped, because that step would call a provider.

An unverified readback is `CONVERSATION_WORK_RESULT_UNVERIFIED`. A failed run is `CONVERSATION_WORK_RESULT_FAILED`. Neither is a success reply. `before_result` raises `CONVERSATION_WORK_RESULT_INTERRUPTED` before the executor runs; the goal is already changed, and the same operation id can then show the result once. `after_result` raises `CONVERSATION_WORK_RESULT_UNKNOWN` after the file is verified and before the conversation receipt is stored. That response is not success. The same operation id returns the existing file and does not publish a second one. A different goal still conflicts.

A second login cannot open that conversation. Its own turn does not contain the verified line. A paired device still receives 403.

## Interruption and unknown result

`ConversationWork.offline_interrupt` is an in-process fixture control. It is not an HTTP field. Text and voice use it on the same turn.

- `before_commit` raises `CONVERSATION_WORK_INTERRUPTED` before steer. The goal is unchanged. The same operation id can then admit once.
- `after_commit` raises `CONVERSATION_WORK_RESULT_UNKNOWN` after steer and before the conversation receipt is stored. That response is not success. The same operation id and the same goal recover the existing steer. A different goal conflicts, and a second steer does not run. While a voice snapshot is still live, a different message is `VOICE_INPUT_CHANGED`. After that snapshot is gone, the same operation id still recovers; a different goal is `OPERATION_ID_CONFLICT`.

Closing the assistant stream before it finishes is not the success receipt. Recovery uses the same operation id through SSE and does not steer again. This keeps the 28 October rule that a stream interrupt is not success. The verified-result rules above use the same operation id.

[Voice goals](voice-work.md) still govern freeze and new-run admission. The review screen uses the steer above when the owner updates current work, and keeps new-run admission when there is nothing current to update.

## Checks

From `desk-companion/`:

```sh
uv run --no-sync ruff check backend/desk/conversation_work.py backend/desk/assistant.py backend/desk/voice_work.py backend/desk/text_ai.py backend/desk/runtime.py tests/test_conversation_work.py
uv run --no-sync pytest tests/test_conversation_work.py tests/test_integration_acceptance.py -q
```

From `frontend/`:

```sh
node --experimental-strip-types --test tests/voice-work.test.ts tests/voice-work-lifecycle.test.ts tests/voice-work-render.test.ts
```

No paid provider call and no GitHub Actions run. The full backend suite and frontend totals for the verified-result slice are in [QA](../../output/qa/2026-11-06-conversation-work-verified-result/verification.md).

Absent voice fields are excluded from ordinary chat receipt fingerprints, preserving pre-upgrade operation recovery. The new report check matches an entire Goal line, not a prefix embedded in different content.
