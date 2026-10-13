# Recoverable terminal-watch maintenance

Updated 13 October 2026. This watch-only implementation adds owner-reviewed Trash,
Restore history and explicitly confirmed permanent removal to
[selected task-change responsibilities](responsibilities.md). It does not add
file/Work removal, automatic emptying, a new scheduler, quota increases or a
provider-callable removal tool. Software verification and actual mounted UI
acceptance are separate; see the [backend evidence](../../output/qa/2026-10-13-terminal-watch-retention-backend/verification.md).

## Meaning and eligibility

Only `cancelled`, `expired` and `budget_exhausted` watches are eligible. An active,
paused or blocked watch must first be cancelled through its existing explicit
control. Maintenance never cancels a watch implicitly.

Evaluation status and retention are separate:

- `retained`: appears in the ordinary watch workspace
- `trashed`: omitted from ordinary listing/detail; visible in the dedicated
  owner-only Trash workspace and still charged against the twenty-watch limit
- `purged`: content-free tombstone, excluded from body-slot accounting only when
  its completed shell, retained purge receipt and absence of child bodies validate

Trash and Restore change only retention state/version/timestamps. They preserve
the same identity, terminal status, evaluation version/generation, original
expiry, review limits, spent budgets, history and nondecreasing day watermark.
Restore does not resume evaluation or recreate an alert. Workers, expiry,
ordinary actions, acknowledgments and task/note triggers have positive retained
state gates; a nonretained watch cannot become active through those paths.

Permanent removal can follow Trash or operate directly on an eligible retained
terminal watch after the same separate final confirmation. It deletes only that
watch's saved source-baseline rows and retained review rows, replaces its private
definition JSON with `{"kind":"purged_watch_v1"}`, and retains its stable ID,
terminal/budget/lifecycle metadata and every original hash-only operation receipt.
The entire change, new receipt and workspace revision are one SQLite transaction.
No watched task, task evidence, calendar event, independently started Work,
voice-origin claim, source or artifact is removed.

This releases exactly one logical saved-watch reservation. It does not claim
that the SQLite file shrinks, disk bytes are securely erased, a backup is updated,
or any downloaded/provider copy or past external effect is undone.

## Bounds and honest usage

The working-set limit remains twenty charged watch bodies. Trash is charged.
A separate 256-lifetime-identity limit includes retained, trashed and purged IDs.
Identity metadata is reserved at creation, so a final purge does not need a new
identity slot. The old twenty-watch limit is not silently increased.

All receipt kinds count together, including creation, ordinary controls,
acknowledgments and maintenance. Original-key replays add none.

- Ordinary actions retain the existing total-count threshold of 256
- Trash requires at most 254 existing receipts; after Trash there are at most 255
- Restore requires at most 255 existing receipts; it can reach 256
- Existing valid final pause/cancel reserves can reach 258
- Purge requires at most 258 existing receipts and adds one final receipt, at most 259

Thus valid admitted state has at most 256 × 259 = 66,304 watch receipts. This is
logical admission capacity, not preallocated disk storage or a promise that
writes succeed on a full disk. Distinct-key no-op Trash/Restore/purge requests
are rejected without a receipt. Repeated Trash/Restore cycles eventually stop;
a Trash admitted through this protocol always retains its one Restore slot.
No receipt TTL, ID reuse, namespace rotation or automatic resurrection is used.

Legacy malformed/over-limit rows are preserved, flagged and do not advertise
available admission. New purge against an already excessive per-identity count
is also refused without writes. Existing-key recovery still works. Identity
metadata exhaustion does not prohibit valid terminal removal or existing stop
controls, but it does prohibit new creation even after a body slot is released.

The ordinary and hidden watch lists return a separately validated
`maintenance_usage` object:

```
{
  "version": 1,
  "retained_count": 19,
  "trashed_count": 1,
  "lifetime_count": 20,
  "lifetime_limit": 256,
  "lifetime_remaining": 236,
  "state": "known"
}
```

