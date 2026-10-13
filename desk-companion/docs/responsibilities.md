# Selected task-change responsibilities

Updated 13 October 2026. Implemented local task-only change detection, separate
from [scheduled routines](routines.md). The owner explicitly selects saved task
IDs and fields, reviews the exact current scope, acknowledges local retention
and enrolls a baseline. Enrollment itself creates no alert or initial analysis.
No model, external notification, arbitrary file watcher, calendar watch or
AgentRun is created by this service.

## Scope and what a change means

One immutable definition watches one to ten unique saved task IDs. Later-created
or same-named records never join automatically. The six selectable fields are:

- `status`: authoritative task status, including completed/cancelled
- `due`: saved local due time together with its IANA timezone
- `next_step` and `waiting_for`: exact saved text, compared by local hashes
- `steps`: ordered saved step titles and completion flags
- `progress`: latest evidence ID whose kind is `note`; note text is never read
  by the comparator or copied into a review

Titles are current labels only, not a watched field or historical snapshot.
Scheduling-only pause, snooze, follow-up delivery, unchanged updates, unrelated
records and mere passage of a due time are quiet. No-op dirty markers advance
only the baseline cursor, without a review reservation or workspace revision.
The projection is versioned canonical JSON hashed with SHA-256; hashes are
change-detection metadata, not encryption or anonymization.

This is current-state comparison. A→B→A before evaluation can be quiet. If two
separate evaluations observed A→B and B→A, the pending review records that the
selected field changed, without claiming that current state differs from A.
`catch_up` means multiple dirty markers or coalesced observations; a task update
and its note insertion can produce two markers from one user operation. It is
not an intermediate-change count or a reconstruction of old note/title values.

## Durable transaction boundaries

`ResponsibilityService(runtime)` is constructed after `TaskService`. Its four
SQLite tables retain definitions, per-selected-task dirty mailboxes and field
hashes, change reviews, and hash-only operation receipts with stable references.
Triggers run in the source transaction for task insert/update/delete and note
insert/delete. They only update already-enrolled IDs and contain no source text,
Python callbacks, network requests or provider instructions. Existing UI,
assistant-confirmed and restore writes are covered at the table boundary;
restored new IDs never enroll themselves. Direct external database editing is
not a supported integration.

Enrollment rereads the exact sources and validates the selected IDs/fields,
source version/latest-note tokens and projection hashes in one `BEGIN IMMEDIATE`
transaction. A concurrent committed edit either invalidates the reviewed scope
or happens after the baseline and dirties its mailbox. There is no read/enroll
lost-change gap.

An independent local application worker calls `advance()` (also `tick()`) once
per second through thread offload. It is not part of the legacy posture/task/
routine tick. A worker exception cannot skip those services or voice cleanup.
An unchanged call uses indexed metadata and does not read task projections.
At most ten dirty eligible definitions are evaluated, ordered by a persisted
counter rather than wall time, so busy definitions cannot starve the others.
Daily-capped definitions without an existing pending review are ineligible until
the next permitted budget day; no repeated source reads occur while waiting.

Each evaluation uses a SQLite savepoint inside the write transaction. Source
hashes, dirty consumption, review changes and budget reservation commit together.
Malformed/missing selected sources roll back partial evaluation and block once
with `RESPONSIBILITY_SOURCE_UNAVAILABLE`. Dirty baselines remain intact and no
retry occurs until explicit owner recheck. Unexpected database/process failures
roll back the enclosing transaction and reach the worker's own error boundary.
This is one-host SQLite coordination, not a distributed service guarantee.

## Reviews and budgets

There is one pending local review per definition. A relevant change creates a
stable review ID and reserves one lifetime and UTC-day unit. Further relevant
changes update that same review, increment its version, union bounded selected
IDs/field names and update the latest observation tokens/time. Coalescence
reserves no additional unit and creates no additional pending notification.
There are no monetary charges or provider calls associated with these units.

GET/list/detail never acknowledges a review. Explicit acknowledgment requires its
exact current version. An unseen coalesced version returns `REVIEW_CHANGED`.
Once acknowledged, unchanged ticks stay quiet; a later distinct observed change
may reserve a new review. A source edit not yet evaluated at acknowledgment can
produce that later review, so it is not lost. There is no re-alert just because
the owner has not responded or time has elapsed.

