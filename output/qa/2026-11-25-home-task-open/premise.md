# Premise — Home task cue opens that task in Tasks

## Gap (current main `fc3b8d2`)

The compact Alice home cue for a task follow-up offers Done, Still working, and In an hour. It does not open the cited task. ui-copy asks for a relevant action when an update cites another part of Alice. Open #166 adds Open task on finding Sources only; #172 covers morning/evening home navigation. Neither opens the bound task from the home task cue.

Rule follow-up only — no model call.

## Not this slice

- #158–#172 product (including Sources Open task #166 and home morning/evening #172)
- Changing Done / Still working / In an hour semantics
- Live mailbox, paid model, external send

## Expected visible journey

1. Fixture creates a followed task and advances past its check interval so the home cue is kind `task`.
2. Owner is on Alice home (Conversation collapsed).
3. Owner chooses Open task (not Done / Still working / In an hour).
4. Tasks opens with that task selected and its title visible. Cue actions that mutate the task are unchanged; Open task does not complete, snooze, or dismiss.

## Evidence tier

Local real Chrome at 1440 and 320 on owned ports. Fixture login + rule task follow-up. Not live-account or paid-model acceptance.
