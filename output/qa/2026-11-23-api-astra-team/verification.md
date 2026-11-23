# Group 2 · Parallel API development

## Source and scope

Restored the project from the 22 November calendar-aware flight release at `412721b2`. The source review covered AGENTS.md, product.md sections on ordinary chat, flight reviews and shopping, handoff.md, the 22 November flight decision, the flight conversation specification, scoped commerce reviews, existing calendar storage and the ordinary conversation view. Deployment on the previous day and closed provider trials retain their existing evidence. The API contributor and the integrating engineer use separate worktrees.

## Booked flight to local calendar

[API Astra PR 143](https://github.com/tantalum666/FYP/pull/143) contains the private itinerary projection at `e06c5149`. The OpenAI Responses receipt returned model `gpt-6.2-astra`, reasoning effort `max`, standard service, and a completed response with implementation and tests. The first bounded request ended on its output limit and supplied no code. The integrating engineer corrected the Python package imports and reused the provider's existing PNR validator. All 33 projection cases passed in the API worktree, including a transfer crossing the date line, a desk DST fold, an uncertain airport time, an approved fare increase and exclusion of private receipt details.

In ordinary chat, the integrating branch reopened the supplier record before preview and before saving. The five added HTTP journey tests passed with an isolated desktop database, authenticated owner and synthetic LetsFG transport. A 19:00 Hong Kong departure and 22:10 Tokyo arrival became 19:00–21:10 on the Hong Kong calendar. The preview wrote zero events. Confirmation produced one private event with no reminders, and repeat confirmation found the same event. Deleting the saved event, then replaying the request, returned the removed status. An expired or dismissed draft, a changed capture, a privacy switch during the supplier read, a second login and forgetting the original conversation all prevented an unauthorized new write. The existing flight had one original submission. Frontend TypeScript and the focused Python lint checks passed.

A fixture at the official Sessions/Functions protocol boundary exercised two additional cases. A colloquial request with FR4315 produced the existing local draft via the named Function, and the model received only the minimal review acknowledgement. Unknown flight numbers and injected confirmation/time arguments produced zero calendar writes. These were replayed protocol calls.

The [isolated iOS 26.5 Simulator journey](simulator/verification.md) used real Home controls and the Calendar screen at integration commit `bc2796cc`. Saving and replaying returned the same event ID and version 1. Both the screen and the independent SQLite reader found exactly one event. The native bridge also read a 14-second synthetic Google refresh followed by a successful health check. A later regression checked an appointment arriving after flight preview: the original Save returned a new conflict review and only a second consent saved the trip. Private appointment text stayed on the desk.

Cost and credential evidence are retained privately by the operator. Published changes contain no owner credit amount, credentials, actual account identifiers or production database.

## Mixed WooCommerce baskets

[API Astra shopping PR 145](https://github.com/tantalum666/FYP/pull/145) adds exact per-item terms to the existing WooCommerce checkout. At `3c5358d1`, two HK$4 tissue packs and one HK$17 item with one HK$8 delivery produced a HK$33 quote. The cloned merchant reduced delivery to HK$7. A second owner decision authorized HK$32. Test order #29, its Stripe PaymentIntent and one captured Charge agreed. One complete refund returned HK$32 and restored the two tissue packs. Replaying an ambiguous acknowledgement preserved the same order and charge. The original historical single-item order #17 reopened at its historical HK$46. An equal-total SKU substitution was prevented before payment; the generic buyer message at this commit is being refined. [Independent Web, Woo and Stripe test evidence](basket/verification.md).

## Scoped Google Calendar refresh

At `401e0fb2` the authenticated owner can review changes to imported copies. The API author repaired a reproduced backup conflict when two grants shared a remote occurrence ID, kept an inaccessible 404 copy, recovered an original local ID on a later verified read and preserved a genuine manual edit on upgrade. Two independent calendar accounts and the previous version's actual SQLite writer were reproduced with synthetic Google HTTP. [Differential results and reproducible cases](google-review/verification.md). The ordinary [Web settings journey](google-web/verification.md) independently verified the approved result in SQLite and after reopening the UI. The combined integration at `efd0b064` passed the frontend typecheck and targeted normal-chat Function and single-item compatibility checks.

## Installed stable release and new draft branches

The original Raspberry Pi now runs the same stable `08200201` release as the normal Mac and iPhone Simulator. Its physical kiosk, software, original Google grants and A3 v9 were independently read back after a tested rollback. [Physical Pi evidence](pi-stable-release/verification.md). New API development is reviewed on separate GitHub branches.

The shop aftercare revision `2686b0dc` reconciles distinct partial refunds. In an isolated merchant, order #31 was charged HK$25.00 and three separate Stripe test refunds returned HK$5.25, HK$7.75 and HK$12.00. Reopened net amounts were HK$19.75, HK$12.00 and HK$0.00. The pending-refund evidence is a synthetic replay. [Refund receipts](basket/partial-refunds.md).
