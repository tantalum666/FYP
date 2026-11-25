# Premise — open a cited local calendar event from finding Sources

## Gap (current main `fc3b8d2`)

Conversation findings show Sources with labels. Gmail can open externally. Open task (#166) and Open memory (#167) cover those citation kinds on open PRs and are not stacked here. A cited **local calendar** occurrence remains plain text: the owner cannot open that event from the finding.

Always-on research expects the owner to inspect cited evidence before deciding. Opening the existing cited occurrence is that inspection for calendar evidence.

## Not this slice

- #158–#167 product (including Open task / Open memory / Follow up / snooze)
- Google Calendar remote refs (`calendar:google:…`) — no EventDetail mapping without a separate import story
- Creating events, sending mail, paid model, live mailbox

## Expected visible journey

1. Fake finding cites a local calendar occurrence (and optionally other kinds as labels).
2. Owner opens Conversation, expands Sources.
3. Owner chooses Open calendar for the local calendar citation.
4. Event details open for that occurrence (calendar day context); finding stays pending. Nothing is sent.
5. Ownership / hide-private / offline-stale still hide the finding card.

## Evidence tier

Local real Chrome at 1440 and 320 on owned ports. Fake initiative + fixture login. Not live-account or paid-model acceptance.
