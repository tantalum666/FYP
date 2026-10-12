# Local recurring responsibilities

Routines are owner-created, deterministic read-only reviews of this desk's saved
calendar and tasks. They run in the existing local scheduler, without model
polling, provider calls, external messages, credentials, scripts or arbitrary
URLs. They do not modify calendar events, task status or computer jobs.

## Schedule and lifecycle

A definition has `title`, `skill`, `frequency`, `start_local` and `timezone`.

- `skill`: `day_briefing` (remaining events today plus open tasks due today or
  overdue), or `task_review` (all open tasks, including waiting and undated tasks)
- `frequency`: `once`, `daily`, or `weekly`; weekly uses the starting weekday
- `start_local`: future local datetime at minute precision, e.g.
  `2026-10-13T09:00`, with no UTC offset; years 2000–2100
- `timezone`: IANA timezone, default `Asia/Hong_Kong`; it remains fixed even if
  the calendar's display timezone changes
- Titles are required, trimmed, and limited to 160 characters
- Unknown fields, skills and frequencies are rejected

The starting instant must be unambiguous and exist in that timezone. Subsequent
civil-time gaps are skipped, not shifted. A repeated hour uses its first
occurrence (`fold=0`) once. Daily repeats preserve wall-clock time rather than
adding 24 UTC hours; weekly repeats preserve the local weekday. The local
minute string is the occurrence key, unique within its routine.

`active` routines become due through `Runtime.tick()`. `paused` routines do not
run. Resuming a recurring routine skips the paused backlog and selects the next
future occurrence. A paused one-off that became overdue runs once after resume.
Cancelling is terminal. A one-off becomes `completed` after its result is stored.
Completed/cancelled definitions cannot be resumed. Pause/cancel dismiss any
pending delivery; historical results remain accessible. The schedule is
immutable: cancel and create a new definition to change it.

Nothing runs while the local service is stopped. On restart, the latest missed
occurrence is evaluated once; older missed occurrences are coalesced. The result
is a current snapshot at execution time, not a reconstructed snapshot of a past
day. `catch_up=true` means earlier occurrences were skipped, not merely that
execution was seconds late. No independent timer or worker is created.

SQLite transactions atomically persist the result, occurrence receipt and next
schedule. Restart/concurrent ticks cannot repeat a committed occurrence. A
persisted forward schedule and last-scheduled watermark also prevent repeat
after clock rollback or history pruning. Invalid local source data produces a
safe `failed` receipt with `ROUTINE_SOURCE_UNAVAILABLE`, without source text in
errors or repeated retry on every tick. The next scheduled occurrence can try
again. This is not a guarantee against arbitrary database or disk failures.

## Results and privacy

Results include `status` (`ready` or `failed`), `skill`, `source=local_rules`,
`as_of`, `timezone`, `local_date`, `counts`, `items`, `suggested_action`,
`truncated` and `catch_up`. Counts cover events, tasks, overdue tasks and waiting
tasks. Items contain source IDs and measured state: event start/end and
occurrence key, or task status/due time/overdue flag. Results include at most
20 events and 20 tasks; counts still describe the full matching set.

Suggested actions are `review_calendar_and_tasks`, `review_tasks`, or
`check_local_sources`. These are UI hints, never executable commands. Counts and
statuses are snapshots and can become outdated. Item titles are projected from
the current source record on each read and labelled `title_source=current_record`;
they are not historical title snapshots. Removed sources have `available=false`.
Private titles respect current privacy settings. User notes, next-step text and
waiting-for text are never copied into result receipts.

All routes require an owner session and visible private context. Paired devices,
controllers and hardware agents cannot access them. When Hide private is on,
routine reads and writes return `PRIVATE_CONTEXT_HIDDEN`, including retries,
before returning user-written titles or consuming a delivery. Local computation
can continue, retaining IDs/counts but no copied source titles or notes. The UI
must hide cached private context while offline, stale, signed out or hidden.

## Pending delivery, recovery and limits

There is at most one pending delivery per routine and 20 across the desk. Later
results still enter history while pending delivery is suppressed. Claiming an
older pending entry resolves to that routine's latest stored result, using the
original delivery ID and a separate `result_run_id`; `coalesced_delivery` makes
that distinction explicit. A routine suppressed by the global cap does not
acquire a delivery retroactively just because a slot opens; its next occurrence
can create one. Its stored results remain directly inspectable.

Claim is an explicit owner action, not a read and not an automatic mount effect.
It atomically marks pending deliveries claimed. A new operation key cannot
claim them again. A lost reply must be retried with the exact same operation ID
and body; clients should deduplicate any actual notification by stable delivery
ID. This is at-most-once claim, not guaranteed visible delivery: closing/reloading
a client after an uncertain reply may lose its in-memory recovery key. Inspect
run history in that case. Reading history never consumes pending delivery.

