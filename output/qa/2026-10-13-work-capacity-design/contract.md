# Retained Work capacity: minimum next slice

Status: design only, 2026-10-13. Task-watch source is frozen. No application or test files changed. This is a maintenance prerequisite before broadening public research capture; it does not lift quotas, provide deletion or reclaim retained history. No live model, credentials, browser, filesystem body reads or network is required by the proposed feature.

## Verified current behavior

- `backend/desk/sources.py`: each source at most 1,048,576 bytes; 100 total reservations; 67,108,864 total recorded bytes. `listing()` exposes limits but defaults to a 50-row page. Scope asks for 100 sources but discards the limits wrapper.
- `backend/desk/artifacts.py`: each artifact at most 262,144 bytes; 400 total reservations; 67,108,864 total recorded bytes. Every nonempty run association additionally permits at most four artifacts and 1,048,576 bytes. Superseded/earlier outputs remain retained.
- `backend/desk/file_store.py:ImmutableFiles.put`: checks existing `(kind, operation_key)` before new-capacity admission. Matching retry reconciles its existing reservation. New admission reads every same-kind metadata row, counts all rows and sums every `byte_count`, regardless of `reserved`, `unknown` or `verified`. The new reservation is committed before file publication. A crash, rejected late publication, missing file or unknown readback does not release it. Per-run artifact accounting uses stored `run_id`, not current output membership.
- `backend/desk/agent_runs.py`: new-run admission counts all rows, maximum 100; cancelled, failed and succeeded runs still count. Run listing is capped at 100. A run itself is not a reservation for its future artifacts.
- `backend/desk/responsibilities.py`: `LIMITS.definitions=20`; creation counts every definition including terminal. Existing UI shows complete list length / limit, but does not explicitly explain remaining slots or retained terminal capacity.
- `SourceUpload` currently states static source limits; `RunComposer` states retained-run and per-run output limits; `ArtifactList` shows individual output size/verification only. None reports global current source/artifact/run capacity.
- `WorkSearchService` already establishes the preferred pattern: narrow SQL projection, cap+1 detection, `PRAGMA query_only`, consistent read snapshot, and a second real-session/privacy check in a fresh transaction. Its constants currently duplicate storage limits.

## Proposed boundary

Add a separate `GET /api/work/capacity`, not a member of `AgentRunService.scope()` and not part of its scope fingerprint. Putting changing usage in scope would repeatedly invalidate review/retention on unrelated writes; using scope also loads unrelated task/context/browser catalogs. Capacity is advisory metadata, never authority or a reservation.

Default endpoint returns only global aggregates. An optional exact `run_id` adds per-run artifact accounting for an existing retained run. Validate the generated run-ID format, bind the lookup to current owner authority, and return RUN_NOT_FOUND for absent IDs. Do not accept arbitrary historical standalone publisher scope IDs here; global artifact totals still count those reservations.

The endpoint is visible-owner-only. Existing hidden Work and Watch metadata/status/Pause/Cancel paths are unchanged and do not depend on its success. A hidden owner gets PRIVATE_CONTEXT_HIDDEN for this endpoint; paired/controller/display/device-agent identities get owner denial even if they can call other workspace endpoints. Do not fetch capacity in hidden mode or broaden hidden file-size disclosure merely because names are omitted.

Register with existing owner/origin/header protections and no-store response handling. Service construction creates no table, file or worker. No operation ID, usage cache, background polling task or persistent snapshot is necessary.

## Compact response contract

Return a strict typed object with only:

- `basis: "retained_reservations"`
- `observed_at`: UTC server observation time
- `advisory: true`
- `sources`: count and byte dimensions, plus per-file limit
- `artifacts`: count and byte dimensions, plus per-file and per-run limits
- `runs`: count dimension
- `watches`: count dimension
- `run_artifacts`: null unless an exact run was requested; then that run ID and its count/byte dimensions

Each dimension is `{limit, used, remaining, state}`. `state` is `known`, `over_limit` or `unavailable`. Integers must be strict JSON-safe nonnegative integers, not bools/floats/strings. Known `remaining = max(0, limit-used)`. For unavailable dimensions `used` and `remaining` are null. An over-limit sentinel without a complete count must also use null for exact used/remaining, with an optional bounded `at_least` field; never report cap+1 as the exact total. For a complete bounded row set whose valid byte sum exceeds the limit, exact used and zero remaining can be returned with over_limit.

Include no filename, goal, task ID, title, raw JSON, session hash, operation key, request hash, provider configuration, host path, file content or evidence. In particular omit arbitrary database error strings. State is an accounting status, never physical file integrity or disk-free status.

