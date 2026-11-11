# Reply owed — conversation slice

11 November 2026. Grok Bot completed this on `cursor/reply-owed-conversation-6a62`. It is not merged.

## Why this slice

The research index’s first real acceptance ties one thread to a deadline, the person the owner still needs to reply to, and the thing the owner is waiting on. Open pull request #118 answers “What am I waiting on?”. The other half of that sentence was still missing from the conversation: the owner says they owe someone a reply, and later asks who.

A demo user notices it in an ordinary exchange with Alice. “I need to reply to Sam about the venue.” Then, “Who do I need to reply to?” Alice names Sam and the venue. Nothing is sent. The same words do not open a second task.

This is not who Alice is waiting on. Waiting is someone else. A reply owed is the owner’s own unanswered note. It is also not a Gmail or Outlook draft (Codex #97), not the next-step question (#114), not open time (#115), not meeting prep (#116), and not the calendar list. No model is called. `Runtime.tick` does not approve the draft.

## What the owner can say

| Sentence | Result |
| --- | --- |
| Who do I need to reply to? / What replies do I owe? / 我该回复谁 / 还有谁等我回复 | Names each open reply. Empty means none. |
| I need to reply to Sam about the venue / I owe Sam a reply / Reply to Sam / 我该回复 Sam，关于场地 / 回复 Sam 关于场地 | A task draft. Nothing is saved until Allow once. |
| I need to reply / 回复 | Asks who. Saves nothing. |

`我要…` stays a goal. “我要回复 Sam” is not this slice.

The saved line is `Reply to {who}` or `Reply to {who} about {topic}`. Status stays `todo`. `waiting_for` stays empty, so a waiting task is not listed here and a reply is not listed as waiting.

The same person and topic, ignoring case and extra spaces, does not open a second task. Saying the person again without a topic does not clear a topic already saved. Saying the topic later fills that empty line and leaves the deadline, next step, and visibility as they were. A selected open task that does not already cover that person gains one step and keeps its title, deadline, next step, visibility, follow-up, and interval. A check-in already in the past is left unset so confirm can succeed; the deadline stays. A closed selected task is not reopened. Cancel saves nothing. The same operation id returns the same draft; a different sentence on that id conflicts. An interrupted draft or confirm leaves no task, and the same id can finish that one effect.

A paired display gets the count only. It cannot prepare or confirm a reply. Another login is refused. While private tasks are hidden, the owner’s list does not repeat the name. Full access uses the existing task-draft policy: one new owner request saves one task, and a repeat does not save another. Tick does not.

These sentences stay with their current parsers: “What is on today?”, “When am I free tomorrow?”, “What should I do next?”, “Prep me for my next meeting”, “What am I waiting on?”, “I'm waiting on Sam”, “Track: …”, “Goal: …”, and “Tomorrow 15:00–16:00 …”. On this branch the next-step, open-time, meeting-prep, and waiting questions still fall through to the calendar clarifier, because those slices are not here.

## Where the code sits

`desk/reply_owed.py` owns the match and the draft. No new table, route, or service on `Runtime`.

- `AssistantService._local_message`: after the editor-preview command returns, before the save-note command. That is after memory, goals, and recall, and before a selected task becomes a progress note.
- `TextAssistant._message`: the first local turn, before `memory_turn`. The existing `if turn is not None` return stores the reply, so `maybe_extract` does not see the sentence.

A message that carries `attachment_ids` on the request or the conversation returns None, so a later file composer is not swallowed. On this branch that field is absent. Do not move the call into a `not has_files` chain.

The help page has the question as a button and as one list item, between “What is on next week?” and “Track: …”. When the latest reply is this answer, the transcript shows “Reply owed” / “待回复”. The existing proposal card is Allow once. Welcome chips are unchanged.

## Codex handoff

Merge this on its own. It does not stack on #114–#116 or #118, and it does not edit #97.

Keep both call sites. Do not put an import after `from .goals import GoalService` or before `owner_lookup`. Do not change `Runtime.tick`, `mailbox_bundle`, `shopping_bundle`, or `offline_calendar_bundle`.

Phrases that must not be claimed by this parser: what to do next, when someone is free, meeting prep, who the owner is waiting on, the calendar list, track, and goal. “Who do I need to reply to?” is only this slice.

If #97’s `not has_files` guard is merged later, leave this call where it is. `answer_reply_owed` already returns None when `attachment_ids` is non-empty. The `_message` call is before `memory_turn`, not beside `open_time_turn`, `maybe_extract`, or `answer_meeting_prep`. The `_local_message` call is before the save-note command, not beside `next_step_turn`, `answer_waiting`, `answer_meeting_prep`, or `open_time_turn`.

## Not in this slice

A live mailbox, a sent message, a merchant, a payment, a calendar account, and a paid model call are still separate. Naming a reply owed does not send it and does not mean the other person has written back.