The budget day is a persisted nondecreasing UTC accounting watermark. Clock
rollback cannot restore spent units. `daily_used` belongs to returned
`budget_day`, which need not be today's date after a quiet period or rollback.
Daily exhaustion leaves dirty generations and baseline hashes unconsumed.
The last budgeted pending review can still coalesce. After acknowledgment, a
later change needing another review makes the definition `budget_exhausted`;
it cannot auto-renew or resume. Ordinary task writes are never refused because
a watch's review quota is exhausted.

## Lifecycle and retention

States are `active`, `paused`, `blocked`, `cancelled`, `expired` and
`budget_exhausted`. The last three are terminal and remain visible.

- Pause increments version/generation, stops evaluation and dismisses any pending
  delivery without deleting history
- Resume requires visible-owner authority, the exact definition version and
  `resume_policy: "baseline_now"`; it atomically adopts current selected values
  and discards the paused backlog, without an alert
- Recheck applies only to blocked definitions, validates the same original
  selection and resumes comparison against retained baselines; it never silently
  shrinks the selection or substitutes another source
- Cancel is terminal, fences evaluation and dismisses pending delivery
- Expiry is processed even with no dirty source. It terminates enrollment and
  dismisses pending delivery; retained historical receipts stay inspectable.
  Clock rollback cannot resurrect an already-terminal definition

Retention acknowledgment is required and separate from saved chat or full Work
retention. The locally retained definition includes its owner-written title,
selected IDs/field names, expiry/budgets and field hashes. Reviews contain IDs,
field names, observed tokens/times, versions and delivery states, not copied
before/after text. Current task labels are loaded on visible reads.

Hard bounds:

- Twenty total definitions, including terminal definitions; no automatic deletion,
  replacement, widening, renewal or reset
- Ten selected tasks each; a future UTC expiry no more than thirty days ahead
- One to one hundred lifetime review reservations, one to twenty per UTC day
  (default ten daily)
- Newest fifty retained reviews per definition, preserving pending reviews;
  pruning never deletes baselines, budgets or dedupe references
- Two hundred fifty-six ordinary operation receipts per definition, including
  creation and acknowledgment. At this cap a final pause and terminal cancel
  remain available independently, for at most two additional receipts. A no-op
  repeated pause is rejected and cannot consume the cancellation reserve

Same operation ID/body recovers stable IDs and a freshly authorized current
projection, even after a review was pruned. Different body reuse conflicts.
Receipts contain only request hashes and resource references; response bodies
and source text are not cached durably here. While the same private view remains
valid, a transient lost-reply client retries the original key/body. The service
protocol can also recover that key after fresh authorization, but the current
UI deliberately clears its private draft/retry queue on identity or privacy
epoch changes. In that case reopen current history and inspect the saved result;
the UI does not offer a cross-epoch retry with a cleared key. Capacity failure is explicit; making a new definition does
not erase an old definition's retained records. There is no deletion/forensic
wipe API or promise about existing backups in this slice.

## Owner authority and privacy

Every API requires a real current owner session. Service methods independently
validate the session table, not an owner-shaped dictionary. Paired controllers,
displays and device agents cannot create/read/control/acknowledge watches.
Enrollment stores no session token or credential. The narrow local comparison
grant survives logout and private-hide, but it never impersonates an owner for
Work, provider calls or other effects.

Hidden-owner list and pause/cancel responses expose only opaque definition IDs,
status/version/generation, safe reason codes, times and budget/pending metadata.
No title, selected task ID or field name is exposed. Detail, scope, creation,
resume/recheck and acknowledgment require visible private context.

Authority is checked in each source/write transaction and again in a fresh
transaction before returning private content, including operation replay.
The initial settings version must still match, so hide→show cannot revive a
pre-hide response. Any intervening settings edit conservatively produces
`RESPONSIBILITY_CONTEXT_CHANGED`; a mutation may already have committed. The
service supports original-key recovery under fresh authority, while the current
UI clears that older private queue and asks the owner to reopen current history
before repeating anything. It never silently substitutes a new operation key.
Client identity/privacy/selection generations additionally fence delayed replies.

