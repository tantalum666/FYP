# Meeting prep in the conversation

11 November 2026. Grok Bot, offline. Alice answers one asked question from the saved calendar: what the next meeting is, where it is, one related open task, and one memory the owner already saved. She does not create, move, book, or send anything.

## Why this, and not another card

The research index’s life journeys are mail, a staple purchase, and a trip. Those, plus Work re-show and continue, the folder-job clock, browser takeover, memory follow-ups, the morning check-in, trip quotes, saved and scheduled skills, the staple purchase card, cited briefs, held choices, the asked “what should I do next?” sentence, and the asked “when am I free?” sentence, are already open pull requests. Codex’s pull request owns the shared Alice home, attachments, Gmail and Outlook drafts, and voice preferences.

What is still missing in an ordinary conversation is the question a person asks before they walk into a room: “Prep me for my next meeting.” The calendar list answers “What is on today?” by naming every saved event. A next-step answer names one action. An open-time answer names gaps. This question is asked, so Alice answers with the meeting itself. Quiet hours and proactivity off do not suppress it. There is no confirm button, and `acted` stays false.

## What the owner can say

The whole message has to be the question. English and Chinese both work. The reply language follows the request.

- “Prep me for my next meeting”, “Brief me before my next meeting”, “What should I know before my next meeting?”, and “下一场会要准备什么” use the soonest timed meeting that has not ended and starts within 36 hours. An in-progress meeting is that meeting.
- “Prep me for tomorrow's meeting” and “明天的会议要准备什么” use the first timed meeting on the next local calendar day, and the reply names that date.
- “What is on today?”, “What should I do next?”, “When am I free tomorrow?”, a task title, and “Tomorrow 15:00–16:00 Studio time” are not this question.

A transparent event and an all-day event do not count as the meeting. A weekly event counts on the later occurrence that falls in the window. The first sentence names the time and says the calendar was not changed, so a brief reply still keeps that fact. A later sentence can name a saved note, one open task whose title shares a word with the meeting, and one saved memory that shares a word, with the day it was saved. An unrelated fact is not quoted.

## Privacy, receipt, and provider

Titles come from the existing calendar snapshot. A private event is named for the owner only when the calendar is not hiding private events. A paired display hears “a private meeting” and does not hear the title, the place, the note, a private task step, or any saved memory. A displayable meeting can be named on that display. Its related memory stays with the owner.

The same operation id returns the stored sentence, including after the calendar changes. A different message under that id conflicts and does not replace the sentence. A new id reads the calendar again. If the reply is interrupted before it is stored, nothing is written and the same id can be sent again. An omitted language stays English. An unknown field is rejected. A configured text provider is not called, including when memory extraction is armed.

The answer is registered in the offline parser after the file commands and before a selected task would become a progress note. On a configured provider it is registered after memory, goals, recall, and extraction, and before the model call. `Runtime.tick` is unchanged. No import was added after `from .goals import GoalService` or before `owner_lookup`. `mailbox_bundle`, `shopping_bundle`, and `offline_calendar_bundle` are unchanged. Schema version stays 3.

## Not in this slice

No mailbox send, no merchant, no payment, no live calendar account, and no paid model call. A cited memory is a saved fact, not a claim that the meeting will go well.

## Codex handoff

Files:

- `desk-companion/backend/desk/meeting_prep.py` — new
- `desk-companion/backend/desk/assistant.py` — one call in `_local_message`, after the save-note command and before the calendar-list parser. A local import, not a new top-level import
- `desk-companion/backend/desk/text_ai.py` — `maybe_extract` returns before a model call when the message is this question; `_message` then answers after extraction and before the model
- `desk-companion/frontend/src/workspace/AssistantPanel.tsx` — a starter button beside the existing chips, a help-list line, and a “Next meeting” label when `kind === "meeting_prep"`
- `desk-companion/frontend/src/workspace/assistant-minimal.css` — label only
- tests: `desk-companion/tests/test_meeting_prep.py`, `desk-companion/frontend/tests/meeting-prep.test.ts`

#114 registers at the start of `_local_message` and in `_scoped_message`. #115 registers after the clock is loaded and before `maybe_extract`. This slice uses neither of those spots. If a merge drops the call in `_local_message`, a selected task turns the question into a progress-note draft, and the word “meeting” falls through to the calendar list. If a merge drops the call in `_message`, a configured provider sees the question. Keep both.

#97 rewrites the AssistantPanel welcome and deletes the starter chips. If that merge deletes the welcome, do not restore the whole welcome; the typed phrase still works. Keep the `meeting_prep` label inside the turn, after the job card. Keep #97’s attachment fingerprint. A goal-change phrase still reaches `conversation_work.turn` first.

Known suite failures on `main`, left as they were: `test_public_unicast[::ffff:93.184.216.34]` and `test_restart_runs_only_the_approved_folder_job` (the latter is fixed by #98, which is not in this branch).

Local check on this branch: backend **2044 passed, 2 failed** (those two), frontend **331 passed, 0 failed**, ruff and `tsc --noEmit` clean. The owner browser on `127.0.0.1:5190` sent the starter phrase and got the Project discussion brief, including Studio 3, the open task, and the cited 11 Nov 2026 memory, with no approve control.
