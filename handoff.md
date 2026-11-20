# Group 2 · Current handoff

20 November 2026, Hong Kong. Continue in `/Users/tantalum/.codex/worktrees/proactive-agent-merge-20261117/FYP`, branch `codex/shopping-flight-quotes-20261119`. [PR 134](https://github.com/tantalum666/FYP/pull/134) targets [PR 133](https://github.com/tantalum666/FYP/pull/133). [Product](product.md) · [decisions](decision-log.md).

## Running release

The shared Mac backend runs `4a773f31`. The iPhone 17 Pro Simulator UI runs `c4207e4f` with identical frontend code, and is left showing the Woo/Stripe receipt. Both local rollouts preserved A3 v9 and the store’s account grants. The original Pi is still at `85e6aa94`. [Current acceptance](output/qa/2026-11-19-alice-shopping-conversation/verification.md) · [Pi release](output/qa/2026-11-19-pi-release/verification.md).

## Commerce

The verified Amazon Pay buyer completed a US$14.30 KitchenSmart demo order, with an order number ending in 4202. The original US$1.00 FYP tissue checkout captured through Amazon Pay and produced one completed full refund, independently matched to the same Charge. Stripe's hosted receipt showed US$0.00 net. KitchenSmart exposed no working buyer-cancellation action. eBay developer sign-in still reports pending approval. [Provider receipts and remaining cancellation test](output/qa/2026-11-20-overseas-shopping-sandboxes/verification.md).

Ordinary chat now supports reviewed WooCommerce shopping. Two shippable stationery packs at HK$17 produced a HK$42 quote with HK$8 delivery. Woo then returned HK$12 delivery and HK$46 total. Only a second confirmation paid. Merchant order #17, Stripe test capture and chat follow-up all matched HK$46. The store’s delivery fixture is back at HK$8. [Contract](desk-companion/docs/conversation-shopping.md) · [receipts](output/qa/2026-11-19-alice-shopping-conversation/receipts.json).

An owner-approved flight lookup with no named merchant now uses the read-only Kiwi.com MCP through an official OpenAI Session without a hosted browser. The real 25 November HKG–HND nonstop search returned 11 offers. UO628 was HK$2,006 with one checked bag, above the HK$1,500 limit. The supplier omitted the bag weight and did not confirm the payable total. The public seller page required further access and the carrier prompted for human verification. The Wellcome two-pack shopping quote remains HK$34 before delivery. [Flight acceptance](output/qa/2026-11-19-flight-ledger/verification.md) · [shopping evidence](output/qa/2026-11-19-shopping-flight/verification.md).

The merchant-side HK$34 Link Checkout test passed. The deployed Alice shopping adapter uses the standard Stripe test Visa. The Link Agent Wallet SDK has a simulated-contract check only. On the 20 November follow-up the FYP wallet had no consumer grant. A payment-only device connection was requested again. Link documents US and Canadian customers for hosted SDKs and lists six markets in its FAQ. Hong Kong and mainland China are absent from both. Check the existing FYP profile before creating another request. [Provider receipts and delegated-wallet status](output/qa/2026-11-20-overseas-shopping-sandboxes/verification.md#link-checkout-and-the-delegated-wallet).

The earlier virtual-product WooCommerce test order #13 was HK$34. The reopened order and its captured Stripe test charge matched. Consumer wallet authorization remains open. Duffel’s 32-option incorporation menu omits Hong Kong and mainland China. [Duffel signup](output/qa/2026-11-19-pi-release/verification.md) · [store readback](output/qa/2026-11-19-woocommerce-guest/verification.md).

LetsFG’s public sandbox now covers search, simulated checkout and provider order readback without registration. A Hong Kong to Haneda test returned a HK$34 capture and simulated PNR. Reusing the request key returned the same order. Declining a rise to HK$35.43 released the hold. Singapore Airlines also provides a separate airline-run sandbox requiring an approved developer key. [Booking acceptance](output/qa/2026-11-19-flight-booking-sandbox/verification.md).

## Accounting

The Diagnostics screen shows the UTC platform export, usage-based estimate, local unresolved holds and available HK-day allowance separately. Import a single-day Costs CSV through the operator command in the [managed browser contract](desk-companion/docs/managed-browser.md). Keep account-level exports private. The user's US$20/day authorization expires at the end of 24 November. On 19 November the split is Mac US$10, Pi US$9 and unallocated US$1. The normal US$9/US$9/US$2 split resumes on 20 November. Several previously deleted browser sessions lacked token receipts. Their holds remain visible. After the shopping run, the Mac showed US$9.80 used or reserved and US$0.20 available for 19 November. The shopping quote added US$0.16 in unresolved reservations. Previously closed trials stay closed.

Ordinary chat now supports the complete LetsFG test booking. At HK$34 the quote was still unbooked; after an explicit HK$36.25 reapproval Alice showed simulated PNR `5SMZA7` and matching capture. The same chat reopened the record after backend restart. [Native verification](output/qa/2026-11-19-alice-flight-conversation/verification.md).

**Next step** — Once the owner connects the FYP Link Agent Wallet, use a test spend request for one quoted purchase, obtain wallet approval and independently match the issued credential to the merchant payment. The eBay buyer cancellation separately awaits developer approval.
