# Retained Work capacity

Updated 2026-10-13. This slice adds advisory visibility to retained Work reservations. It does not add deletion, reclamation, quota increases or guaranteed admission. Software checks and actual browser/target-device acceptance are separate; see [interface QA](../../output/qa/2026-10-13-work-capacity-interface/verification.md).

## Read contract

`GET /api/work/capacity` is a separate visible-owner read, independent of Work scope and its fingerprint. The global-only response includes `basis: retained_reservations`, `advisory: true`, a UTC `observed_at`, source and artifact count/byte dimensions, retained-run and saved-watch count dimensions, and server-derived per-file/per-run limits. There is no run-specific usage query in this version.

Each dimension has `limit`, `used`, `remaining` and `state` (`known`, `over_limit`, `unavailable`). Unknown exact usage and remaining capacity are null, never estimated zeros. A complete over-limit byte sum may have exact usage and zero remaining; an incomplete count overflow has null usage/remaining. The frontend rejects invalid integer, state or remainder combinations and shows unavailable instead of guessing.

The measure counts retained reservations, including reserved/unknown files, earlier outputs, terminal Work and retained/trashed watch records. A separately confirmed, validated completed watch purge shell is excluded from the twenty body slots; its opaque lifetime identity/receipt usage is reported separately by watch maintenance. Malformed purported shells never become free capacity. It is neither file integrity nor physical disk usage. Cancellation, archive, download and panel closure do not release capacity. Current run output membership is not lifetime per-run accounting, so the UI displays per-run limits explicitly as limits only.

## Interface and lifecycle

The private Work workspace shows one compact English/Chinese section with source/work/output/watch counts, source/output reserved bytes and observation time. Its own Refresh capacity action only refreshes this optional observation. Work refresh and useful successful run/source mutations also request a new observation. Opening the workspace performs one read; there is no new polling loop or persistent browser cache.

The source uploader shows dynamic server limits and warns if a selected file exceeds the observed remaining bytes or per-file limit. The composer displays dynamic per-file/per-run output limits and warns when a deterministic report/evidence pair has fewer than two observed output slots. Neither warning disables submission, changes consent, clears a draft or replaces an unknown operation's original retry data. Server admission remains authoritative; free slots never guarantee future byte or per-run capacity.

Capacity fetching is independent of run scope/read freshness and mutations. An ordinary unavailable/transport capacity failure cannot disable existing inspect, download, pause/cancel, resume or same-operation recovery. Actual authentication, owner, privacy or context denial immediately invalidates the shared private-view fence, including a reordered denial within the same epoch. Those actions retain their original authorization, freshness and byte checks. The capacity hook is mounted only in visible owner Work, never hidden metadata mode. Parent identity/privacy/offline/stale transitions unmount or mask the read; local session, privacy and offline listeners invalidate immediately. Request sequence and response epochs reject out-of-order and close/reopen replies. Old callbacks cannot fetch after invalidation/unmount.

Watch uses its existing complete list and returned definition limit to show remaining slots, including in hidden mode. It does not call the visible-only capacity endpoint. Cancelled, expired and budget-exhausted definitions explicitly remain saved and occupy slots until separately confirmed permanent removal; moving to Trash still occupies a slot. The watch workspace uses explicit retained_count rather than visible list length. Missing limits are labeled unknown; no local quota fallback is introduced.

## Boundaries

No provider, credential, external application or live model call is required. The global read carries no filenames, goals, IDs, operation keys or content. The existing exact-task Watch handoff, voice-origin/expiry/recovery restrictions, search, A1 whole-image layer and independent DeviceApp are unchanged. Real browser 390px/desktop/DeviceApp and target-hardware acceptance remain separate from executed hook/callback and React SSR tests.

## Backend accounting and authority

The response keys are exactly `basis`, `observed_at`, `advisory`, `sources`, `artifacts`, `runs` and `watches`. Source and artifact objects contain `count`, `bytes` and `file_bytes`; artifacts additionally contain `per_run_count` and `per_run_bytes`. Run and watch objects contain only `count`. There is no `run_artifacts` value or implicit current-run usage.

The dependency-free `work_limits.py` supplies the existing admission and display quotas: sources 100 / 67,108,864 recorded bytes / 1,048,576 bytes per file; artifacts 400 / 67,108,864 recorded bytes / 262,144 bytes per file; artifacts per nonempty run association four / 1,048,576 bytes; retained runs 100; saved watch definitions 20. The extraction does not alter command ordering, request fingerprints, errors, scope fingerprints or reconciliation. Existing-key lookup still precedes new-capacity admission, so full capacity does not block recovery of an existing reservation.

Construction stores only the existing Store reference. Observation uses one explicit SQLite read transaction with `PRAGMA query_only=ON`, reading at most each resource cap plus one rows. Runs and watches project only a constant scalar, never their body/status. File accounting uses the authoritative SQL kind and a projected integer byte count, regardless of reservation status, run membership or supersession. Unknown SQL kinds are outside both file admission buckets.

Before any JSON parsing, a nested SQL CASE checks metadata type, UTF-8 byte length at most 64 KiB, and absence of literal NUL. It then requires valid object JSON, one unambiguous byte_count key and JSON integer type. Bools, floats, strings, nested values, zero/negative/oversized file bytes and missing/duplicate fields make that bucket's byte dimension unavailable while its row still consumes a count. SQLite accepts some literal-NUL suffixes that Python admission rejects; the explicit guard avoids reporting those malformed rows as valid. This bounds materialized rows and scalar output, not SQLite physical disk work or general metadata integrity.

Both the observation and a fresh final read transaction require an actual unexpired owner session. Bounded privacy-setting projection and the settings version plus personal-settings epoch prevent hidden reads and invalidate in-flight logout, expiry, hide/show and consent changes. Paired/controller/display/device-agent identities cannot substitute for the owner's session. Metadata failures do not invoke listing, detail, file reads, reconciliation, network, model calls or cleanup. Missing/unsupported database schema returns `WORK_CAPACITY_UNAVAILABLE` (409), never fabricated empty usage; changed privacy authority returns `WORK_CAPACITY_PRIVACY_CHANGED` (403), alongside existing owner/hidden denials. Existing middleware provides origin checking and no-store responses; GET does not introduce a mutation header or operation ID.

The endpoint is advisory even when exact. A later writer may consume a reported slot; final new-operation admission remains in the original write transaction. A count over the bounded cap has `over_limit` with null exact usage and remaining, and the corresponding file-byte dimension becomes unavailable. A complete valid byte sum above its limit has exact over-limit usage and zero remaining. No reservation is released, and no all-or-nothing guarantee is added for the existing sequential report/evidence publication pair.

## Watch lifecycle integration

The exact capacity response keys remain unchanged. Watch accounting shares the same indexed charged predicate and bounded scalar integrity checks as creation, excluding only positively verified completed shells. Unknown/over-limit lifecycle metadata makes usage unavailable/over-limit and prevents false headroom. Separate [watch maintenance](watch-retention.md) exposes its finite lifetime metadata limit; this capacity read itself never removes anything. Source/artifact/run reservations are unchanged.
