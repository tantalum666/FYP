# Terminal watch retention design: independent review

2026-10-13. Scope: proposal review against current cloud checkout; no application edits, runtime-user data, provider requests, deletion, migration or publication. Temporary databases contain synthetic data only. Inherits the parent task's 186-document intake, not a new independent full-repository reading claim.

## Verdict

The watch-only slice is suitably small and its receipt bound is achievable. Revise the downgrade guarantee and specify the compatibility, confirmation, and accounting contracts below before implementation. Broader file/Work maintenance should remain explicitly deferred.

### 1. Blocking: new guards cannot protect against already-shipped old binaries

`backend/desk/store.py:27-56` unconditionally bootstraps and writes `PRAGMA user_version=1`; it does not read a forward schema version first. The actual old Store successfully reopened a synthetic version-2 database, preserved an additional marker table, reset the version to 1, and continued. A guard added to a new binary cannot change this behavior retroactively. An additive lifecycle column also does not make existing readers, triggers or capacity scans lifecycle-aware. Old positional INSERTs failing would not establish that all reads/writes are safely blocked.

Replace the design sentence with an operational compatibility contract: stop the single API process and all workers; make and verify a coherent pre-migration SQLite backup; migrate only with the supported new binary; prohibit older binaries from opening the migrated database. An intentional rollback uses an isolated pre-migration backup and acknowledges loss of post-backup changes; do not restore purged data automatically. Add an early forward-schema check to new supported binaries before any DDL, settings write, or schema version write. This prevents future unsupported downgrade attempts, not historical ones. If automatic enforcement against old binaries is required, it needs a separate proven storage-format/launcher isolation design and cannot be claimed by this additive migration.

`Store.connection(write=True)` does not make an `executescript()` caller atomic: sqlite3 commits its existing transaction before the script. An actual injected exception after a script left its created table and inserted row committed. Implement migration using individual `execute` statements inside one explicit `BEGIN IMMEDIATE` transaction (or a deliberately self-contained transaction script with robust error rollback), not the existing bootstrap pattern. Version and transformed rows commit together; run schema checks before service bootstrap. Recreate changed triggers explicitly: current `CREATE TRIGGER IF NOT EXISTS` keeps old trigger bodies.

### 2. Blocking contract gap: visible watch list is currently also the capacity count

`ResponsibilitiesPanel.tsx:300-311` displays saved usage and remaining capacity from `list.responsibilities.length`. Excluding Trash from ordinary listing while charging it will lie unless the interface changes. Keep capacity v1's exact response shape, change only watch admission/count predicates together, and return separately typed validated retained-watch usage for the watch workspace. Hidden stop view must still receive a safe aggregate count or explicitly say unknown; it cannot call the visible-owner capacity endpoint. Trash view includes at most the existing twenty retained rows; tombstone lookups need only exact IDs/keys, not a new unbounded browser or pagination framework. Current general Work search does not include watches, so do not expand that service just to satisfy generic proposal wording.

### 3. Receipt arithmetic: valid with explicit total-count semantics

Current `_operation_capacity` counts all receipts, including creation and any early pause/cancel, before allowing ordinary operations only when total <256. It does not count a separate category of ordinary kinds. Preserve that rule:

- Creation consumes receipt 1 and one of 256 lifetime identity slots
- New ordinary actions use the existing total-count threshold; old-key replays allocate zero
- Trash requires a terminal retained row and total receipt count <=254; its receipt raises total to at most255
- While trashed only Restore or final purge may create a receipt; Restore then reaches at most256 and preserves terminal status
- Existing state-machine-valid final pause/cancel at the limit reach at most258; no-op repetitions do not allocate
- One transition to purged adds at most one final receipt, reaching at most259
- A different key cannot allocate another purge receipt against an already-purged row; likewise no-op restore/trash must reject without writes

