# Premise — Inbox task follow-up opens the cited task

## Gap (current main `fc3b8d2`)

Inbox follow-up receipts offer View tasks, which only opens the Tasks list. The notice id is `followup-<followup_row_id>` and did not expose `task_id` on the receipt. Home already gains Open task for the same follow-up in open #173; that PR does not change Inbox. ui-copy asks for a relevant action inside the entry when an update cites another part of Alice. This slice adds `task_id` on new follow-up notices and Open task in Inbox.

Rule follow-up only — no model call.

## Not this slice

- #158–#173 product (including home Open task #173 and Inbox morning/evening #170)
- Changing Dismiss semantics
- Live mailbox, paid model, external send

## Expected visible journey

1. Fixture creates a followed task and advances past its check interval so an open follow-up notice exists.
2. Owner opens Inbox, expands the follow-up receipt.
3. Owner chooses Open task (not Dismiss).
4. Tasks opens with that task selected. The notice stays open (not dismissed).

## Evidence tier

Local real Chrome at 1440 and 320 on owned ports. Fixture login + rule task follow-up. Not live-account or paid-model acceptance.
