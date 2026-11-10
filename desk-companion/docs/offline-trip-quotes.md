# Offline trip quotes

10 November 2026. This is the offline slice of the third journey in the [research index](../../research/personal-agent-research-index.md): a fare can be reviewed, held, failed, or matched to a fixture receipt, and a later change stays on the same task. Mailbox, shopping, and the offline calendar already do that for their own sources. The 7 November browser flight comparison did not record those states.

It does not call a model, an airline, a payment service, or a calendar account. A fixture receipt is not a live ticket. `purchase` is always `not_performed`.

## What a fixture is

Files live in [fixtures/travel](../fixtures/travel/README.md). The file name is `<fixture_id>.json`. `fixture_id` and `itinerary_id` are lowercase, so names stay unique on a case-insensitive disk. `DESK_TRAVEL_FIXTURES` selects another directory for tests. The loader refuses a path that leaves that directory.

The first event is a `quote` with both airports, both local times, both IANA timezones, passengers, baggage, total, and fare rules. Later events are `reprice`, `schedule_change`, `payment_failed`, or `ticketed`. A field that is absent stays as stored. An explicit null is rejected and does not clear the task. Arrival must be after departure once both clocks are known.

## What the owner can do

`POST /api/trips/connections` reads one fixture and stores a cursor at zero. The same fixture does not open a second task. `POST /api/trips/connections/{id}/sync` commits the next contiguous `seq`.

- The same event id and body is skipped. A different body returns `TRIP_EVENT_CONFLICT` and does not move the cursor.
- A higher `seq` waits until the missing one arrives. Restart keeps that buffer.
- `disconnect_after` 0 does not open the file. `completed` is false. That is not a finished sync.
- `disconnect_after` N commits at most N new events, then stops. The cursor moves only for an event that has been committed.
- Revoke stops the next read. `completed` is false. A later sync does not apply the rest.

One itinerary gets one task from the existing task table. Later events reuse it. Task `next_step` and `waiting_for` change only when that event includes them. The route title follows the airports.

## Hold, failure, and receipt

`POST /api/trips/connections/{id}/holds` is the only way to mark the current quote held. The body must carry the `quote_id` and `expected_task_version` the owner just saw. Omitted task fields stay stored.

- The same operation id and body returns the original result. A different body returns `OPERATION_ID_CONFLICT`.
- A wrong quote or a stale task version stores no success, so the same operation id can be reused.
- A later reprice or schedule change leaves the task in place and makes the earlier approval stale.
- `payment_failed` is not a ticket. A ticket event applies only when the owner holds that exact quote and the event cites it. Anything else is recorded as blocked and is not retried into a success.
- A second receipt does not replace the first. A schedule change after a receipt keeps the receipt and marks it as not covering the new times.

Quiet hours keep the same notice id. The rules tick delivers it once after quiet hours end. The notice says that no card was charged.

## Who can call it

Every route requires the owner session and visible private context. A signed-out client and a paired display receive 403. Hiding private details returns 403 before a hold is written. A later owner sign-in can keep reading the same fixture; the cursor stays in SQLite.

Portable JSON backup is unchanged. `mailbox_bundle`, `shopping_bundle`, and `offline_calendar_bundle` are not part of this slice. A whole-file SQLite copy still contains the trip rows.

## Checks

From `desk-companion/`:

```sh
uv run --no-sync ruff check backend/desk/travel_quotes tests/test_travel_quotes.py
uv run --no-sync pytest tests/test_travel_quotes.py -q
```

No paid provider call and no GitHub Actions run.

## Handoff

The trip service is `TravelQuoteService` on `Runtime.trips`, registered beside shopping. It does not create a Work run, a proposal, or a browser job. The panel is `TripQuotes` under Work & tools. Approval sends only `quote_id` and `expected_task_version`.

The next gap is still a real itinerary source and a real ticket receipt. This fixture does not close that. Portable backup of the trip cursor is the local follow-up if a restore must keep the same task without a SQLite file copy.
