# Offline trip quotes

10 November 2026. This is the offline slice of the third journey in the [research index](../../research/personal-agent-research-index.md): a fare can be reviewed, held, released, failed, or matched to a fixture receipt. A later price, time, or unavailable report stays on the same task and retires the earlier approval. Mailbox, shopping, and the offline calendar already do that for their own sources. The 7 November browser flight comparison did not record those states.

It does not call a model, an airline, a payment service, or a calendar account. A fixture receipt is not a live ticket. `purchase` is always `not_performed`.

## What a fixture is

Files live in [fixtures/travel](../fixtures/travel/README.md). The file name is `<fixture_id>.json`. `fixture_id` and `itinerary_id` are lowercase, so names stay unique on a case-insensitive disk. `DESK_TRAVEL_FIXTURES` selects another directory for tests. The loader refuses a path that leaves that directory.

The first event is a `quote` with both airports, both local times, both IANA timezones, passengers, baggage, total, and fare rules. Later events are `reprice`, `schedule_change`, `unavailable`, `payment_failed`, or `ticketed`. A field that is absent stays as stored. An explicit null is rejected and does not clear the task. Arrival must be after departure once both clocks are known.

Replacing the file with a later `seq` is how the offline source reports a change. `unavailable` carries a reason and no replacement airports, times, or price. A replacement on that event is rejected and does not move the cursor. After the fare has ended, a later price or itinerary event is recorded as blocked and is not turned into another fare.

## What the owner can do

`POST /api/trips/connections` reads one fixture and stores a cursor at zero. The same fixture does not open a second task. `POST /api/trips/connections/{id}/sync` commits the next contiguous `seq`.

- The same event id and body is skipped. A different body returns `TRIP_EVENT_CONFLICT` and does not move the cursor.
- A higher `seq` waits until the missing one arrives. Restart keeps that buffer.
- `disconnect_after` 0 does not open the file. `completed` is false. That is not a finished sync.
- `disconnect_after` N commits at most N new events, then stops. The cursor moves only for an event that has been committed.
- Revoke stops the next read. `completed` is false. A later sync does not apply the rest.

One itinerary gets one task from the existing task table. Later events reuse it. Task `next_step` and `waiting_for` change only when that event includes them. The route title follows the airports.

## Hold, change, release, and receipt

`POST /api/trips/connections/{id}/holds` is the only way to mark the current quote held. `POST /api/trips/connections/{id}/releases` is the only way to drop that hold. Each body carries the `quote_id`, `quote_version`, and `expected_task_version` the owner just saw. Omitted task fields stay stored. A quote is not a hold. A hold is not paid. Nothing is ticketed and no card is charged.

The quote version starts at 1 and increases when the price or either local time changes, and when the fare becomes unavailable. Approving or releasing any other version returns `TRIP_QUOTE_CHANGED` and stores no success, so that operation id can be reused for the version now on screen.

- The same operation id and body returns the original result. A different body returns `OPERATION_ID_CONFLICT`.
- A response that never commits stores nothing. The same operation id can be sent again.
- A commit whose response is lost is not treated as a new success. Sending that same operation id returns the stored result once, with `recovered: true`, and does not write a second note.
- A later reprice or schedule change stays on the same task. The snapshot `change.fields` lists each changed value as `before` and `after`. `held_covers` becomes false and `approval_stale` becomes true. The new quote is held only after the owner approves that new version.
- `unavailable` ends the fare on that same task. The quote id does not change and no substitute is stored. The owner cannot approve it. A release applies only while that exact version is still held.
- Releasing a current hold returns the fare to `quoted` and clears the hold. Releasing a version that is not held stores no success.
- `payment_failed` is not a ticket. A ticket event applies only when the owner holds that exact quote and the event cites it. Anything else is recorded as blocked and is not retried into a success.
- A second receipt does not replace the first. A schedule change after a receipt keeps the receipt and marks it as not covering the new times.

Quiet hours keep the same notice id. The rules tick delivers it once after quiet hours end. The notice says that no card was charged.

## Who can call it

Every route requires the owner session and visible private context. A signed-out client, a different login, and a paired display receive 403. Hold and release read that session again inside the write transaction. Hiding private details returns 403 before a hold or release is written. A later owner sign-in can keep reading the same fixture; the cursor stays in SQLite.

Portable JSON backup is unchanged. `mailbox_bundle`, `shopping_bundle`, and `offline_calendar_bundle` are not part of this slice. A whole-file SQLite copy still contains the trip rows.

## Checks

From `desk-companion/`:

```sh
uv run --no-sync ruff check backend/desk/travel_quotes tests/test_travel_quotes.py
uv run --no-sync pytest tests/test_travel_quotes.py -q
cd frontend && npm test
```

No paid provider call and no GitHub Actions run.

## Handoff

The trip service is `TravelQuoteService` on `Runtime.trips`, registered beside shopping. It does not create a Work run, a proposal, or a browser job. The panel is `TripQuotes` under Work & tools. Approve and release send `quote_id`, `quote_version`, and `expected_task_version`. The panel shows the old and new fare or times, and says when a fare has ended with no substitute.

The next gap is still a real itinerary source and a real ticket receipt. This fixture does not close that. Portable backup of the trip cursor is the local follow-up if a restore must keep the same task without a SQLite file copy.
