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
- `disconnect_after` stops after that many newly committed events. `0` commits nothing. `completed` stays false. Operation receipts already stored are not deleted.
- Revocation is checked before the file is read and again before each event. A revoked connection returns `SHOPPING_REVOKED` and does not parse the fixture.

One subject (one product or one order) gets one task from `TaskService.create` and one deterministic Work run. The run is paused immediately so the worker does not compose a purchase. Later events reuse that task and that run.

## Advice, approval and notices

Meaningful changes create a `shopping_advice` draft. The note cites the fixture id and the observation time and says that no purchase or checkout was performed. Confirm and cancel use `POST /api/assistant/proposals/{id}/decisions`.

- Only an owner session can confirm or cancel. A paired device receives 403 and cannot list the draft.
- Confirmation reads the live task and changes only `provided_fields`. Omitted fields, including `next_step`, stay as they are.
- `shopping_advice` is outside full software permission, so standing permission does not auto-apply it.
- Cancelling a draft does not write the sourced note.
- Notices use `Notifier` for a price drop at or past the threshold, a new shipment, a new delay, or a change that needs a decision. An unchanged cart, a smaller price drop, and a second sync do not add another notice.

There is no checkout route. Portable JSON backup was not extended; shopping cursor rows live in the desk SQLite file, and tasks created here are ordinary tasks.

## Checks

From `desk-companion/`:

```sh
uv run --no-sync ruff check backend/desk/shopping tests/test_shopping_fixtures.py
uv run --no-sync pytest tests/test_shopping_fixtures.py tests/test_permissions.py -q
```

No paid provider call and no GitHub Actions run.