Here `retained_count` includes Trash. In known usage all counts are nonnegative
integers, `trashed_count <= retained_count <= lifetime_count`, body count is at
most twenty and lifetime count at most 256. At either exact limit the result is
still known. `unavailable` or `over_limit` returns null for all count/headroom
fields; the limit and version remain present. A short visible list never implies
free capacity. Hidden mode exposes only safe aggregate usage and its existing
metadata-only stop controls, not maintenance or private history. Hidden list,
pause and cancel do not load or decode private watch JSON, including corrupt
JSON; malformed content is not a reason to prevent a safe hidden stop.

The existing `/api/work/capacity` v1 response keeps its exact keys. Admission and
capacity share the indexed charged predicate and bounded scalar integrity
checks. NULL/unknown retention does not disappear from charging. Invalid purge
shells, residual source/review bodies or missing purge receipts make usage
unavailable. Bounded SQL projections prevent oversized lifecycle strings from
being copied into Python. More than twenty charged bodies is body-count
`over_limit`; metadata-only excess is `unavailable` in the capacity v1 count
rather than falsely claiming that the body limit was exceeded.

## Exact preview and final confirmation

The server holds at most 32 opaque watch-maintenance previews. Each expires
five minutes after issue under both server wall and monotonic clocks; clock
rollback also invalidates it. Eviction and process restart require a new preview.
Only IDs, versions, a canonical inventory digest, authority epochs and deadlines
are cached, never a title, review body or full response.

A preview binds one watch ID, one action, its evaluation and retention versions,
the complete bounded source/review inventory and current receipt count, plus the
actual owner session hash, `settings.version` and `personal_settings.epoch`.
Current labels are read from the database. The preview fingerprint is comparison
metadata, not evidence of human consent.

A new purge mutation additionally requires strict
`confirm_permanent_removal: true`, sent only by the final click on a separate
current permanent-removal confirmation. The field is forbidden on Trash/Restore,
including null/false. The screen identifies the exact watch, history counts,
one released logical slot, retained opaque receipts including the new purge
receipt, and independently retained tasks/Work. Cancel sends no mutation.

The write transaction first checks real current visible-owner authority and the
durable original operation receipt. A matching recorded request recovers the
current disposition before checking a lost/expired preview, versions, scope or
new admission. A changed body or target under that key conflicts. For a new key,
all preview bindings, exact versions, terminal eligibility and receipt admission
are checked again under `BEGIN IMMEDIATE`. A consumed confirmation cannot approve
a different record, action or operation. There is no global lock or new worker.
A fresh response authority check after commit rejects logout/hide/show/session or
personal-epoch changes; the write may already have committed, so recovery uses the
same original request/key instead of a new effect.

The client clears private queues and confirmation on identity/privacy changes,
fences delayed replies, and disables actions while offline/stale. Within the
same valid privacy epoch, an uncertain response retains the exact serialized
request and original operation key. Across an invalidated epoch the UI reopens
current history rather than inventing a replacement key.

## HTTP contract

All endpoints are under `/api/responsibilities` and require a real owner session.
Paired/device/forged-owner principals are rejected independently by the service.
Existing origin, `X-Desk-Request: 1`, no-store responses and mutation
`X-Operation-Id` protections apply. Preview has no operation key and makes no
SQLite/user-record changes.

- `GET /`: ordinary retained list with `maintenance_usage`; hidden mode remains
  metadata-only
- `GET /maintenance`: visible-owner Trash list, `maintenance_usage`, `revision`
  and `server_time`; the list is bounded to the retained-body working set
- `GET /{id}/maintenance`: complete ordinary detail shape for retained/trashed
  records (`responsibility`, `reviews`, `selected_tasks`, `revision`); purged
  records return stable HTTP 410 `RESPONSIBILITY_REMOVED`
- `POST /{id}/maintenance-preview`: `action: trash|restore|purge`, strict positive
  `expected_version` and `expected_retention_version`
- `POST /{id}/retention`: same three fields plus opaque `preview_id`; purge also
  requires the strict final-confirmation field above

A full retained/trashed watch adds `retention_state`, `retention_version`,
`trashed_at`, `restored_at` and `purged_at`. These timestamps may be null.

Preview response fields are:

```
kind: "watch_retention_preview"
preview_id, action, expires_at, revision
responsibility: {id, title, status, version, retention_state, retention_version}
counts: {definitions: 1, source_baselines, retained_reviews, operation_receipts}
retained_operation_receipts_after: current operation_receipts + 1
logical_slots_released: 0 for Trash/Restore, 1 for purge
receipts_retained: true
independent_tasks_retained: true
independent_work_retained: true
maintenance_usage: the validated usage object
```

