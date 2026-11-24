# Partial refunds on one Stripe test capture

The 23 November 2026 independent check of `2686b0dce63faed0c0c870fe50e0255790c2bf0c` verified **three merchant-issued partial refunds on a new HK$25.00 test order, ending at HK$0.00 net**. The ordinary Alice message endpoint reopened each intermediate result after restarting the backend. The isolated WooCommerce merchant and Stripe API independently confirmed the same amounts. [Sanitized observations](partial-refunds.json).

| Clone order #31 | Original capture | Cumulative settled | Pending | Remaining net | Woo state |
| --- | ---: | ---: | ---: | ---: | --- |
| Original payment | HK$25.00 | HK$0.00 | HK$0.00 | HK$25.00 | Processing |
| First refund of HK$5.25 | HK$25.00 | HK$5.25 | HK$0.00 | HK$19.75 | Processing |
| Second refund of HK$7.75 | HK$25.00 | HK$13.00 | HK$0.00 | HK$12.00 | Processing |
| Third refund of HK$12.00 | HK$25.00 | HK$25.00 | HK$0.00 | HK$0.00 | Refunded |

The clone’s test gateway and configured Stripe account were checked before payment. The separate order used the official test Visa and a synthetic customer. Each merchant action called WooCommerce’s existing payment gateway refund function for the specified partial amount. An independent reader checked the Woo refund children and their parent/currency, original captured Charge, PaymentIntent, and all three individual Stripe Refund objects. The resulting payment activity was one new test intent, one captured test charge and three distinct refunds tied to that charge. All three real refund reads returned `succeeded`. [WooCommerce refund behavior](https://woocommerce.com/document/woocommerce-refunds/) · [Stripe refunds](https://docs.stripe.com/refunds).

**Pending was exercised with a local replay.** A copy of the first verified HK$5.25 settlement gained a simulated HK$7.75 pending Refund. The reader saw one duplicate settled Refund across two pages. Alice reported HK$25.00 gross, HK$5.25 settled, HK$7.75 pending and HK$19.75 net on both sides of a backend restart. Four separately isolated replays supplied a different Stripe account, wrong Charge currency, wrong Refund currency or a Refund tied to another Charge. All four preserved the previous values as explicitly last verified and disabled cancellation. The wrong-account case stopped after the account GET. All reconciliation replay traffic used GET requests. [Replay results](partial-refunds.json).

The checkout needed to create #31 used the ordinary owner-approved API and a scripted Sessions quote with zero paid model calls. This supplement exercised the receipt path and did not repeat the earlier native checkout. Clone #17 stayed processing at HK$46.00 with zero refunds, and clone #29 retained its one HK$32.00 full refund. The normal merchant matched its original order, stock, delivery and plugin controls. The isolated merchant was stopped after verification.
