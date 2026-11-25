# Premise — Inbox initiative opens the bound finding in Conversation

## Gap (current main `fc3b8d2`)

Inbox shows “View in conversation” for an initiative notice, but it only switches to Assistant and expands Conversation. It does not pass the notice id, scroll to the bound finding, or open Sources. With history or several pending findings, the owner may miss the receipt that Inbox pointed at. Home cue → Conversation is #164 (open) and is not stacked here. Inbox Dismiss heal is #165 (open).

Always-on research keeps evidence in Conversation while Inbox holds a generic receipt. The owner should land on that receipt’s finding with Sources open, without dismissing.

## Not this slice

- #158–#168 product (including #164 home cue View, #165 Dismiss heal, source opens, Follow up, snooze)
- Changing Got it / Dismiss semantics
- Live mailbox, paid model, external send

## Expected visible journey

1. Fake initiative delivers one inbox notice bound to one pending finding.
2. Owner opens Inbox, expands the Alice noticed something group.
3. Owner chooses View in conversation (not Dismiss).
4. Conversation expands; that finding is focused with Sources open; Got it still available.
5. Inbox notice remains open (state open); finding remains pending.

## Evidence tier

Local real Chrome at 1440 and 320 on owned ports. Fake initiative + fixture login. Not live-account or paid-model acceptance.
