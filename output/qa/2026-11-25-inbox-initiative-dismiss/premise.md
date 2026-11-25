# Premise — Inbox Dismiss clears bound initiative findings

## Gap (current main `fc3b8d2`)

Inbox shows an initiative notice with **View in conversation** and **Dismiss**. Dismiss only marks the notice row dismissed. Pending findings stay pending, so the home cue and Conversation still show the same suggestion. Owner-facing Dismiss therefore does not mean Got it.

Reproduced on pristine main: after `POST /api/notices/{id}/dismissals`, `initiative.current()` still had the finding and the cue remained.

Open #158–#164 do not fix this. #164 opens Conversation from the home cue; #161/#163 act on the finding card; none change Inbox Dismiss semantics.

## Not this slice

- Follow up / snooze / cue View in conversation product from open PRs
- Live mailbox, paid model, send, merge/deploy
- Weakening ownership on notice routes (remain owner-gated)

## Expected visible journey

1. Fake finding is delivered; Inbox shows “Alice noticed something” (or batched title).
2. Owner opens Inbox, expands the notice, chooses **Dismiss**.
3. Notice is dismissed; bound pending finding(s) for that `notice_id` are dismissed.
4. Conversation and home cue no longer show that finding. Replay of the same operation id is idempotent.
5. Got it on one of two findings in Conversation still leaves the other (unchanged independent path). Nothing is sent.

## Evidence tier

API fixture + local real Chrome at 1440 and 320 on owned ports. Not live-account or paid-model acceptance.
