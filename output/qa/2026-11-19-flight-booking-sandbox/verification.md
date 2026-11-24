# Flight booking from Hong Kong in the LetsFG public sandbox

19 November 2026, Hong Kong. The owner asked for a usable alternative after Duffel’s registration form omitted Hong Kong and mainland China. We selected the public LetsFG flight sandbox for FYP booking-flow acceptance. It accepts requests from the project without a personal account, card details or API key. A second provider track is Singapore Airlines’ own KrisConnect test environment. The existing agent continues to use Kiwi for real public fare research. [Structured receipts](receipts.json) · [LetsFG sandbox](https://letsfg.co/developers/docs/api-sandbox/index.html) · [previous Duffel check](../2026-11-19-pi-release/verification.md).

## Booking results

Acceptance required a fresh provider read using the booking ID, matching the selected offer, displayed amount, currency, terminal state and reservation reference. A second booking had to decline a price increase and show that the pending hold was released.

| Operation | Observed provider result |
| --- | --- |
| Search | Anonymous sandbox POST for one adult, 25 November 2026, HKG to HND. The response contained 50 offers. The selected nonstop example was HK$34. Its baggage figures were estimates. This case used the base fare and did not certify a checked weight. |
| Successful booking | Submitted the provider’s fictional passenger and requested its success scenario. HTTP 202 authorized HK$34 on the simulated Visa ending 4242. The booking progressed through card issuance and processing. At 21:22 HKT it reached `completed`. A separate process reopened the original booking and matched the offer, HK$34 capture and simulated PNR `YT7A93`. |
| Duplicate submission | After completion, replayed the same success request with the original idempotency key. The provider returned HTTP 202, marked the request as a duplicate and returned the same booking ID in the completed state. |
| Price increase | A separate booking paused with an offer to raise HK$34 to HK$35.43. A decline for that question round returned HTTP 200. An independent GET found `failed`, an empty PNR, a null capture, and an explicit provider message that the hold was released. The record still carries the original HK$34 in its held-amount field after release. |

The creation response also had an embedded normalized fare of 31.58. The displayed price, authorization and final successful capture all agreed on HK$34. The verifier binds to the approved displayed total. The provider designates this inventory, Visa and PNR as simulated. Actual money, airline inventory consumption, emails and airline-issued tickets were zero. No publicly read back status contains a confirmed checked-bag weight, or substitutes for a priced real-market itinerary. [Provider booking states and test data](https://letsfg.co/developers/docs/api-sandbox/index.html).

## Independent verification in FYP

The [operator verification command](../../../desk-companion/scripts/verify_letsfg_sandbox_booking.py) makes one GET to the fixed LetsFG sandbox host. Keep the provider booking ID and the expected quote in a private JSON file. LetsFG says possession of a sandbox booking ID is sufficient to retrieve its status. The public receipts omit the booking IDs, idempotency keys and passenger data. For a success the expectation uses `outcome=completed`. For a rejected increase use `outcome=price_change_declined`.

From the `desk-companion` directory run the following command, substituting the path to your private record.

```sh
.venv/bin/python scripts/verify_letsfg_sandbox_booking.py /path/to/expected-booking.json
```

The expectation fields are `booking_id` from the accepted submission, `search_id`, `offer_id`, `approved_amount` and `currency` from the selected quote, plus `outcome`. The command reports the matched simulated capture, reference or hold release. Both independent provider reads succeeded. Eight new refusal checks used saved provider responses and changed one condition per case, including a mismatched offer, the wrong price and a decline without evidence of release. Three malformed provider replies were also rejected. The final formatting and malformed-reply handling reproduced both independent outcomes against the saved replies. The script passed the project linter. No prior local suite, paid model trial or previous shopping checkout was repeated.

## Airline-owned alternative

Singapore Airlines’ Flight Booking page links its free Sandbox to a public explorer. We opened the Flight Booking operations and inspected the search form. It requires a developer API key and the input was empty. The first registration page asked for a username, display name, email, password and a CAPTCHA. That page had no company-country dropdown. SIA retains control over account and API-subscription approval. FYP did not receive a key or an SIA test reservation during this check. Choose **Sandbox** for simulated data. SIA describes its separate **Trial** plan as using production data. [Flight Booking plans](https://developer.singaporeair.com/api_flight_booking) · [registration](https://developer.singaporeair.com/member/register) · [access conditions](https://developer.singaporeair.com/terms_of_use).

The Stripe Directory plugin returned no profiles for the two booking-sandbox and airline-booking queries. We used provider documentation and public forms for discovery. Norba publishes a test Visa, while its developer account requires someone authorized to bind a business. Amadeus’s current portal records the retirement of its former self-service access. Neither is a prerequisite for the LetsFG acceptance. [Norba terms](https://norba.io/company/terms) · [Amadeus portal](https://developers.amadeus.com/api-catalog).

## Scope

Read the project instructions, current product and handoff, recent commerce and deployment decisions, the commerce research entry, previous sandbox receipts, current agent tool boundaries and the existing Stripe readback command. Compared the published LetsFG search, booking, polling, refusal and idempotency contracts with live provider responses. Updated the entry points, product, research, decisions, work log and handoff. This check ran against the external vendor sandbox from the operator’s computer. No production booking Function or runtime deployment was part of this change.
