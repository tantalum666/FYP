# Held choices

11 November 2026. An owner records one choice and the assumption it rests on. The choice becomes current only when that owner approves the exact wording. A later assumption keeps the previous wording readable, and the previous wording stays current until a fresh approval. Nothing is mailed, bought, booked, or marked complete. No model is called.

This is the gap left after the open slices. Mail, the staple purchase card, trip quotes, saved and scheduled skills, cited note comparisons, memory follow-ups, morning check-in, browser takeover, and conversation Work each cover their own journey. None of them keeps a choice whose basis changed: the old wording stays on record, and it is no longer safe to treat a new basis as already approved. Grok's approval rule is that a changed target does not reuse an earlier approval. Dot treats a changed constraint as something that does not redo a confirmed result. Muse authorizes the purchase or booking in front of the owner again when the basis changes. This slice is that rule for one local choice. It is not a fourth copy of the mailbox, shopping, or calendar journey.

## What the owner can do

On Tasks, under the task list:

1. Write what the choice is, the assumption, the choice, and why. Saving creates a draft. It is not the current choice.
2. Approve that exact wording. It becomes the current choice.
3. Change the assumption. The current choice stays current. The new wording waits.
4. Approve the new wording, or drop the draft. Approving moves the old wording to "Previous wording" and makes the new one current. Dropping the draft leaves the current choice alone.
5. The page says that saving a choice does not send mail, buy, or book anything.

A repeated save of the same wording, ignoring case and extra spaces, returns the open choice instead of creating a second one. The stored wording keeps the owner's original casing and collapsed spaces. An approval that quotes different text does not hold the choice. Omitted fields on a replacement stay as they are. JSON `null` does not clear a field.

Full access does not approve a draft. `Runtime.tick` does not either. Opening the list does not approve it. A paired display has no owner session, so it cannot read or approve. Hiding private facts and signing out both refuse the write, including a retry of an approval that was interrupted. An interrupted save is not success. The same operation id finishes that one effect, including from a new process that opens the same database. A later, different operation id can also approve the still-pending wording, and that still produces one current row.

## Boundaries

- Owner session is checked again inside the write transaction, including private-hide.
- Operation ids share the existing `operations` table. The same id and body return the saved result. A different body conflicts.
- The intent row commits before the choice becomes current. A fault between those two commits leaves the choice unheld.
- At most 100 choices and 20 versions of one choice.
- No new portable backup key. `mailbox_bundle`, `shopping_bundle`, and `offline_calendar_bundle` are untouched.
- `Runtime.tick` is untouched.
- Phone Plan still shows tasks only. This panel is on the desk Tasks page.

## HTTP

Owner cookie, `X-Desk-Request: 1`, and `X-Operation-Id` on writes.

- `GET /api/held-choices`
- `POST /api/held-choices` with `title`, `assumption`, `choice`, `reason`
- `POST /api/held-choices/{id}/replacements` with `expected_version` and any of the four text fields
- `POST /api/held-choices/{id}/approval` with `expected_version` and all four text fields
- `POST /api/held-choices/{id}/withdrawal` with `target` of `pending` or `current`, and `expected_version`

Responses include `held`, `live_effect`, `mailed`, `purchased`, and `booked`. The last four are false. `held` is true only when a current version exists.

## Not in this slice

A live merchant, mailbox, or calendar account. A model call. Completing a task because a choice was approved. Editing saved skills, trip quotes, or source briefs.
