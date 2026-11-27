# Alice traveller-card flight checkout

27 November 2026, Hong Kong. The owner registered with Nuitée and asked to continue in their signed-in Chrome. Flights was selected in the existing Connect sandbox. The test used Nuitée Air, the provider’s published adult passenger example, reserved contact information and Stripe’s official test Visa.

## What the traveller saw

In the ordinary Alice composer the traveller explicitly requested one adult, HKG to PEK, a direct flight and at least 15 kg of checked luggage. The existing OpenAI text Session on GPT-6.2 Sol invoked the read-only `live_flight_search` Function. The traveller selected a direct morning service at HK$2,288.39 with one 23 kg bag included. A cheaper option lacked a verified bag-inclusive total. Alice showed the itinerary, baggage and tax-inclusive total again before the single test Visa approval.

| Check | Independently observed result |
| --- | --- |
| Original booking detail | Confirmed reservation, airline locator and a 13-digit electronic ticket marked issued. |
| Merchant's payment field | The booked order reported its payment completed. |
| Original Stripe payment | Test mode, HKD 228,839 minor units, still `requires_capture`. Alice showed the authorized hold and left collection pending. |
| Read the original ticket again | After restarting the desk service, a new message in the original Chrome conversation returned the same ticket, locator and hold. The supplier received one order for that chat itinerary. |
| Financial scope | Two distinct synthetic itineraries were issued during this acceptance. One was the initial protocol check and one came through Alice. Both original card intents still showed a hold on independent read. Real bank charges and production airline tickets were zero. |

The comparison uses the supplier’s booking-detail endpoint and an independent read of the payment processor’s original intent. The scoped test browser read did not disclose a captured amount. No manual capture or second payment was submitted. Provider credentials, processor identifiers, passenger data, original receipts and booking locators stay in the operator’s private store. [Booking detail](https://docs.nuitee.com/reference/get_flights-bookings-bookingid) · [Flight booking and payment methods](https://docs.nuitee.com/reference/post_flights-bookings) · [Stripe authorization and capture](https://docs.stripe.com/payments/place-a-hold-on-a-payment-method).

## Corrections and failure checks

- The supplier rejected an invented surname in the initial protocol check. Its published passenger fixture passed. The prebook’s order reference contains a nested order ID. The adapter now checks that ID before releasing the protected card session.
- An early build displayed the previous seller’s name. The review now names the supplier attached to the original offer. The first payment frame did not deliver a payment method. An independent read showed the original intent still waiting for a method and no order for the chat itinerary. Switching to a separate loopback web origin allowed the existing intent to complete authorization. This origin serves only the two payment-frame resources.
- Seven focused tests cover owner and chat isolation, explicit supplier selection, fare and bag changes through prebook and after a hold, duplicate submission, recovery, processor/airline disagreement and isolating the browser frame from the desk API. The existing either-airport search regression passed separately. Frontend type checking, production compilation, Python lint and a scan for actual operational secrets and receipt identifiers passed.
- The normal flight search and existing LetsFG checkout retain their provider. Only an explicitly selected Nuitée sandbox request can select its synthetic inventory. The new payment path accepts one documented synthetic adult and a fixed test Visa. The account’s prebook offered `TRANSACTION_ID` and `ACC_CREDIT_CARD`. The traveller path uses the former. The supplier documents separate enablement of direct traveller-card charging, and formal production Flights activation. [Access by environment](https://docs.nuitee.com/docs/getting-access-to-flights).

## Release and scope

The chat checkout was exercised on `0023d662`. Final source `2f20e0497e2191e0f74fd4a5fc4d4ca0fcc457d7` adds the iOS transport setting and one targeted regression check. The final runtime changes were self-reviewed against main `0115cce1`. The Mac upgraded from `949d76df` through these two revisions. Its HTTP build identity matched the staged manifest. The original operator session, connected-app versions, GPT-Live-1.1 / A3 v9, GPT-6.2 Sol and managed-browser configuration passed comparison. Both database snapshots contained 145 tables at schema version 3. The primary page confines the Stripe SDK to the payment frame. A request to the same frame hostname for a desk API path returned 404.

The normal iPhone 17 Pro Simulator received the same bundle. CoreSimulator relocated the private data directory during installation. The first check rolled back and verified the original data. The confirmed installation preserved all seven durable-file checks, the saved Mac server address and the hashes of all 81 public files. The user-facing airline transaction above was exercised in Chrome. The original Pi and physical iPhone were outside this sandbox credential rollout.

On an isolated iPhone Simulator, the original package could open the app but its WebKit frame did not load the dedicated loopback host. An otherwise identical package with a transport exception for the exact `nuitee-card.localhost` hostname received the frame’s validation reply. The final package repeated this exchange from the secure Capacitor origin using an empty test message. It rejected the message before loading a payment method or requesting a transaction. The new eighth regression check also verifies that this host exception includes no subdomains or global web transport override. [Apple local network transport settings](https://developer.apple.com/documentation/bundleresources/information-property-list/nsapptransportsecurity/nsallowslocalnetworking).

The implementation reuses OpenAI Sessions/Functions, the existing scoped flight checkout, optimistic review versions, the desk Vault and the normal release tooling. Dependency locks and the SQLite schema stayed the same. Project entry, active travel requirements, handoff and the latest flight decisions were read, together with the personal-agent research index, prior traveller-card assessment, existing flight contract and operator instructions. The product contract, supplier guide, operator guide, research index, decisions, work log and handoff reflect this acceptance.

The original test authorization is available for another read if the payment processor records collection. Enabling actual traveller-card delegation requires separate supplier authorization and validation of traveller consent, bank authentication when required, collection and carrier-issued ticket details.