Simpler acceptable first implementation: omit optional run_id/per-run usage while still returning per-run limits and clearly labeling them as limits, not current usage. Do not approximate per-run usage from `RunDetail.artifacts` because that only represents selected/current outputs and can miss reservations.

## Bounded read and authority algorithm

1. Open explicit read transaction with query_only enabled. Check the actual unexpired owner session and visible-private setting. Capture settings.version and personal_settings.epoch. Do not accept an owner-shaped principal alone.
2. Read at most cap+1 rows per resource in this one snapshot. Runs and watches need only a code-owned scalar sentinel per row; do not decode their data. Files need only authoritative table kind, projected byte_count, and (only when requested) a valid projected run_id. Status is not a filter: every row consumes a count slot. No listing(), detail(), metadata(), checked(), reconcile(), `_view()`, source coverage or file-directory methods are called.
3. Extract scalar fields with guarded SQL CASE. Before JSON parsing, bound input metadata byte length to 64 KiB (including malformed/oversized rows); only then json_valid/object/type checks and scalar projection. Never select full metadata or serialize a large nested byte_count/run_id value. Inspect json_type to reject true/false and real values before integer extraction. A valid file reservation has integer byte_count between 1 and that kind's per-file maximum. Invalid fields make its byte dimension unavailable; its row still counts. A malformed run_id makes requested per-run accounting unavailable because membership cannot safely be inferred. Unrelated names/provenance are never read.
4. For cap+1 overflow, mark that resource count/bytes over-limit/unavailable without presenting a partial sum as a complete total. Other independent resources can still be returned. Unknown `private_files.kind` is outside these two admission buckets; do not silently assign it to either one. Unsupported database tables/schema are a safe unavailable service error, not assumed empty.
5. Compute aggregates with bounded integers in memory. No quota is released for unknown/reserved states, missing files, terminal runs/watches, superseded outputs, cancellation, panel closure, download or exporting data.
6. Close the read snapshot. In a fresh query-only connection recheck actual owner session/expiry, visibility, settings.version and personal epoch. Logout, expiry, hide→show or consent changes deny the response. A current capacity change alone is permitted: the response is explicitly the earlier internally consistent observation, not a promised reservation.
7. Return only the typed aggregate. No status updates, store revision bumps, SQLite writes, reconciliation, file stat/open/read, model calls or network.

SQLite itself must inspect bounded metadata to parse JSON; this is not a claim of constant-time disk access. Row/output bounds prevent application materialization of unbounded metadata. For anomalous oversized metadata, early length guard avoids JSON extraction.

## Shared limits and admission parity

Introduce a dependency-light `work_limits.py` with constants for source file/count/total, artifact file/count/total/per-run count/per-run bytes, and retained runs. Replace corresponding literals in sources.py, artifacts.py, file_store.py, agent_runs.py and work_search.py with imports. Reuse existing responsibilities.LIMITS.definitions rather than creating a second watch quota; avoid circular imports (or move only that constant to work_limits and have LIMITS reference it).

Display receives these constants from the endpoint rather than duplicating TS quota literals. Existing source/artifact list limit wrappers must use the same constants. This is a behavior-preserving extraction; no configuration knob or quota increase.

The first slice need not rewrite admission metadata validation, which currently trusts JSON and can error on corruption. Capacity must honestly return unavailable in those cases and must not predict admission. If a shared bounded reservation reader is introduced into admission later, isolate and review it separately: preserve old-key lookup before capacity checks, same-write-transaction admission, every-row counting, per-run checks and existing reservations. Never make a malformed row consume zero bytes or make idempotent recovery require a new slot.

## Interface integration

