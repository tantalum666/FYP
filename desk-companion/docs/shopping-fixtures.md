# Offline shopping fixtures

3 November 2026. Local cart, price, stock and shipment fixtures feed the existing task, Work and notice path. There is no store account, payment call or checkout.

## What a fixture is

A fixture is one UTF-8 JSON file in a directory. The file name is `<fixture_id>.json`. `fixture_id` is lowercase letters, digits and hyphens, so two names cannot collide on a case-insensitive disk. The default directory is `desk-companion/fixtures/shopping`. `DESK_SHOPPING_FIXTURES` selects another directory for tests. The loader refuses paths that leave that directory.

Each event has `event_id`, `seq`, timezone-aware `observed_at`, and one kind: `cart_change`, `price_drop`, `out_of_stock`, `order_shipped`, or `order_delayed`. A product event needs a `sku`. An order event needs an `order_id`. `continues_subject` (`product:` or `order:` plus a lowercase token) keeps a later shipment on the product already being tracked. Fields that are absent are not treated as cleared.

`price_drop_threshold_bps` defaults to 500 (5 percent). A drop is measured from the last observed unit price. The first price is a baseline and does not notify.

## What ingest does

`POST /api/shopping/connections` reads one fixture and stores a cursor at zero. `POST /api/shopping/connections/{id}/sync` reads the file again and commits the next contiguous `seq`.

- The same `event_id` and body is skipped.
- A repeated `event_id` with a different body returns `SHOPPING_EVENT_CONFLICT` and does not move the cursor.
- A higher `seq` waits in `shopping_buffer` until the missing sequence arrives. Restart reads that buffer and the file.
- Revocation is checked before the file is read and again before each event. A revoked connection returns `SHOPPING_REVOKED` and does not parse the fixture.

`disconnect_after` is an optional integer on the sync body, from 0 to 100.

- Omitted: commit each contiguous event that is not already applied, until a gap, a revoke, or the end of the fixture.
- `0`: do not open the fixture file and do not commit. The cursor stays put. The response is `completed: false` and `stopped: "disconnected"`. This is not a successful sync.
- `N`: commit at most N events that this call newly applies. Events already stored do not count. The call then returns `completed: false` and `stopped: "disconnected"`. The cursor moves only for an event whose task, draft, notice, and receipt have been committed. Stored operation receipts are not deleted. A disconnect is not a completed sync.

One subject (one product or one order) gets one task from `TaskService.create` and one deterministic Work run. The run is admitted in paused state atomically so the worker cannot dispatch between create and pause. Later events reuse that task and that run.

## Advice, approval and notices

Meaningful changes create a `shopping_advice` draft. The note cites the fixture id and the observation time and says that no purchase or checkout was performed. Confirm and cancel use `POST /api/assistant/proposals/{id}/decisions`.

- Only an owner session can confirm or cancel. A paired device receives 403 and cannot list the draft.
- Confirmation reads the live task and changes only `provided_fields`. Omitted fields, including `next_step`, stay as they are.
- `shopping_advice` is outside full software permission, so standing permission does not auto-apply it.
- Cancelling a draft does not write the sourced note.
- Notices use `Notifier` for a price drop at or past the threshold, a new shipment, a new delay, or a change that needs a decision. An unchanged cart, a smaller price drop, and a second sync do not add another notice.

There is no checkout route. The owner portable JSON backup includes the shopping connection, cursor, subject-to-task mapping, applied receipts, and out-of-order buffer. Preview checks that bundle before anything is written. Apply is owner-only and keeps a connection that is already present, so a second restore does not rewind the cursor. The backup does not include the owner session or its hash, pending drafts, delivered notices, or the old execution run row. Deferred notices are included. On explicit sync, an absent run is replaced by one paused run bound to the existing task; later syncs reuse it. The prior run ID is only a historical pointer until this recovery. A whole-file SQLite copy still holds the Work run.

## Checks

From `desk-companion/`:

```sh
uv run --no-sync ruff check backend/desk/shopping backend/desk/exchange.py tests/test_shopping_fixtures.py
uv run --no-sync pytest tests/test_shopping_fixtures.py tests/test_exchange.py tests/test_backup_persona_jobs.py -q
```

No paid provider call and no GitHub Actions run.

## 4 November review corrections

Notice IDs include connection and event identity. Undelivered notices survive quiet hours, restart and portable restore and are released by the existing rules tick. The optional `notice_holds` field accepts earlier bundles without it. Login is rechecked between events. Shared cards show a task update/price or shipment source and never label confirmation as a purchase, payment or calendar write. See [combined QA](../../output/qa/2026-11-04-grok-journey-review/verification.md).