## HTTP contract

All routes are under `/api/responsibilities`. Mutations require the existing
`X-Desk-Request: 1`, same-origin checks and `X-Operation-Id` (1–100 characters).

- `GET /scope?task_id=...&field=...`: repeated IDs/fields. With no IDs, returns at
  most 500 candidate labels and `scope_revision: null`, never implicit selection.
  With IDs, returns that exact selection and its fingerprint. Default fields
  when omitted are status/due/progress
- `POST /`: `title`, `kind: "selected_task_changes"`, unique `task_ids`, unique
  nonempty `fields`, `scope_revision`, explicit `retain_change_history: true`,
  UTC `expires_at`, strict integer `review_budget` and `daily_review_budget`
- `GET /`: `responsibilities`, `pending_count`, `hidden`, `revision`,
  `server_time`, `limits`
- `GET /{id}`: `responsibility`, newest-first `reviews`, live `selected_tasks`,
  `revision`; missing labels have `available: false`
- `POST /{id}/actions`: `action: pause|resume|cancel|recheck`, `expected_version`;
  `resume_policy: "baseline_now"` required only for resume
- `POST /{id}/reviews/{review_id}/acknowledge`: `expected_review_version`

Mutation replies contain current `responsibility`, `saved`, `revision` and
`operation_id`; acknowledgment also returns stable `review_id` and
`acknowledged: true`. Background reviews do not change definition versions;
owner lifecycle controls, blocking, expiry and lifetime exhaustion do.
Each coalescence/acknowledgment/dismissal changes the separate review version.

Important errors include `RESPONSIBILITY_SCOPE_CHANGED`,
`RESPONSIBILITY_SOURCE_UNAVAILABLE`, `RESPONSIBILITY_SOURCE_KIND_UNSUPPORTED`,
`RESPONSIBILITY_CONTEXT_CHANGED`, `RESPONSIBILITY_CLOSED`,
`RESPONSIBILITY_LIMIT`, `RESPONSIBILITY_OPERATION_LIMIT`,
`RESPONSIBILITY_EXPIRY_INVALID`, `RESPONSIBILITY_ACTION_INVALID`,
`REVIEW_CHANGED`, `REVIEW_NOT_PENDING`, `VERSION_CONFLICT` and existing
owner/privacy/operation errors. Errors contain no source text. Unsupported
calendar/source/artifact kinds and unknown predicates/URLs/scripts are rejected.

## Explicit Work follow-up and verification

The separate UI may prefill the existing deterministic Work composer with the
exact enrolled task IDs and a code-owned goal. This is only a draft. It must
re-fetch Work scope and require normal explicit full-data retention and Start.
Missing selections require a new reviewed choice, not silent scope shrinkage.
No provider, memory, conversation, connector or mutation permissions are carried.
Acknowledgment and Work Start are independent. Watch cancellation does not cancel
an independently owner-started Work package. This minimal slice does not promise
exactly one Work run per review and has no direct linked-run endpoint.

`tests/test_responsibilities.py` uses real SQLite and real task writes to exercise
10,000 quiet ticks, selected projections, enrollment/edit ordering, rollback,
concurrent evaluation, coalescence, restart, review-version acknowledgment,
daily/lifetime/rollback limits, bounded history and stop reserves, missing data,
owner HTTP/hidden/replay/late-privacy guards and fairness. Its explicit Work test
independently downloads actual Markdown/CSV bytes, recomputes hashes, parses CSV
and verifies that the watched task remains unchanged. Parent-owned
`tests/test_responsibility_worker.py` exercises actual application lifespan
failure isolation and scheduler-off behavior. Independent audit and aggregate
checks are recorded separately; source/protocol tests do not claim real browser,
model, microphone, remote-service or hardware acceptance.

Nothing runs when the local service is stopped. This feature cannot watch remote
mailboxes or arbitrary files, infer semantic importance, reconstruct every
intermediate edit, prove that a person saw a card or grant external capabilities.