Idempotency receipts retain only delivery/result IDs and reapply live privacy on
retry. A retry after result history has expired returns the stable IDs in
`unavailable_delivery_ids`, rather than manufacturing a result. The current UI
keeps sensitive request recovery in memory only and uses an explicit reveal
button; it does not create OS or external notifications.

The prototype supports 50 total routine definitions, including terminal ones.
Each detail view exposes the newest 50 results. Storage preserves those 50 plus
an older pending entry if necessary, so no pending receipt is pruned before it is
claimed/dismissed. These bounds are deliberate; there is no general scheduler
framework, arbitrary cron input or automatic deletion API.

## HTTP contract

All paths are under `/api/routines`. Mutations require `X-Desk-Request: 1` and
`X-Operation-Id` (1–100 characters). Same key plus same body replays the receipt;
a different body returns `OPERATION_ID_CONFLICT`. No endpoint needs an AI key.

| Method / path | Body | Response |
| --- | --- | --- |
| `GET /api/routines` | — | `routines`, `pending_count`, `revision`, `server_time`, `limits` |
| `POST /api/routines` | Definition fields above | `routine`, `saved`, `revision`, `operation_id` |
| `GET /api/routines/{id}` | — | `routine`, newest-first `runs`, `revision` |
| `POST /api/routines/{id}/actions` | `action`: pause/resume/cancel; `expected_version` | `routine`, `saved`, `revision`, `operation_id` |
| `POST /api/routines/deliveries/claim` | optional `limit`, integer 1–20, default 10 | `claimed`, `delivery_ids`, `delivery_refs`, `deliveries`, `unavailable_delivery_ids`, `revision`, `operation_id` |

Definition responses also contain `id`, `version`, `status`, `next_run_at`,
`last_scheduled_at`, `created_at`, `updated_at`. UTC instants use ISO 8601 with Z.
Lifecycle actions advance definition version; scheduler execution does not.
Version mismatch returns `VERSION_CONFLICT`; refresh before making a new action.

Run responses contain `id`, `routine_id`, `occurrence_key`, `scheduled_at`,
`created_at`, `delivery_state` and `result`. Delivery state is `pending`,
`suppressed`, `claimed` or `dismissed`. Claimed delivery projections additionally
include `result_run_id` and `coalesced_delivery`; their `id` is the stable delivery
ID. A claim receipt's `delivery_refs` pairs `delivery_id` and `run_id`.

Important errors: `ROUTINE_NOT_FOUND` (404), `ROUTINE_START_IN_PAST` and
`ROUTINE_LIMIT` (422), `ROUTINE_CLOSED`, `ROUTINE_ALREADY_PAUSED`,
`ROUTINE_ALREADY_ACTIVE`, `VERSION_CONFLICT`, `OPERATION_ID_CONFLICT` (409).
Input validation uses the existing `VALIDATION_FAILED` response.

## Verification

`tests/test_routines.py` covers restart catch-up, one-off/daily/weekly scheduling,
DST gap/fold, invalid/unsafe inputs, pause/resume/cancel, optimistic concurrency,
idempotency, concurrent tick/claim, bounded pending/history, clock rollback,
source-table immutability, privacy-safe claim replay, failure receipts and
Runtime/owner-only/hidden-context route integration.

## Owner interface

`RoutinesPanel.tsx` exposes bilingual English/Simplified Chinese creation,
pause/resume/cancel, run history and explicit pending-result reveal. Cancel
requires an inline review; unsaved form text and uncertain writes participate in
the existing draft navigation guard. The form lets the owner choose the local
starting time and IANA timezone explicitly. All content is owner-only and is
masked when the workspace is offline/stale/private-hidden or its embedding
surface applies stricter posture-away privacy.

Reads are fenced by request generation and selected routine. Failed reads clear
cached routine titles and results. Delivery callbacks are separately fenced by
owner/visibility epoch, so a response started before hide→show cannot restore
older private text. Requests use the shared component-memory private mutation
helper, never browser storage. A lost-reply retry is available while the panel
remains open. After navigation/reload, inspect run history rather than blindly
repeating an action. Opening or refreshing the panel only reads records; it
never claims a pending delivery.

Cancelled calendar occurrences and occurrence keys removed by a series change
are treated as unavailable in a result's live title projection. Historical counts
and times remain explicitly labelled snapshots.

`frontend/tests/routines.test.ts` tests lifecycle/reveal guards, source-title
masking and stable delivery deduplication, plus source-level contracts for
privacy fencing, memory-only writes, explicit claim and bilingual controls.
These source-level tests are not a substitute for integrated browser checks.
