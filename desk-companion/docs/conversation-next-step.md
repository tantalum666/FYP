# Conversation next step — 11 November 2026

Grok Bot completed this slice. Alice answers one ordinary question in the existing conversation: “What should I do next?” / “接下来做什么？”. The answer is read from local records. She does not do the step, open a draft, or call a model.

This is the gap a demo user hits on the main conversation page. The offline parser already answers “What is on today?” and can draft a calendar event, but the same page answers “What should I do next?” with the calendar-format prompt. Moments and morning briefs stay on their own cards and stay silent during quiet hours or when proactivity is off. Those are unsolicited. This question is asked, so Alice answers anyway. It is not another approval ledger: there is no confirm button and `acted` stays false.

Research context: Dot’s published behavior is to keep one responsibility and come back with a concrete next step, and the research index separates that from a timer that only calls the model. Grok’s public notes say a reusable skill is not itself the live answer in chat. Saved skills, scheduled skills, held choices, purchase cards, trip quotes, source briefs, memory follow-ups, and morning check-in stay out of this slice.

## What the owner hears

The phrase has to be the whole message. “What is next week?” and “What is on today?” stay on the calendar parser. A selected open task with a saved next step or a waiting reason wins. Otherwise Alice names one thing, in this order:

1. The soonest timed event that has not ended and starts within 24 hours. A hidden title is “a private event” plus the time, for the owner only.
2. An open task that has a saved next step, then one that is waiting on someone.
3. The open goal with the soonest saved due date.
4. A sentence that nothing is waiting, and that nothing was created.

The first sentence includes the fact and “I have not done it” (or the Chinese equivalent), so brief style cannot drop the refusal. A paired screen does not receive a private title or a private step. With hide-private on, the owner’s own display gets the same hiding. The same operation id returns the stored sentence. A later operation id reads the current record. An error before that sentence is stored does not complete the task, and the same operation id can be sent again.

No new request field. Omitting `language`, `task_id`, and `conversation_id` still answers. `mailbox_bundle`, `shopping_bundle`, and `offline_calendar_bundle` are unchanged. `Runtime.tick` is unchanged. Schema version stays 3. No backup bundle was added.

## Codex handoff

Files:

- `desk-companion/backend/desk/next_step.py` — new
- `desk-companion/backend/desk/assistant.py` — `next_step_turn`, called at the start of `_local_message` so a selected task is not turned into a progress-note draft
- `desk-companion/backend/desk/text_ai.py` — one `elif` in `_scoped_message` after `conversation_work.turn` returns None and before `_message`. That is what keeps a configured provider from seeing the question
- `desk-companion/frontend/src/workspace/AssistantPanel.tsx` — starter chip, help line, and a “Next step” label when `kind === "next_step"`
- `desk-companion/frontend/src/workspace/assistant-minimal.css` — label only
- tests: `desk-companion/tests/test_conversation_next_step.py`, `desk-companion/frontend/tests/conversation-next-step.test.ts`

Do not insert an import after `from .goals import GoalService`. This slice imports `answer_next_step` next to the recall import in `assistant.py`. It does not edit `runtime.py`.

#97 rewrites the AssistantPanel welcome (it deletes the starter chips) and the turn markup (it adds file chips). If that merge deletes the welcome, do not restore the whole welcome; the typed phrase still works. Keep the `next_step` label inside #97’s turn block, above the message paragraph. Keep #97’s `attachment_ids` fingerprint pop. Keep this `elif stepped` between the admitted Work reply and `_message`. A goal-change phrase still reaches `conversation_work.turn` first.

#108–#112 do not own this phrase. Do not fold it into moments, nudges, memory follow-ups, or held choices.

Known suite failures on this checkout, left as they were: `test_public_unicast[::ffff:93.184.216.34]` and `test_restart_runs_only_the_approved_folder_job` (the latter is fixed by #98, which is not in this branch).
