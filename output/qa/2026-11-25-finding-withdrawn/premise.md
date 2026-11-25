# Premise — withdrawn finding stays visible when Sources change

## Gap (current main `fc3b8d2`)

Conversation shows a cited proactive finding. If the owner deletes or changes a cited memory/task so fingerprints no longer match, the next workspace refresh drops that finding from `current()` with no owner-facing explanation. The card vanishes. Contract says a changed source invalidates the finding; it does not say Alice should silently erase the transcript. #161 (open) only blocks Follow up on stale evidence; it does not add a withdrawn card. Not stacked.

## Not this slice

- #158–#170 product (Follow up, snooze, source opens, inbox focus/dismiss, nudge View)
- Re-opening research, paid model, live mailbox
- Weakening dismiss/idempotence

## Expected visible journey

1. Fake finding cites a memory (and task) in Conversation.
2. Owner sees the proactive suggestion with Sources.
3. Cited memory is deleted (fixture API).
4. Conversation still shows that card as withdrawn: original message, note that Sources changed, Got it to clear.
5. After Got it, the withdrawn card is gone. Nothing is sent.

## Evidence tier

Local real Chrome at 1440 and 320 on owned ports. Fake initiative + fixture login. Not live-account or paid-model acceptance.
