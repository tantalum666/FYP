# Group 2 · Current handoff

23 November 2026, Hong Kong. Resume in `/Users/tantalum/.codex/worktrees/proactive-agent-merge-20261117/FYP`, branch `codex/alice-booking-calendar-handoff-20261123`. [Integration PR 144](https://github.com/tantalum666/FYP/pull/144) contains the reviewed personal-agent changes. [Product](product.md) · [decisions](decision-log.md) · [complete work history](work-log.md).

## Running software

The original Pi runs stable `08200201`. The normal Mac Web and installed iPhone 17 Pro Simulator have since advanced to the separately verified owner-facing hotfix `0c36c8c4` for global weather, HKD and compact voice controls. Text and hosted-browser delegation use GPT-6.2 Sol. Voice uses GPT-Live-1.1 and the existing A3 v9 sample. The Pi release's assets, authenticated services, physical kiosk, original grants and protected data were read back. The original Pi has rebooted repeatedly for an undetermined reason. [Stable device receipt](output/qa/2026-11-23-api-astra-team/pi-stable-release/verification.md) · [released fare/calendar behavior](output/qa/2026-11-22-calendar-aware-fares/verification.md).

## Parallel development

Five independent worktrees used the OpenAI API's GPT-6.2 Astra with maximum reasoning effort. API commits identify the real contributor. Integration commits identify the coordinating engineer. [Combined acceptance](output/qa/2026-11-23-api-astra-team/verification.md).

| Area | Latest verified behavior | Source and evidence |
|---|---|---|
| Shopping | One cart and shipping selection for multiple products. Changed terms, even at the same total, require new consent. Prepayment substitutions, partial refunds, pending refunds and zero net have distinct receipts. | [PR 145](https://github.com/tantalum666/FYP/pull/145) · [Woo and Stripe acceptance](output/qa/2026-11-23-api-astra-team/basket/verification.md) · [substitution](output/qa/2026-11-23-api-astra-team/basket/substitute-acceptance.md) · [three partial refunds](output/qa/2026-11-23-api-astra-team/basket/partial-refunds.md) |
| Flights | Restore the exact offered option after restart, retain the new lower budget, and check calendar conflicts before fresh approval. A booked itinerary can become one private local event after a separate review. | [PR 148](https://github.com/tantalum666/FYP/pull/148) · [shortlist](output/qa/2026-11-23-api-astra-team/flight-shortlist/verification.md) · [Simulator](output/qa/2026-11-23-api-astra-team/simulator/verification.md) |
| Calendar | Review selected Google changes, preserve separately imported copies and manual edits, and read the last confirmed result in chat. | [PR 143](https://github.com/tantalum666/FYP/pull/143) · [upgrade](output/qa/2026-11-23-api-astra-team/google-review/verification.md) · [ordinary Web](output/qa/2026-11-23-api-astra-team/google-web/verification.md) · [normal chat](output/qa/2026-11-23-api-astra-team/google-review/chat-readback.md) |
| Routines | Skip one selected occurrence, preserve the regular schedule, and read or acknowledge only the current chat's verified quiet-hours updates. | [PR 146](https://github.com/tantalum666/FYP/pull/146) · [clock, scope and restart checks](output/qa/2026-11-23-api-astra-team/continuation/verification.md) |
| Work | The owner can recover a retained run from a fresh chat. A verified CSV can advance one checkpoint. An original approval stays bound to its run. A historical chat that predated durable linkage is recovered through a fresh chat. | [PR 147](https://github.com/tantalum666/FYP/pull/147) · [independent Work journeys](output/qa/2026-11-23-api-astra-team/continuation/verification.md) |

## External services and accounting

The standard storefront is the WooCommerce sandbox. Stripe’s original test-mode charges and refunds were read independently on isolated merchant copies. The separate Link recurring test authorization has an issuer-fixture compatibility issue. eBay’s developer registration review remains pending. [Marketplace evidence](output/qa/2026-11-20-overseas-shopping-sandboxes/verification.md) · [eBay follow-up](output/qa/2026-11-21-shopping-next-step/verification.md). The organisation's billing, keys, customer data and operator allowances are kept outside Git. Previous paid acceptance trials retain their original closed status.

**Next step** — Review the integrated branch against the documented production baseline before choosing a release.