The nested responsibility versions become the mutation's `expected_*` fields.
Session hashes and authority epochs are not exposed.

An operation against a currently retained resource keeps the existing success
shape: full `responsibility`, `saved`, `revision`, `operation_id`, and the existing
acknowledgment fields when applicable. A successful Trash/purge or replay of any
previous operation whose current resource is nonretained returns instead:

```
{
  "kind": "retention_disposition",
  "responsibility_id": "opaque original ID",
  "retention_state": "trashed or purged",
  "retention_version": 2,
  "original_operation_kind": "create|pause|resume|cancel|recheck|acknowledge|trash|restore|purge",
  "review_id": null,
  "operation_id": "original key",
  "revision": 10,
  "recorded_success": true
}
```

An acknowledgment replay can retain its opaque historical review ID even after
its body was pruned/purged. The disposition contains no old title or fabricated
full definition, and does not assert a newly achieved `acknowledged: true`.
This receipt-only shape is never fabricated for a plain GET.

New stable errors include `RESPONSIBILITY_NOT_TERMINAL`,
`RESPONSIBILITY_RETENTION_INVALID`, `RESPONSIBILITY_RETAINED_STATE_REQUIRED`,
`RESPONSIBILITY_REMOVED`, `RESPONSIBILITY_PREVIEW_EXPIRED`,
`RESPONSIBILITY_PREVIEW_CHANGED`, `RESPONSIBILITY_METADATA_LIMIT` and
`RESPONSIBILITY_METADATA_UNAVAILABLE`. Existing operation conflict, version,
receipt-limit, owner and privacy errors remain.

## Schema2 and operator compatibility

The supported Store checks existing schema version and core ownership/settings/
state structure before any journal-mode/bootstrap/settings/credential/version
write. An unsupported forward version is refused, never reset. Existing legacy
schema1 stores require an explicit `allow_watch_retention_migration=True`
constructor opt-in; the normal app default is false. The
[operator procedure](operator-guide.md) and one-time
[`migrate_watch_retention.py`](../scripts/migrate_watch_retention.py) command require
an explicit acknowledgment that all app/workers are stopped and a coherent
protected backup was separately verified. The flag proves neither condition.
There is no backup service or automatic migration of an existing user store.

Fresh Store initialization creates all four core watch tables and indexes in
schema2 without Runtime. Only task-dependent triggers/indexes wait for
TaskService. Current standalone Store can reopen normally; missing or partial
core watch schema is rejected. Legacy databases with no watch tables are valid
supported inputs only when the other Store schema is recognized and migration
is explicitly opted in.

The migration uses individual `execute` statements inside one explicit
`BEGIN IMMEDIATE`: column defaults keep every old watch retained/charged,
existing bodies/IDs/status/budgets/history/receipts are preserved, required indexes
are created, known task/note triggers are explicitly replaced, and schema version
commits with everything else. `executescript()` is not used for the migration.
A fault rolls back columns, rows, triggers and version together. Invalid stored
watch content is preserved rather than defaulted into free space.

This guard protects cooperating new binaries. Already-shipped old binaries can
still overwrite `user_version` and do not understand lifecycle columns; an
additive schema migration cannot retroactively protect against them. Operators
must prevent old binaries from opening a migrated store. Intentional rollback
uses an isolated verified pre-migration backup and acknowledges loss of
post-backup changes. Never silently restore purged history or replay an old
effect. Pre-migration backups still contain pre-purge content.

## Verification boundary

Backend tests use isolated synthetic SQLite stores. They cover full-capacity
release, concurrent original-key retry, review replay after purge, terminal
status/budget preservation, exact receipt ceilings, lifecycle/authority/preview
fences, malformed metadata, hidden stop availability, mutation rollback,
explicit migration and all-or-nothing schema rollback. Backup readback tests use
SQLite's supported backup API on fixtures. Independent child-process-exit and
runtime audits are linked from the backend QA record.

No actual user history was removed, no current runtime store migrated, and no
provider, credentials, account, installation, hardware, remote publication or
live UI acceptance was exercised by this backend work.
