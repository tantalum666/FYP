# Premise — Inbox calendar update opens Calendar

## Gap (current main `fc3b8d2`)

Calendar update receipts (`calendar_deadline`, `calendar_conflict`, `calendar_decision`, `calendar_cancelled`) land in Inbox with only Dismiss. ui-copy asks for a relevant action inside the entry. Sources Open calendar is open #168 (finding citations) and was not stacked.

Fixture notice only — not live Google or mailbox.

## Not this slice

- #158–#175 product (including #168 Sources Open calendar and #170/#172 Today/Tasks)
- Opening a specific occurrence’s Event details
- Live Google, live mailbox, paid model, external send

## Expected visible journey

1. Fixture publishes an open `calendar_deadline` notice (local rule/fixture copy; no provider).
2. Owner opens Inbox, expands the Calendar update receipt.
3. Owner chooses View calendar (not Dismiss).
4. Calendar opens. The notice stays open.

## Evidence tier

Local real Chrome at 1440 and 320 on owned ports. Fixture login + published local notice. Not live-account or paid-model acceptance.
