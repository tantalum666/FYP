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

A mail or calendar layout steers when its labels are the only other lines and the remaining line is one phrase above. Those labels are From, Subject, Date, To, Cc, Sender, Location, Notes, Title, and Snippet, plus 发件人, 主题, 日期, 收件人, 抄送, 地点, 备注, and 标题. A CSV row, a Notes or 备注 value that itself contains the phrase, a second owner line, or chatter before the phrase stays on the short chat path.

The short chat path also keeps:

- `Goal: …` or `目标：…`, which still prepares a new task draft and leaves Work untouched.
- A question, including a line that ends in `?` or `？`, and a sentence that only asks about the goal.
- Quoted text: a `>` line, or a line wrapped in `「」`, `『』`, or quotation marks. A quote after a real command is left out of the goal.
- More than one current run when the phrase has no run id.
- A missing task with no run id, a cancelled run, or a run that already used its goal change.

A goal that already matches is left as it is. The task's other fields, including an omitted `next_step`, stay as they are. Full access does not turn this reply into a proposal or a computer job. A paired device receives 403.

## Voice snapshot

Freezing a snapshot still does not steer and does not start work. The owner sends that reviewed text on the ordinary assistant message together with `voice_origin_ref`. The server accepts the turn only when the text is the live snapshot. `ConversationWork.turn` then steers. There is no second steer implementation.

A snapshot that is a question, a quote, or a `Goal:` draft gets a normal reply. It does not steer, and it does not continue into a task draft or a model call. Two current runs and no run id stay unresolved. Steering leaves the snapshot in place until its existing expiry.

## Interruption and unknown result

`ConversationWork.offline_interrupt` is an in-process fixture control. It is not an HTTP field. Text and voice use it on the same turn.

- `before_commit` raises `CONVERSATION_WORK_INTERRUPTED` before steer. The goal is unchanged. The same operation id can then admit once.
- `after_commit` raises `CONVERSATION_WORK_RESULT_UNKNOWN` after steer and before the conversation receipt is stored. That response is not success. The same operation id and the same goal recover the existing steer. A different goal conflicts, and a second steer does not run. While a voice snapshot is still live, a different message is `VOICE_INPUT_CHANGED`. After that snapshot is gone, the same operation id still recovers; a different goal is `OPERATION_ID_CONFLICT`.

Closing the assistant stream before it finishes is not the success receipt. Recovery uses the same operation id through SSE and does not steer again. This keeps the 28 October rule that a stream interrupt is not success.

[Voice goals](voice-work.md) still govern freeze and new-run admission. The review screen itself still starts a new run only.

## Checks

From `desk-companion/`:

```sh
uv run --no-sync ruff check backend/desk/conversation_work.py backend/desk/assistant.py backend/desk/voice_work.py backend/desk/text_ai.py backend/desk/runtime.py tests/test_conversation_work.py
uv run --no-sync pytest tests/test_conversation_work.py tests/test_integration_acceptance.py -q
```

No paid provider call and no GitHub Actions run.
