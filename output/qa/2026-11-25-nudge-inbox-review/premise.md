# Premise — Inbox morning/evening check-in opens the cited surface

## Gap (current main `fc3b8d2`)

Inbox already offers View in conversation for initiative and View memories / View tasks for memory_morning and followup. Morning briefing and evening check-in receipts only show summary text plus Dismiss, even though they cite today’s plan and open tasks. ui-copy asks for a relevant action inside the entry. Home cue Got it is separate; this slice is Inbox navigation only. Not stacked with #164/#165/#169 initiative inbox work.

No model call: rule-based nudges.

## Not this slice

- #158–#169 product (initiative focus/dismiss/source opens/snooze/Follow up)
- Changing Dismiss / Got it semantics
- Live mailbox, paid model, external send

## Expected visible journey

1. Fixture enables evening check-in with one open task; tick delivers Evening check-in to Inbox.
2. Owner opens Inbox, expands the check-in group.
3. Owner chooses View tasks (not Dismiss).
4. Tasks page opens and shows the open task. Inbox receipt stays open until Dismiss.

(Morning briefing → View today is the same wiring; Chrome acceptance uses evening → Tasks.)

## Evidence tier

Local real Chrome at 1440 and 320 on owned ports. Fixture login + rule nudge. Not live-account or paid-model acceptance.
