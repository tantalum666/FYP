# Group 2 · Explicit choice between a flight and a shop

The test used a newly signed-in owner, the original Kiwi result, a selected LetsFG total and a separate Woo sandbox cart in the same chat. Each row used a fresh local desk and simulated merchant and flight providers. The ordinary message endpoint received “yes”.

| Request | Parent `689d1d8e` shop submissions | Corrected shop submissions |
| --- | ---: | ---: |
| Plain message with no reference | 0 | 0 |
| Composer-inferred shop reference | 1 | 0 |
| Explicitly selected shop card | 1 | 1 |

The flight supplier received zero submissions in all six cases. Replaying the explicit choice kept the single shop submission. An active fare review in a different chat left the original single-card workflow available. The composer checks the current chat and task before inferring a shop or sandbox flight card. The server independently checks the same login, chat, task, active review and expiry.

All 21 focused checkout and consent tests passed, together with frontend TypeScript and targeted Python lint. [Reproducible cases](../../../desk-companion/tests/test_live_flight_shop_consent.py)
