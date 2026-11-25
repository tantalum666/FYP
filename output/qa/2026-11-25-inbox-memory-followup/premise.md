# Premise — Inbox memory follow-up opens Memory

## Gap (current main `fc3b8d2`)

Individual memory follow-up receipts (`kind: memory_followup`) say “Open Memory to review it” but Inbox offers no action. Morning memory check-ins already have View memories. Sources Open memory is open #167 and was not stacked. ui-copy asks for a relevant action inside the entry.

Owner-approved memory follow-up only — no model call.

## Not this slice

- #158–#174 product (including #167 Sources Open memory and #174 Inbox task Open task)
- Focusing a specific memory fact (requires #167 MemoryPanel wiring)
- Live mailbox, paid model, external send

## Expected visible journey

1. Fixture creates a saved memory, owner-approves a follow-up, and advances past due so an open `memory_followup` notice exists.
2. Owner opens Inbox, expands the Alice remembered receipt.
3. Owner chooses View memories (not Dismiss).
4. Memory opens and shows the saved fact. The notice stays open.

## Evidence tier

Local real Chrome at 1440 and 320 on owned ports. Fixture login + rule memory follow-up. Not live-account or paid-model acceptance.