An exhaustive abstract transition enumeration covered 1,282 state/count pairs and reached exactly259, with every admitted Trash restorable. 256×259=66,304. This is a design-model check, not an implemented lifecycle test. No extra reserve table is needed: state predicates, receipt count, and atomic write serialization suffice. Describe the reserve as logical receipt admission, not preallocated disk space or a guarantee against disk-full errors. Corrupt excess legacy identities/receipts are preserved and flagged; do not claim the global bound covers preexisting invalid data.

### 4. Fresh exact owner confirmation and authority

The existing watch `_authority` verifies an actual owner session and hide state; `_reply` compares settings.version. It does not pin the personal-settings epoch used by the newer capacity contract. New maintenance preview must bind exact watch ID, requested action, evaluation/lifecycle versions, review/baseline inventory and current owner session plus settings/personal authority epochs. Recheck the same authority/inventory under the final SQLite write lock; recheck current response authority after commit. Define “fresh” explicitly: at minimum current matching versions/authority, and use an expiring server-issued preview if a time freshness promise is offered. A plain unkeyed fingerprint is comparison metadata, not evidence of human consent.

Use a separate mounted confirmation screen and an explicit strict purge-only confirmation field, with exact title/ID, history counts, one logical slot release, retained opaque metadata, and independently retained tasks/Work. Only its final owner click sends purge. No provider/tool path or generic success callback may synthesize this step. Cancel does not call a mutation endpoint. Exact same-key/body recovery checks the durable receipt before stale preview/expiry validation, under renewed current owner authority; otherwise a committed-but-lost reply becomes unrecoverable. New keys always require the current fresh confirmation. Hide/show, session replacement, offline/stale and reordered denials clear/disable this screen and its stale callbacks.

No extra global lock or scheduler is needed for DB-only mutations: `BEGIN IMMEDIATE` serializes authority/settings/session writes and lifecycle mutation on the single SQLite host. Do not claim frontend event fences alone serialize backend authority.

### 5. Replay result must be concrete and consumed

The proposal correctly requires original-key lookup before scope, current capacity or source/review lookups. Existing receipts store request hashes and IDs, not titles or response content, so do not introduce a generic response cache. Specify a discriminated lifecycle disposition carrying only stable opaque responsibility ID, current retention state/version, original operation kind, optional opaque review ID, operation ID, revision and recorded-success status. Do not fabricate `Responsibility`, set `acknowledged:true` as a new event, or embed removed labels. Retained results preserve the current shape. Matching replay returns current disposition; changed body/target remains OPERATION_ID_CONFLICT; absent key to purged target fails closed.

`usePrivateMutation` accepts unknown response bodies and the current watch success callback just reloads. The new maintenance callback must validate/branch on the lifecycle result, clear a selected detail after trash/purge, and refresh current retained usage. Otherwise detail rejection in `useResponsibilities`' Promise.all can clear the entire view after successful removal. Fetch an explicit maintenance detail for Trash rather than force the existing WatchDetail type to accept missing private fields.

### 6. Implementation checklist without widening the slice

Use three retention states only for watches: retained/trashed/purged. `purge_pending` is a later filesystem need, not necessary for one SQLite transaction. Add indexed retained predicates, explicit column INSERTs, tightly validated body/tombstone decoding, and positive retention gates to existing worker, expiry, trigger, ordinary action, acknowledgment, detail and replay paths. Preserve terminal state, spent budgets, watermark and all ID/key/hash barriers. Deleted sources/reviews and the shell update plus purge receipt must commit as one unit. Task/Work data remain untouched. Validate migration rows rather than defaulting corrupt metadata into free space.

## Evidence and limits

- `probe.py` ran against actual Store in the existing virtualenv, creating only temporary synthetic SQLite stores
- `probe-results.json`: legacy bootstrap resets version2 to1; executescript changes survive context rollback; abstract receipt maximum259, lifetime maximum66,304
- Inspected actual responsibilities service, Store, capacity query/model, watch list/detail/types/controls, private mutation helper, existing tests, product/handoff and relevant contracts
- No implementation tests, UI mount, provider, target device, real data deletion, migration deployment or capacity recovery claimed

Parent owns proposal/handoff/decision updates. This reviewer changed only its own QA directory.
