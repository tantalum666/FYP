# Native traveller-card checkout and renewed consent

28 November 2026, Hong Kong. A traveller asked the installed iPhone app to find a direct test flight with a minimum checked weight. A second, local scenario examined the same checkout after the seller changed terms following a card authorization.

## Ordinary iPhone checkout

The iPhone 17 Pro Simulator ran the regular build `2f20e049` against the enrolled Mac. Alice used GPT-6.2 Sol and the existing read-only flight Function. The traveller requested a synthetic adult on HKG–PEK on 18 December with at least 15 kg of checked luggage. The first direct offer was HK$2,286.23. A cheaper fare was labeled as awaiting a verified baggage-inclusive total.

Selecting the first flight returned ND4190, 06:45–09:59, with one 23 kg checked bag. One tap on the named test Visa confirmation produced a supplier reservation. The app displayed the electronic ticket number, the airline locator and the HK$2,286.23 authorization. A typed follow-up in the same conversation brought back those same details. The original synthetic booking detail independently reported CONFIRMED and issued. The Stripe intent for the same amount and currency was in test mode with `requires_capture`. The supplier account contained two test orders before this itinerary and three after the follow-up. Ticket and payment identifiers stay in the private operator record.

## Changed terms after a payment session opens

At baseline `8696b231`, the original private review correctly paused when a supplier reduced the included bag below the traveller’s requirement. In a regression replay, restoring that bag and merely asking for status submitted the booking against the old consent. The failed assertion observed one supplier booking before the traveller had made a new decision.

Application `ff7abaef120c1e5324396a59502080027d976f60` records that the original approval was invalidated. Unchanged status reads retain the review version. A newly matched offer is shown for explicit reconfirmation. A second change during that confirmation pauses ticketing again. The existing verified test intent and prebook are reused. A known difference in the original processor amount, currency or collected amount also stops ticket submission. Older rows that saved only the material-change reason follow the same rule. The public view shows the latest verified supplier fare and baggage separately from the earlier authorization.

| Browser observation with an isolated supplier and processor | Supplier orders | Original prebooks |
| --- | ---: | ---: |
| HK$1,200 / 23 kg was authorized, then the fare became HK$1,350 with 10 kg. The new fare was labeled as awaiting a qualified total and the original hold remained visible. | 0 | 1 |
| The seller restored HK$1,200 / 23 kg. The traveller clicked Check original booking and saw Reconfirm original fare. | 0 | 1 |
| The traveller pressed the new confirmation. The app displayed the ticket, locator and original hold. | 1 | 1 |

Seven focused backend cases cover normal authorization/settlement readback, losing and restoring baggage, a changed fare at the second confirmation, an unpaid original intent, legacy data, service restart and three payment-amount/currency cases. Stale decision versions, repeated status and duplicate confirmations were exercised on the same order. The production frontend compiled and passed type checking, the affected Python modules passed lint and the public diff was scanned for actual credentials and receipt IDs. The rendered replay used the actual checkout UI with synthetic external responses. It made no charge or booking on an external platform.

## Normal release

Mac and iPhone Simulator both serve `ff7abaef`. The running Mac reported the staged frontend revision and retained the original owner sessions, private configuration, app grants, A3 v9 voice profile and GPT-6.2 Sol. All 145 existing database tables survived. The in-place iPhone upgrade preserved the saved Mac server address, seven durable data checks and all 81 packaged public files. During the original native checkout the app reported `paired=false` for its separate device token. The desk returned an authenticated owner session through its existing loopback sign-in. These observations identify how the Simulator accessed the desk. The payment frame on the normal desk remains restricted to static resources. The original Pi is outside this release.

After the release, three successive background Gmail source reads succeeded at 00:53, 00:58 and 01:03 Hong Kong time during the configured quiet period. These timestamps were read from the running desk and are independent of the last time a suggestion was generated. No lock-screen test alert was sent.

Self-review covered the user journey, the complete executable diff, normal and restored confirmations, the original prebook and intent identity, and the versioned database update before an external booking request. The supplier documents one idempotent booking per prebook and Stripe distinguishes a card authorization from collection. [Nuitée booking contract](https://docs.nuitee.com/reference/post_flights-bookings) · [Stripe authorization and capture](https://docs.stripe.com/payments/place-a-hold-on-a-payment-method).

Read the project entry, current product and handoff sections, the recent traveller-card decisions, the personal-agent research index, the previous sandbox acceptance and the affected flight and commerce paths. Updated the live flight contract, product, handoff, decisions and work log. The test ticket was issued on a supplier sandbox. Final card collection and production traveller-card authority have separate evidence requirements.
