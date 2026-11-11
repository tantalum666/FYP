# Staple purchase card

## Reviewed integration — 11 November 2026

Under Work & tools → Purchase preferences. Confirmation, updates and offer approval require expected_version from the reviewed card/offer. A stale screen cannot approve a later version. Offer operation identity includes card_id. Private-hide and current-session checks apply, including inside writes. same_spec_cheaper requires reference_total_minor (original item including shipping); a substitute must be below that original total and within budget. A local receipt remains explicitly not a live order. [Review evidence](../../output/qa/2026-11-11-grok-review/verification.md). Runtime rollout is separate.

11 November 2026. Offline slice for the second acceptance in the [research index](../../research/personal-agent-research-index.md): before any order, the owner confirms the item, quantity, allowed merchants, a budget that already includes shipping, whether a cheaper same-spec substitute is allowed, and an address label. A later offer is checked against that card. This is not a store account, a payment, or a live order.

Grok Bot chose this because the open pull requests already cover Work re-show and continue, the folder-job clock, browser takeover, memory follow-ups, trip quotes, and saved or scheduled skills. Codex pull request #97 covers the shared Alice UI, chat attachments, Gmail and Outlook drafts, and voice preferences. The shopping fixture journey still tracks cart and shipment events. It does not store the confirmed card those events would have to match.

## What the owner can do

The card starts as a draft. Offers are refused until the owner confirms it. Confirmation, updates, revocation, approval, and a fixture receipt are owner-only. A paired display cannot create or approve a card.

An update writes only the fields present in the request. A JSON null does not clear a saved field. Omitted fields stay, including SKU, quantity, merchants, and the address label. The label is a short token such as `home`, not a street address.

Tokens are stored in lowercase so `Tissue-Box` and `tissue-box` are the same item. That is the same case-folding rule used so two fixture names cannot fork on a case-insensitive disk. This slice does not write fixture files.

A matching offer creates one task for the card and waits for a fresh approval. Repeating the offer does not create a second task. Full access does not approve it. A refused offer, including a total over the budget or a substitute that is not cheaper, leaves the task uncompleted.

Changing the card bumps its version. An approval for the previous version cannot be reused, and a receipt cannot be recorded against it until the offer is checked and approved again. A different offer is not covered by an older approval.

`interrupt: "write"` commits nothing about the offer and is not success. `interrupt: "open"` keeps one task in `opened` and does not approve or notify. The same operation id then finishes that one task. Holding an approval or a receipt writes nothing further until the same operation is retried. A second receipt id conflicts and the first receipt stays.

The task is never marked completed. The receipt note says it is not a live purchase. A later offer can still be checked on that same card; an over-budget offer is refused and the recorded receipt stays. Every response sets `purchased` and `live_purchase` to false.

Quiet hours hold the decision notice. `Runtime.tick` releases it once, after the existing tick work. The portable backup still has `mailbox_bundle`, `shopping_bundle`, and `offline_calendar_bundle`. This slice does not add a purchase bundle.

## Where it lives

- `desk-companion/backend/desk/purchase_cards.py` — card, offer check, approval, receipt, quiet notice
- `TaskService.insert_task` and `TaskService.apply_action` — same task transaction, no second task service
- `POST /api/purchase-cards` and the confirmation, update, revocation, offer, approval, and receipt routes
- Tasks page, below the list, hidden on the display surface: `PurchaseCardPanel`

## Codex merge note

Append `purchase_cards.release_quiet_notices()` at the end of `Runtime.tick`, after `voice.work.cleanup()`. Do not insert it between mailbox, shopping, and offline calendar. Do not drop those three bundles from `exchange.py`. The tasks page mounts this panel at the bottom of the list, not beside the saved-skills panel. A live merchant, payment, or address book is still out of scope.