- Work workspace: one compact retained-capacity section near saved work / new work actions, with Sources x/100, Work x/100, Outputs x/400 and source/output recorded bytes. Label bytes as retained/reserved logical bytes, not physical disk use. Show remaining slots/bytes only when known.
- SourceUpload: show source aggregate adjacent to the existing explicit retention acknowledgment. Selected `File.size` can support a warning when larger than observed remaining bytes, but selection never uploads automatically. Preserve upload draft and original retry key.
- RunComposer: show retained runs and global artifact capacity plus four-artifact/1-MiB per-run limits. A new deterministic run normally needs two final files; if fewer than two artifact slots remain, warn that its required pair cannot both be reserved at this observation. Do not claim two free slots guarantee outputs: other work, bytes and per-run history can consume them. No up-front reservation redesign in this slice.
- ArtifactList/RunDetail: expose the global output information and optionally exact selected-run capacity. Current displayed output count is not lifetime reservation count. Preview/download/existing readback remain usable at quota, subject to their existing identity/privacy/byte gates.
- Watches: show `Saved definitions x/20; y slots remaining` using server aggregate if available, and explicit text that cancelled/expired/budget-exhausted definitions remain saved and use slots. Hidden mode retains only its existing complete-list count; avoid cross-depending on the visible-only endpoint.
- Unknown or failed capacity load: `Capacity unavailable; the server checks limits when saving.` Never show zeros or an empty progress bar implying unused space. Over-limit/corrupt state says inspection is needed; do not recommend manual deletion, secret cleanup or quota lifting.
- Full state: `No remaining source slots. Existing work and files remain available; this version has no deletion control.` Never suggest cancellation/archiving/download frees space.
- All capacity-driven UI is advisory. Do not add capacity to general disabled expressions. Keep inspect, pause/cancel, same-operation retry, readback/reconcile, resume and existing file download available under their existing contracts. Let backend new-operation admission be authoritative; do not substitute a new key after an uncertain result.
- Capacity request lifecycle is separate from scope freshness and mutation retry. Use ResponseFence plus request generation; clear counts on identity/privacy/offline/stale/unmount, reject late A→B→A replies and refresh on explicit open/refresh and successful relevant mutation. A capacity-only refresh must not clear a draft, reset retention, invalidate scope or block stop controls. No localStorage, query URL payloads, autonomous background notifications or frequent new poll loop.
- English/Chinese parity, accessible plain text before any optional meter, 390px/desktop layouts, no A1 artwork changes.

## Required tests before implementation claim

Backend service + HTTP:

1. Empty store returns exact zero used/full remaining for all four resources and correct shared constants.
2. Exact maxima and byte boundaries; count full independently of bytes, byte full independently of count; four/1-MiB per-run accounting independent of global availability. Final two-artifact warning is advisory only.
3. Reserved/unknown/verified, cancelled/failed/succeeded runs, terminal watches, superseded outputs, standalone artifacts and reserved artifacts not linked in parent membership all count. Reconcile/status transitions do not change capacity.
4. More than cap rows yields no false exact total or partial usable-byte claim. Corrupt/non-object/oversized/deep JSON, absent byte_count, bool/string/float/negative/zero/over-per-file integers and malformed run association yield bounded unavailable dimensions without throwing raw JSON/errors. Other dimensions remain truthful.
5. Authoritative SQL identity overrides embedded fields; no session/token/name/title/report/provenance/body leaks. Test hostile nested values and large excluded fields; bounded output and bounded selected rows.
6. Two simultaneous creators after a near-full observation cannot exceed actual admission. Stale capacity never guarantees a reservation. Existing operation retry still recovers at full count/bytes, cancellation and original readback still work. Keep existing paired artifact production semantics: no false all-or-nothing promise.
7. Anonymous/paired/controller/display/device-agent denied; expired/revoked actual owner denied; current hidden denied; delayed logout, expiry, hide→show and epoch changes deny. Final check must use fresh transaction, not old snapshot.
8. Snapshot remains internally consistent during concurrent writes; counts may be stale but are never cross-transaction totals. Verify no service construction writes and no revision/file/status/coverage/operation-table changes. Patch body-read/reconcile/model/network seams to fail if called.

Frontend behavior (mounted harness, not source regex alone):

9. Correct known/full/unavailable rendering, no NaN/negative/zero fallback, all retained-state explanations and bilingual copy; no count-derived button disablement.
10. Late responses on identity/privacy/offline/stale/close and out-of-order requests cannot restore counts; fresh capacity does not reset run/upload/watch drafts or original retry queue. Failure remains isolated from run stop controls.
11. At full quotas, open an existing run/file, preview/download, pause/cancel and retry original unknown mutation through existing paths; do not create new key. Watch cancel leaves saved count unchanged.
12. All request call sites use current fence and owner-visible policy. One open/refresh does not trigger reconciliation or extra provider calls. Repeated observations are quiet.

## Independently safe integration order

A. After explicit root freeze release, extract constants only; existing focused source/artifact/run/search/watch tests prove unchanged quotas and idempotency. Review source diff before introducing UI.
B. New work_capacity.py + route/runtime wiring + isolated unit/HTTP tests. Do not change any existing command, worker or scope semantics. This backend addition can be reviewed independently.
C. New typed capacity hook/component + Work integration, then source/composer/artifact hints and watch retained-terminal explanation. Capacity is an optional independent read, never a dependency of existing actions. Add mounted lifecycle tests.
D. Independent negative review; focused tests then root-owned full frozen suite/type/build/assets checks; record actual source hashes and checks. Root updates product/handoff/decision/work log and publishes only after aggregate review. Actual browser acceptance remains separate and must use the authorized isolated environment.

Not trivial enough to slip into the current freeze: source constants touch admission and projection adds a privacy read surface. The feature is small but deserves a fresh bounded batch with independent backend/late-response review. No source/test edits were made during this design.
