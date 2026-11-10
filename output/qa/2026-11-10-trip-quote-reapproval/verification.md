# Trip quote change, release, and re-approval

10 November 2026. Grok Bot. Offline only. No paid model call, live airline, merchant, payment account, or Pi/VPS change.

## Reading

Full: `AGENTS.md`, `desk-companion/docs/offline-trip-quotes.md`, `desk-companion/backend/desk/travel_quotes/` (service, routes, fixtures, notices), `desk-companion/tests/test_travel_quotes.py`, `desk-companion/frontend/src/workspace/TripQuotes.tsx`, `desk-companion/frontend/src/workspace/tripQuoteState.ts`, `desk-companion/frontend/tests/trip-quotes.test.ts`, `desk-companion/fixtures/travel/hkg-tyo.json`.

Partial: `handoff.md` opening and next step; `research/personal-agent-research-index.md` section 4 and the third journey (travel booking states); `desk-companion/docs/shopping-fixtures.md` through the ingest contract; `desk-companion/docs/ui-copy.md` default-view section. Searched `product.md` and `decision-log.md` for trip-quote decisions; neither names this slice. `output/qa/2026-11-10-offline-trip-quotes/verification.md` records the prior quote/hold/receipt slice.

## Choice

`TravelQuoteService` already keeps one task and marks a hold stale after `reprice` or `schedule_change`. This slice stays on that service. A fixture file can be replaced with a later `seq`. The snapshot stores `change.fields` as before/after. `quote_version` increases when the fare identity changes or the fare ends. Hold and release require that version. `unavailable` ends the same quote and does not accept a replacement itinerary. Later events after that ending are blocked.

## What was checked

- `uv run --no-sync ruff check backend/desk/travel_quotes tests/test_travel_quotes.py` passed.
- `tests/test_travel_quotes.py`: 13 passed. Adds price change, time change, unavailable without a substitute, stale-version rejection with no stored success, re-approval, release, omitted task fields, owner/paired/other-login denial, idempotent retry, and interruption before commit and after commit.
- Full backend `PYTHONPATH=. uv run --no-sync pytest -q`: **2047 passed, 2 failed**. Failures are the known `test_public_unicast[::ffff:93.184.216.34]` and `test_restart_runs_only_the_approved_folder_job`. Two OpenAI tests failed only while `DESK_TEXT_PROVIDER=none` was set and passed when that variable was unset. After the full run, the unavailable test gained assertions that a stale or ended release stores no success; that test was re-run and passed. The full suite was not repeated.
- Frontend `npm test`: **334 passed, 0 failed**. `tsc --noEmit` passed.
- Chrome on Tasks → Work & tools → Trip quote, fixture `hkg-tyo`: read showed HKD 2080.00 and “Not held and not ticketed.” Approve changed it to “Held. Not paid and not ticketed.” and showed Release hold. A reprice file then showed “The fare changed. The earlier approval does not cover it.” and “Fare: HKD 2080.00 → HKD 2260.00”, with Approve back and Release gone. Approving again restored the hold. Release returned “Not held and not ticketed.” An unavailable event then showed “This fare is no longer available. No other fare was offered.” and “The flight was withdrawn.” The route stayed HKG to TYO. Approve and Release were both absent.

`mailbox_bundle`, `shopping_bundle`, and `offline_calendar_bundle` were not edited. `handoff.md`, `work-log.md`, `AGENTS.md`, and `START_HERE_NEXT_CHAT.md` were left unchanged. The slice handoff is `desk-companion/docs/offline-trip-quotes.md`.

## Not done

No real itinerary source, ticket receipt, or portable JSON backup of the trip cursor. No card was charged.
