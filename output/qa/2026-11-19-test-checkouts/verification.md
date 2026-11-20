# Test cards for shopping and travel

19 November 2026, Hong Kong. The FYP merchant-side checks used a newly provisioned, isolated Stripe sandbox with the owner's approval. The test buyer, phone and merchandise were fictional. The original user Link wallet, real cards and normal Alice payment permissions were outside this run. No OpenAI model request, shipment, airline booking or money movement occurred.

## What was exercised

| Exercise | Observed result |
| --- | --- |
| Official Stripe API Visa success fixture | The HK$34 test PaymentIntent succeeded. A separate charge read returned captured, paid and test mode. |
| Standard card through a hosted Checkout Session | The test merchant offered two HK$17 stationery packs. Checkout returned to the merchant. Separate GETs matched the order reference, its HK$34 amount and currency, the completed/paid session, the succeeded PaymentIntent and its captured charge. The charge method was `card`. |
| Link through a different hosted Checkout Session | Checkout and the separate Link window both identified themselves as sandbox. A fictitious sandbox buyer used the published test Visa. Stripe recorded the payment method as `link`. Independent merchant reads matched the two units, HK$34, complete/paid Checkout, succeeded PaymentIntent, captured charge and `livemode=false`. |
| Official decline fixture | Confirmation returned HTTP 402 with `card_declined`. Reading the same PaymentIntent returned `requires_payment_method` and zero received. |

The official Link Agent Wallet CLI reported no authenticated FYP consumer wallet. The pending device authorization expired without an approval. An Agent Wallet can issue a test virtual card for a test spend request after the eligible consumer connects their wallet and approves it. A Stripe merchant account manages the merchant sandbox. Stripe Checkout supports a separate simulated Link buyer under a sandbox publishable key. Those experiences use different authorizations. This run established buyer-to-merchant Link **Checkout** acceptance and did not obtain an **Agent Wallet** spend credential. [Link Agent Wallet quickstart](https://docs.link.com/quickstart/overview) · [testing Link at a merchant](https://docs.stripe.com/payments/link/payment-element-link) · [Stripe test cards](https://docs.stripe.com/testing).

The public Stripe sample first displayed a test-mode session and test card fields, but did not return a completed order in the embedded browser. Its console reported an unmounted verification component. No payment result was claimed for that sample. For the dedicated sandbox, the current Stripe API rejected an obsolete method-selection field before creating the first API PaymentIntent. The accepted request used the sandbox's configured methods. The account identity, official test Visa object's test flag, and payable objects' test flags were checked. The dedicated sandbox did not grant balance-report access. Verification instead used the actual merchant orders, payment intents and charges. The hosted tests used the merchant's official Stripe checkout. Sensitive keys, addresses, claim and checkout links stay private.

## Which platforms admit test cards

| Platform and environment | Suitable acceptance | Prerequisite or boundary |
| --- | --- | --- |
| [Stripe Checkout](https://docs.stripe.com/testing) | Card and Link checkout, success, decline and separate charge readback | Create the checkout under sandbox keys. This is the platform actually exercised here. |
| [Shopify dev or test store](https://help.shopify.com/en/manual/checkout-settings/test-orders/processing-test-order) | Cart to test order using Shopify Payments test mode or the test gateway | The store operator chooses the test gateway. Each gateway has its own permitted test inputs. |
| [WooCommerce with its Stripe extension](https://woocommerce.com/document/stripe/customer-experience/testing/) | Use an isolated shop in Stripe test mode, return to the order received page and reopen the store order | Use test keys and test cards for that extension. Order emails and other shop integrations need the operator's test configuration. |
| [Duffel Airways and Duffel Hotel Group](https://duffel.com/docs/guides/paying-with-customer-cards) | Test flight or lodging orders, including card authentication and declines | The developer needs a Duffel testing access token. Use the designated suppliers and the fixtures for the exact product. The [Duffel Payments fixtures](https://duffel.com/docs/api/overview/test-mode/test-card-numbers) are for payment collection. Duffel Cards has its own card/3DS scenarios when paying travel suppliers. The test airline's prices and schedules are synthetic. No Duffel order was executed in this run. |
| [Booking.com Demand accommodation sandbox](https://developers.booking.com/demand/docs/getting-started/sandbox) | Partner test inventory and booking workflows | The accommodation flow involving payments requires a real card and temporary charges. It is outside this test-card-only exercise. |

The previously verified Kiwi MCP returns a booking link to the ordinary seller checkout. The Wellcome and airline pages checked for quotes are also regular consumer sites. A card tested in a payment processor's sandbox does not establish that it can be submitted to those production sites. An independent travel acceptance needs the provider's test order reference, and any test ticket document it actually returns. A Stripe charge alone supplies neither.

## Reproducing the independent read

The new [read-only verifier](../../../desk-companion/scripts/verify_stripe_sandbox_checkout.py) uses the private FYP Stripe CLI profile, a private file containing the merchant checkout ID, the expected merchant order reference, minor-unit amount and currency. It checks the owning account, allows only test session identifiers, and retrieves Checkout, PaymentIntent and Charge independently from the official API. A wrong amount and a synthetic live reference were rejected. Ruff passed. Two existing hosted orders were read without creating new charges. [Sanitized results](receipts.json).

Read AGENTS.md, the current product, handoff and decision sections, the personal agent research index's wallet and commerce entries and the preceding wallet feasibility check. This adds an operator QA command and evidence. It does not deploy a new payment tool. The normal runtime remains at `85e6aa94`. Next travel acceptance requires a Duffel test token and a test supplier order, keeping source-specific card collection, flight booking references and any test ticket evidence distinct.
