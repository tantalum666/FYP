# Waiting on — conversation slice

11 November 2026. Grok Bot completed this on `cursor/waiting-on-conversation-eae3`. It is not merged.

## Why this slice

A demo user talking to Alice can already ask what is on today, track a task, and (in open pull requests) ask what to do next, when they are free, and how to prep a meeting. They cannot say who they are waiting on and hear that name back.

That question is the blocked half of the mail-to-task journey in the research index: a thread becomes a task with something still outstanding, and the owner asks again later. Tasks already store `waiting` and `waiting_for`, and the proposal card already shows “Waiting:”. The conversation did not use them. Morning check-in cites memories. Held choices keep a decision and its assumption. Next step, open time, and meeting prep answer different sentences. This slice does not touch those.

Nothing is mailed, bought, booked, or marked complete. No model is called. `Runtime.tick` does not approve the draft.

## What the owner can say

| Sentence | Result |
| --- | --- |
| What am I waiting on? / Who am I waiting for? / 我在等什么 / 谁还没回我 | Names each open waiting reason. Empty means nobody. |
| I'm waiting on Sam for the budget / Waiting on Sam / 在等 Sam 的预算 | A task draft. Nothing is saved until Allow once. |
| I'm waiting / 在等 | Asks who or what. Saves nothing. |

The same wording, ignoring case and extra spaces, does not open a second task. The stored wording keeps the owner’s original casing. A selected open task is updated and keeps title, deadline, next step, steps, visibility, follow-up, and interval. A check-in that is already in the past is left unset so confirm can succeed; the deadline stays. A closed task is not reopened. Cancel saves nothing. The same operation id returns the same draft; a different sentence on that id conflicts. An interrupted draft or confirm leaves no task, and the same id can finish that one effect.

A paired display gets the count only. It cannot prepare or confirm a reason. Another login is refused. While private tasks are hidden, the owner’s list does not repeat the reason. Full access uses the existing task-draft policy: one new owner request saves one task, and a repeat does not save another. Tick does not.

These sentences stay with their current parsers: “What is on today?”, “When am I free tomorrow?”, “What should I do next?”, “Prep me for my next meeting”, “Track: …”, “Goal: …”, and “Tomorrow 15:00–16:00 …”. “Prep me for my next meeting” is still the calendar clarifier on this branch, because meeting prep is not here.

## Where the code sits

`desk/waiting_on.py` owns the match and the draft. No new table, route, or service on `Runtime`.

- `AssistantService._local_message`: after `recall_turn`, before the save-to-folder command.
- `TextAssistant._message`: after the block that returns a memory, goal, recall, or extract turn, and before `from .assistant import TOOLS`.
- `maybe_extract`: returns immediately when the message is a waiting sentence, so a raised extract cap does not send it to a model. The check is the line before `generate`, not the top of the function.

A message that carries `attachment_ids` on the request or the conversation returns None, so a later file composer is not swallowed. On this branch that field is absent. Do not move the call into the `not has_files` chain.

The button “What am I waiting on?” / “我在等什么” sits above the text composer, outside the welcome chips. The same question is one help-list item. The existing proposal card shows the reason and Allow once.

## Codex handoff

Merge this on its own. It does not stack on #114, #115, or #116, and it does not edit #97.

Keep both call sites. Do not drop the `is_waiting_message` return inside `maybe_extract`. Do not put an import after `from .goals import GoalService` or before `owner_lookup`. Do not change `Runtime.tick`, `mailbox_bundle`, `shopping_bundle`, or `offline_calendar_bundle`.

Phrases that must not be claimed by this parser: what to do next, when someone is free, meeting prep, the calendar list, track, and goal. “What am I waiting on?” is only this slice.

If #97’s `not has_files` guard is merged later, leave this call where it is. `answer_waiting` already returns None when `attachment_ids` is non-empty.

## Not in this slice

A live mailbox, a merchant, a payment, a calendar account, and a paid model call are still separate. A waiting line is not an email and not a promise that the other person replied.
