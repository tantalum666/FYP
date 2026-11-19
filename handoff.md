# Group 2 · Current handoff

19 November 2026, Hong Kong. Continue in `/Users/tantalum/.codex/worktrees/proactive-agent-merge-20261117/FYP`, branch `codex/shopping-flight-quotes-20261119`. [PR 134](https://github.com/tantalum666/FYP/pull/134) targets [PR 133](https://github.com/tantalum666/FYP/pull/133). [Product](product.md) · [decisions](decision-log.md).

## Running release

The shared Mac backend is `03ca29d3`. The iPhone 17 Pro Simulator has the `02feaffa` native UI, whose frontend source matches the backend release. The original Pi remains at `85e6aa94`, with A3 v9 and verified Google grants. The normal Simulator is left showing its verified test-booking receipt. [Current Simulator and backend](output/qa/2026-11-19-alice-flight-conversation/verification.md) · [last Pi release](output/qa/2026-11-19-pi-release/verification.md).

## Commerce

An owner-approved flight lookup with no named merchant now uses the read-only Kiwi.com MCP through an official OpenAI Session without a hosted browser. The real 25 November HKG–HND nonstop search returned 11 offers. UO628 was HK$2,006 with one checked bag, above the HK$1,500 limit. The supplier omitted the bag weight and did not confirm the payable total. The public seller page required further access and the carrier prompted for human verification. The Wellcome two-pack shopping quote remains HK$34 before delivery. [Flight acceptance](output/qa/2026-11-19-flight-ledger/verification.md) · [shopping evidence](output/qa/2026-11-19-shopping-flight/verification.md).

The [wallet feasibility check](output/qa/2026-11-19-agent-wallet-feasibility/verification.md) identified the consumer Agent Wallet integration. A separate FYP Stripe sandbox has now completed and independently verified two hosted merchant orders, one by test Visa and one by Link Checkout, plus a refusal case. The consumer Agent Wallet has no authorized account in this run. Real card eligibility, live settlement and travel supplier receipts remain open. [Test results and platform choices](output/qa/2026-11-19-test-checkouts/verification.md).

A local WooCommerce test store now has a paid guest order for two test items at HK$34. The reopened order and its captured Stripe test charge matched. Consumer wallet authorization remains open. Duffel’s 32-option incorporation menu omits Hong Kong and mainland China. [Duffel signup](output/qa/2026-11-19-pi-release/verification.md) · [store readback](output/qa/2026-11-19-woocommerce-guest/verification.md).

LetsFG’s public sandbox now covers search, simulated checkout and provider order readback without registration. A Hong Kong to Haneda test returned a HK$34 capture and simulated PNR. Reusing the request key returned the same order. Declining a rise to HK$35.43 released the hold. Singapore Airlines also provides a separate airline-run sandbox requiring an approved developer key. [Booking acceptance](output/qa/2026-11-19-flight-booking-sandbox/verification.md).

## Accounting

The Diagnostics screen shows the UTC platform export, usage-based estimate, local unresolved holds and available HK-day allowance separately. Import a single-day Costs CSV through the operator command in the [managed browser contract](desk-companion/docs/managed-browser.md). Keep account-level exports private. The user's US$20/day authorization expires at the end of 24 November. On 19 November the split is Mac US$10, Pi US$9 and unallocated US$1. The normal US$9/US$9/US$2 split resumes on 20 November. Several previously deleted browser sessions lacked token receipts. Their holds remain visible. After simulator acceptance, the 19 November Mac ledger showed US$9.64 local usage plus reservations combined and US$0.36 available; the new US$0.48 consists of unresolved reservations. Previously closed trials stay closed.

Ordinary chat now supports the complete LetsFG test booking. At HK$34 the quote was still unbooked; after an explicit HK$36.25 reapproval Alice showed simulated PNR `5SMZA7` and matching capture. The same chat reopened the record after backend restart. [Native verification](output/qa/2026-11-19-alice-flight-conversation/verification.md).

**Next step** — Use the ordinary conversation sandbox for the next requested booking scenario. Keep any later live-ticket authorization specific to its merchant, itinerary and final price.
