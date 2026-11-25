# Premise — proactive finding snooze

## Gap (current main `fc3b8d2`)

Conversation findings offer Sources and Got it only. Got it permanently dismisses. There is no owner-controlled deferral of the same cited finding. Quiet hours can hold *delivery* of new notices, but an already-visible finding cannot be put aside and raised again later without creating a follow-up task (#161, open) or discarding it.

Memory follow-ups and moments already have snooze / Not now. Initiative findings do not. Always-on research expects Alice to interrupt once when useful and let the owner defer without losing evidence.

## Not this slice

- #158–#160, #162 harness/product elsewhere
- #161 Follow up → bound private task (open; not stacked)
- Live mailbox, paid model, send, merge/deploy

## Expected journey

1. Fake finding appears in Conversation with Sources.
2. Owner chooses Remind me later (one hour).
3. Finding leaves the pending cue; same id retained with snooze_until.
4. Fake clock advances past snooze_until; finding returns to pending with same sources; one paced notice may fire when quiet hours allow.
5. Got it still dismisses permanently. Replay/idempotence, hide_private, paired, stranger, revoke fences hold. Nothing is sent.
