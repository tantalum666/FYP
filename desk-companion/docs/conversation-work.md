# Group 2 · Conversation goal changes into existing Work

6 November 2026. An ordinary Alice text turn can change the goal of a Work run that already exists. The turn uses `AgentRunService` steer. It does not create a task, a run, a queue, or a model approval tool, and it does not call a provider.

Offline phrases and the interruption cases live in [changed-goal.json](../fixtures/conversation-work/changed-goal.json). [QA](../../output/qa/2026-11-06-conversation-work-changed-goal/verification.md).

## What the owner can say

The message has to start with one of these forms. Anything else stays on the existing short chat path.

| Phrase | What it selects |
|---|---|
| `Change the goal: …` or `调整目标：…` | The one current Work run on the message's `task_id` |
| `Change work <run id>: …` or `调整工作 <run id>：…` | That run. A `task_id` on the message must be one of the run's tasks |

The run id is 32 hex characters. The goal is the exact text after the colon, up to 4,000 characters. A missing task with no run id, more than one current run, a cancelled run, or a run that already used its goal change gets a normal reply and no steer. `Goal: …` still prepares a new task draft and does not touch Work.

A goal that already matches is left as it is. The task's other fields, including an omitted `next_step`, stay as they are. Full access does not turn this reply into a proposal or a computer job. A paired device receives 403.

## Interruption and unknown result

`ConversationWork.offline_interrupt` is an in-process fixture control. It is not an HTTP field.

- `before_commit` raises `CONVERSATION_WORK_INTERRUPTED` before steer. The goal is unchanged. The same operation id can then admit once.
- `after_commit` raises `CONVERSATION_WORK_RESULT_UNKNOWN` after steer and before the conversation receipt is stored. That response is not success. The same operation id and the same goal recover the existing steer. A different goal on that operation id conflicts. A second steer does not run.

Closing the assistant stream before it finishes is not the success receipt. Recovery uses the same operation id through SSE and does not steer again. This keeps the 28 October rule that a stream interrupt is not success.

Speech snapshots still do not steer an existing run. [Voice goals](voice-work.md) remain a separate review handoff. Unseen phrases and source layouts are not covered by this fixture.

## Checks

From `desk-companion/`:

```sh
uv run --no-sync ruff check backend/desk/conversation_work.py backend/desk/text_ai.py backend/desk/runtime.py tests/test_conversation_work.py
uv run --no-sync pytest tests/test_conversation_work.py tests/test_integration_acceptance.py -q
```

No paid provider call and no GitHub Actions run.
