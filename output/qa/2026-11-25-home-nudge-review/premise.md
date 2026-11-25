# Premise — Home morning/evening check-in opens Today or Tasks

## Gap (current main `fc3b8d2`)

The compact Alice home cue for morning briefing and evening check-in only offers Got it. Inbox gains View today / View tasks in open #170; that PR’s premise leaves the home cue as Got it only. ui-copy asks for a relevant action inside the entry when an update cites another part of Alice. Not stacked with #164 (initiative View in conversation) or #170 (Inbox only).

Rule nudge only — no model call.

## Not this slice

- #158–#171 product (including Inbox #170 and initiative home #164)
- Changing Got it / dismiss semantics
- Live mailbox, paid model, external send

## Expected visible journey

1. Fixture enables evening check-in with one open task; home cue is evening_check.
2. Owner is on Alice home (Conversation collapsed).
3. Owner chooses View tasks (not Got it).
4. Tasks opens and shows the open task. Cue dismiss is unchanged; navigation does not dismiss.

(Morning briefing → View today is the same wiring; Chrome acceptance uses evening → Tasks.)

## Evidence tier

Local real Chrome at 1440 and 320 on owned ports. Fixture login + rule nudge. Not live-account or paid-model acceptance.
