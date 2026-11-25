# Premise — home initiative cue → review Sources in Conversation

## Gap (current main `fc3b8d2`)

When Alice raises a proactive finding, the home surface shows one Alice cue while Conversation is collapsed. That cue only offers **Got it**, which permanently dismisses. The owner has no home-surface control that opens Conversation to read **Sources** before deciding. Inbox already offers **View in conversation** (and expands via `conversationRequest`). Conversation already shows Sources and Got it. The always-on research path expects: interrupt once → open conversation to see evidence → acknowledge independently.

Open #158–#163 do not close this: #161/#163 act inside an already-open finding card; #160 is mail-reply reminder; #163 is Remind me later (API + source contract only).

## Not this slice

- Follow up task (#161), Remind me later (#163), mail reply reminder (#160)
- Live mailbox, paid model, send, merge/deploy
- Changing quiet-hours / delivery caps / ownership fences

## Expected visible journey

1. Fake high-importance finding is pending; home (Conversation collapsed) shows the Alice initiative cue.
2. Owner chooses **View in conversation** on the cue (does not dismiss).
3. Conversation expands; the finding card shows Sources; owner can open Sources.
4. **Got it** on the finding still dismisses permanently. Cue Got it remains a quick dismiss without claiming mail was sent.
5. Ownership / hide-private / offline-stale still hide the cue. Nothing is sent.

## Evidence tier

Local real Chrome at 1440 and 320 on owned ports, plus a frontend source contract. Fake initiative + fixture owner login. Not live-account or paid-model acceptance.
