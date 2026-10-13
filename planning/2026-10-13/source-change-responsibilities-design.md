# Group 2 · Scoped source-change responsibilities

Date: 2026-10-13. Status: engineering proposal, not an implemented capability or a newly approved permission. Continuation of the existing full-project intake; focused reread of current product, handoff, continuous-capability plan, task/routine/run/source contracts and implementation. No implementation or root-document edits accompany this proposal.

## Recommendation and useful first outcome

Build **Watch selected task changes** first: the owner selects particular saved tasks and the fields worth watching, enrolls their current state without an initial alert, and receives one durable local change-review receipt when those fields change. Further changes coalesce into that receipt until explicitly acknowledged. The receipt can open an owner-reviewed deterministic Work package with actual Markdown/CSV evidence output. No model key, credential, browser, external account or third-party write is needed.

Example: watch the status, due date and progress updates of the already-selected “Prepare Progress I” task. Another existing authorized app action records progress or changes its deadline. The responsibility processes that committed change once, indicates which selected fields changed, and offers “Compile current task evidence.” The owner reviews the current selected records and retention, starts Work, and can open/download verified files. Acknowledgment means “I saw these changes”; it does not complete the task, accept an external action or authorize a model.

The automatic bounded follow-up in this slice is the local **change review**, with its own durable run/receipt. A full AgentRun remains an explicit owner-started follow-up. Do not advertise unattended model planning or automatic artifact generation. This is a useful end-to-end increment rather than a fixed timer repeatedly saying that tasks still exist.

Calendar change watching is a closely specified second increment below. Do not delay the task-first path to build a universal event bus, external connector polling or a new scheduler.

## Current-code constraints that drive the design

- `backend/desk/routines.py`: `RoutineService.tick()` executes once/daily/weekly reviews, `_result()` reads all matching current tasks/calendar, occurrence uniqueness and forward watermarks prevent schedule duplicates. One pending delivery per routine is useful precedent, but scheduled review output may be identical on successive days. A schedule occurrence is not a source-change cursor.
- `backend/desk/tasks.py`: create/action writes run inside `Store.operation`; `evidence()` records task progress. Every action changes task version, including pause/snooze. `tick()` can clear `next_check_at` without changing semantic task content. Therefore task version or global workspace revision alone is not a useful notification predicate.
- `backend/desk/store.py`: `connection(write=True)` uses `BEGIN IMMEDIATE`; `operation()` makes mutation, receipt and revision atomic. Generic `records.sequence` mixes many domains and does not contain a uniform source/revision contract. Do not infer source changes by parsing its human-oriented action strings.
- Calendar writes occur in `Store.create/event_action` and `ExchangeService` import/restore paths. Occurrence edits live in `exceptions`, and the parent event version is also changed by ordinary occurrence actions. Calendar watching must cover imports and exceptions, not only the visible calendar action endpoint.
- `SourceService` uploads are immutable revision-1 byte snapshots. An artifact revision is a new ID with an explicit predecessor. Uploading a same-named file does not update the old source; file corruption is an integrity failure, not new content to process. No file watcher or directory permission exists.
- `AgentRunService.create()` requires a real current owner session, exact scope revision and retained-work acknowledgment. The worker rechecks session/visibility/generation; graceful restart pauses it. It permits at most 100 retained runs and artifact reservations have their own lifetime limits. Calling it automatically every time a task changes would create retention pressure and cannot legitimately bypass the owner-session boundary.
- Current Runtime has one local scheduler plus the separate bounded agent-run worker. It is not a continuously available cloud service when the local API is stopped.

Relevant contracts: [routines](../../desk-companion/docs/routines.md), [tasks](../../desk-companion/docs/task-tracking.md), [runs](../../desk-companion/docs/agent-runs.md), [sources/artifacts](../../desk-companion/docs/sources-and-artifacts.md), [continuous plan](continuous-agent-capability-plan.md), [retrieval design](work-history-retrieval-design.md).

## Scope and semantics

### Task-first enrollment

New strict `ResponsibilityCreate` schema:

- `title`: trimmed 1–160 characters
- `kind`: literal `selected_task_changes`
- `task_ids`: 1–10 unique existing IDs, explicitly selected, including closed tasks if the selector offers them
- `fields`: nonempty unique subset of `status`, `due`, `next_step`, `waiting_for`, `steps`, `progress`
- `scope_revision`: server-issued fingerprint of the exact selected IDs, current source tokens, field list and projection schema version, not a broad global revision
- `retain_change_history: true`: required explicit acknowledgment of locally retained definition, identifiers, field-change receipts and limited history
- `expires_at`: explicit future UTC instant, at most 30 days ahead
- `review_budget`: strict integer 1–100, lifetime per responsibility
- `daily_review_budget`: strict integer 1–20, UTC accounting disclosed; default 10

Unknown fields, source IDs, URLs, provider settings, arbitrary predicates/scripts and effect instructions are rejected. Definitions are immutable apart from pause/resume/cancel. Widening IDs/fields, renewing lifetime or changing budgets requires a new reviewed enrollment. Creation never runs initial historical analysis and never alerts on preexisting content.

Canonical watched projections:

- `status`: authoritative tasks.status, not a stale duplicate inside JSON
- `due`: due_local + timezone; a clock crossing the deadline is not a source change
- `next_step`, `waiting_for`: exact saved text, hashed locally but not copied into receipts
- `steps`: canonical ordered stable step data, including completion flags
- `progress`: newest task_evidence ID whose kind is `note`; reading the note body is unnecessary

Per-field hashes use versioned canonical encoding. A no-op same-value edit, scheduling-only pause/snooze, follow-up claim, UI refresh, model result, artifact generation or unrelated source mutation must be quiet unless it changes a selected projection. Watching `progress` reports that a new progress record exists; it does not interpret the text or infer completion. Title edits alone do not trigger the first slice; titles are live labels, not historical evidence.

The authority is bounded to local comparison and in-app receipts for those selected fields. A selected task's private status does not authorize a new provider or communication recipient. This single-owner workspace is not a new multi-tenant ACL model.

### Calendar next, with explicit selection granularity

Use a separate literal `selected_calendar_changes`, not task IDs disguised as sources. Select either an exact series ID with a clear “this whole series, including its exceptions” disclosure, or exact `{event_id, occurrence_key}` entries; do not silently convert an occurrence selection into its entire series. First calendar implementation should choose one mode and ship it completely, preferably exact occurrences.

An occurrence projection resolves the current series plus its exact exception with `is_occurrence`, records available/cancelled/completed/start/end/timezone, and hashes only explicitly watched fields. Series edits that remove the selected occurrence make that selected reference unavailable; they must not select the new replacement occurrence automatically. A change to another occurrence is quiet. A whole-series projection, if later admitted, includes canonical exceptions with a declared hard bound; exceeding it blocks with a safe code, never silently truncates. Date-window membership and midnight are separate temporal triggers, not content change events.

New Google fetches, account access or polling are not part of this feature. Already-confirmed local imports are merely local committed source mutations. Imported new IDs never enroll themselves.

### Immutable files and artifacts

Reject uploaded `source_ids`, artifact IDs and filenames in initial watch requests with `RESPONSIBILITY_SOURCE_KIND_UNSUPPORTED`. Future file replacement must explicitly bind a logical collection and owner-approved new snapshot membership; filename equality and `supersedes_id` alone are not standing permission. An immutable source hash mismatch blocks access rather than claiming “updated source.”

## Durable change detection without meaningless polls

Use a **bounded per-enrollment dirty mailbox**, not an unbounded global event journal. Proposed tables in `backend/desk/responsibilities.py`:

1. `responsibilities(id, kind, data, version, generation, status, created_at, expires_at, review_limit, reviews_used, budget_day, daily_used, blocked_code, updated_at)`
2. `responsibility_sources(responsibility_id, source_kind, source_id, occurrence_key, dirty_generation, consumed_generation, observed_source_token, field_hashes, PRIMARY KEY(...))`
3. `responsibility_reviews(id, responsibility_id, sequence, from_tokens, to_tokens, changed_fields, changed_ids, first_observed_at, last_observed_at, version, delivery_state, catch_up, result_code)`
4. `responsibility_operations(id, request_hash, receipt_ids)` containing stable references only; live responses must reapply privacy
5. Optional follow-up links `responsibility_followups(review_id UNIQUE, agent_run_id, intent_hash, operation_key UNIQUE, state)` only when implementing the direct run linkage described below

For task-only scope the primary key may omit occurrence_key; if a generic key is used, normalize absent keys to `''` rather than nullable SQL uniqueness. Add a partial unique index for at most one unacknowledged pending review per responsibility.

Install SQLite triggers after TaskService has created its tables. Triggers increment only mailbox rows whose source ID is already enrolled, in the **same source mutation transaction**:

- task INSERT/UPDATE/DELETE: mark selected task rows dirty; broad row triggers are acceptable because projection hashes filter irrelevant changes
- task_evidence INSERT with `kind='note'`: mark selected task rows dirty for progress watching
- later calendar: events INSERT/UPDATE/DELETE and exceptions INSERT/UPDATE/DELETE dirty selected references by event ID; projection comparison filters unrelated occurrences

Triggers write no titles, notes, content, snapshots, source credentials or operation bodies. They do not call Python, network or a model. They cover assistant-confirmed edits, exchange/restore and normal UI actions without requiring every new write path to remember a notification hook. They do not make raw external database editing a supported integration.

`ResponsibilityService.tick()` is called from the existing Runtime tick and selects only enrolled rows whose dirty_generation differs from consumed_generation. An unchanged tick is an indexed metadata query, not a full source scan, repeated report or model poll. Triggers provide durable wake evidence; a best-effort in-process event may reduce latency but is never the correctness mechanism.

### Enrollment transaction

Validate the real visible owner and retention input. In one short write transaction, reread exactly selected records, validate the scope fingerprint, calculate canonical field hashes, insert definition and mailbox baselines, and persist the idempotency receipt. A concurrent mutation either precedes the baseline or dirties the new mailbox after it; there is no read-then-enroll gap. Default is “watch changes from now,” with no initial notification.

### Evaluation transaction and coalescing

With `BEGIN IMMEDIATE`, select at most ten fairly ordered dirty responsibilities per tick. Validate state/expiry and budget; load at most ten selected tasks for each. Compare canonical field hashes, consume the observed dirty generations and save new hashes in the same transaction as the review update.

- No selected field difference: advance cursor only, no review, budget charge, app revision bump or delivery
- Relevant difference and no pending review: insert one review, reserve one budget unit, set pending state, atomically advance cursor
- Relevant difference with pending review: update that same receipt, increment its version, union changed IDs/field names, update last_observed_at/tokens; no new notification ID and no new review budget unit
- A field changed back before the evaluator ran can be equal to its baseline and stay quiet. This is current-state-change detection with coalesced missed edits, not a promise to retain every intermediate transition
- If separate committed evaluations observed A→B then B→A, the one pending receipt states that saved changes occurred, with current labels/values clearly projected as current; it must not falsely claim that current state still differs from the original state

No copied before/after notes are required. Historical receipt means “these selected fields changed between these observed versions.” Current source detail is opened through its existing guarded API. `catch_up` means coalesced unprocessed revisions/restart state, not a reconstructed past snapshot. Only claim intermediate-change counts if the selected projection contract can establish them; dirty_generation is not a count of semantic changes.

Restart uses the persisted mailbox and receipt. It does not re-enroll, reset budgets, replay an acknowledged review, manufacture a fresh ID or scan arbitrary old sources. Initialization must not reset consumed_generation or field_hashes. Database transaction rollback leaves both source and dirty marker unchanged. Migration creates no watchers and sends no initial alerts.

## Controls, acknowledgment and budgets

Statuses: `active`, `paused`, `cancelled`, `expired`, `budget_exhausted`, `blocked`. Cancelled/expired/exhausted are terminal for this definition. “Blocked” holds a safe reason plus dirty state until explicit owner recheck; no retry every tick.

- Pause fences generation, stops comparisons and dismisses pending delivery; retained reviews remain inspectable
- Resume requires visible owner, expected version and explicit `resume_policy: 'baseline_now'`; compare/rebaseline current selected records atomically, discard the paused backlog, disclose that behavior. A different catch-up policy can be added later as an explicit choice
- Cancel is terminal and generation-fenced; it clears pending delivery and prevents later automatic review publication
- Hide-private does not revoke the narrow local hash comparison grant, just as current local routines can compute metadata while hidden. Detail, scope, acknowledgment, enrollment and Work creation remain denied. List and pause/cancel may expose only opaque IDs/status/budgets, following agent-run hidden controls; no title or field names
- Definition survives owner-cookie expiry so local comparisons continue under enrollment, but every owner read/control requires current owner authority. No expired cookie is reused to create a full AgentRun
- Expiry ends enrollment whether or not there are new changes; terminal state must remain visible without generating a new alert

Proposed bounds: 20 definitions including terminal definitions, ten selected tasks each, one pending receipt each, newest 50 review receipts plus pending/linked receipts, lifetime 100 review creations per definition. No automatic definition reset or replacement. Coalescing is bounded by selected IDs/field enums, not appended free text. Ten evaluated responsibilities per tick with persisted fair ordering prevents one busy definition starving others.

Daily review creation budget exhaustion preserves dirty mailboxes without consuming their baseline. Next UTC budget day makes only pending dirty work eligible; an unchanged source does not wake. Persist a nondecreasing budget-day watermark so clock rollback cannot restore spent quota. Lifetime exhausted is terminal and does not auto-renew. Capacity failure must return a clear blocker before enrollment; source mutation itself must never be refused because a watch cannot deliver.

Acknowledgment is separate from GET/reveal and from full Work start: `POST /{id}/reviews/{review_id}/acknowledge` with exact review version and operation ID. If a new change coalesced since the owner saw the receipt, return `REVIEW_CHANGED`; do not acknowledge unseen changes. Same-key same-body lost-response retry returns the original stable receipt references with live privacy. Reading or mounting a panel never consumes it. Acknowledgment marks the pending item acknowledged; a later distinct observed source change may create one new item. No re-alert merely because time passed or the owner did not respond.

## HTTP and UI seams

New owner-only router `/api/responsibilities`, mounted alongside routine/run routes in `backend/desk/app.py`; preserve `/api/routines` behavior and response schemas.

- `GET /scope?task_id=...`: bounded current candidates/selection tokens; no automatic “all tasks” enrollment
- `POST /`: strict creation above; existing `X-Desk-Request: 1` and `X-Operation-Id` requirements
- `GET /`: definitions, pending counts, server time, limits; hidden projection is metadata-only
- `GET /{id}`: definition, exact enrollment refs, bounded review history, live current labels
- `POST /{id}/actions`: `action: pause|resume|cancel|recheck`, expected_version; resume_policy only for resume, recheck only blocked and visible
- `POST /{id}/reviews/{review_id}/acknowledge`: expected_review_version

Errors include `RESPONSIBILITY_SCOPE_CHANGED`, `RESPONSIBILITY_SOURCE_UNAVAILABLE`, `RESPONSIBILITY_SOURCE_KIND_UNSUPPORTED`, `RESPONSIBILITY_CLOSED`, `RESPONSIBILITY_LIMIT`, `REVIEW_CHANGED`, plus existing owner/private/version/operation errors. Errors never interpolate source text. Unexpected corrupt projection blocks once and leaves cursor intact.

UI: retain `RoutinesPanel.tsx` scheduled routines; add a sibling `ResponsibilitiesPanel.tsx` or explicit “On selected changes” mode whose form and types are separate. Do not overload `frequency` with an invisible “every second” schedule. Reuse `usePrivateMutation`, `useDraftGuard`, workspace owner/visibility epochs and transient-read safeguards from Work. Add `responsibilityTypes.ts` and a dedicated hook with generation fencing. Show exact task selection, watched fields, baseline date, expiration, local-only behavior, limits and distinct retention acknowledgment before creation. English/Simplified Chinese labels must describe the same semantics.

Pending card: “Selected task changes / 所选事务有更新”; latest observation time, changed field labels, live source link, “Acknowledge / 已查看,” “Compile current evidence / 整理当前证据,” pause and cancel. Receipt body says current titles are current records; no invented old/new values. No OS, email, Slack, audio or remote push integration. Hide/offline/stale/owner-change clears private results and fences delayed replies; hidden stop controls remain usable with metadata only. Merely opening History or refreshing is never acknowledgment.

## Bounded Work follow-up: minimal and stronger variants

**Recommended first implementation:** “Compile current evidence” explicitly prefills the existing Work composer with exactly the still-available enrolled task IDs and a deterministic goal template. Existing Work UI must re-fetch scope, show current selections/full-data retention and require its normal explicit Start. It must not carry memory, conversation, provider grants, browser/connector tools or mutation proposals. This matches the existing chat-to-Work handoff pattern. Attach source review ID as a validated informational origin only if an origin schema is added; do not accept a client-authored origin as authority. Task edits after the change receipt are disclosed as current Work acquisition, not falsely pinned historical evidence. Acknowledgment and start remain independent.

This variant proves source change → durable review → owner starts bounded deterministic work → independently verified retained artifact with no changes to worker authority. Repeated clicks before starting merely refill the same draft; Start retains existing stable operation-ID behavior. It does not promise globally at most one run per review.

**Only if exactly-one direct linkage is required in this batch:** implement a dedicated `POST /{id}/reviews/{review_id}/follow-up` with review version, current scope revision and explicit full-work retention. Persist a server-built immutable RunCreate intent and deterministic operation key before calling AgentRunService; recover by that key, never create a replacement after lost reply. Add a trusted parent checkpoint to run creation/publication so cancellation between intent reservation, child creation and linking cannot publish new work under cancelled authority. Respect lock ordering; do not hold a write connection while `AgentRunService.create()` opens its own write transaction. Unique review link plus canonical-intent validation prevents duplicate clicks/op-ID changes creating multiple children. This is more code than the first useful slice and must not be claimed without its race tests.

Watch cancellation does not silently cancel an independently owner-started Work package in the minimal composer variant; UI states these are independent and links its controls where known. In the direct owned-child variant, define explicit propagation to unstarted/running child with generation fences, without deleting existing artifacts or pretending cancellation undoes effects.

Automatic model runs, automatic reauthorization after logout, recurring new full artifacts and new external effects remain later work requiring explicit scoped grants and storage/usage policy. A model budget is not a currency spending approval. This proposal grants none.

## Implementation order and evidence

1. Add task-only models/tables/triggers, baseline enrollment, bounded local evaluator and owner routes; isolated real SQLite tests
2. Add bilingual selection/review/acknowledgment/stop UI and existing Work-composer handoff, with fresh scope and explicit Start
3. Run deterministic real-file end-to-end acceptance: create selected/unselected tasks, enroll, modify selected task, inspect single receipt, restart, acknowledge, compile current evidence, independently reopen Markdown/CSV and verify hashes/content
4. Add calendar exact-occurrence projector and trigger coverage as a separately tested increment; no unsupported watch type in the initial UI
5. Update capability contracts only to the scope actually verified; actual browser interaction remains separate from source-wiring tests

Expected code seams: new `backend/desk/responsibilities.py` and strict schemas; Runtime construction after tasks and mounting/tick integration; optional small Work handoff interface extension; frontend workspace sibling panel/types/hook; `tests/test_responsibilities.py`, frontend responsibility tests and mounted browser scenario. Do not edit the A1 layer, independent DeviceApp layout, hardware adapters, provider defaults or existing routine scheduling semantics.

## Negative acceptance matrix

The following are required, not optional hardening:

1. Enrollment alone, first restart, 10,000 unchanged ticks and unrelated task/calendar mutations produce zero review receipts, provider requests and artifact reservations
2. Concurrent edit/enrollment is either in the baseline or observed once afterward; no lost transaction boundary
3. Same-value edits, task snooze/pause, follow-up scheduling and title-only changes do not trigger unselected fields; selected note insertion triggers progress without copying its text
4. One selected plus one unselected task: only the selected task is queried for projection and retained in review; later new IDs never join enrollment
5. Duplicate mutation retry, concurrent ticks and crash before/after commit yield one stable pending receipt; operation replay does not dirty unchanged source again
6. Two changes before acknowledgment coalesce under one ID with newer version; stale acknowledgment is refused; current acknowledgment followed by unchanged ticks stays quiet
7. A→B→A before evaluation is disclosed as coalescing and may be quiet; never claim complete intermediate history or a historical B snapshot
8. Restart and receipt pruning do not reset baselines/budgets or re-alert acknowledged versions; baseline cursors survive older review retention pruning
9. Daily and lifetime limits include committed review reservations, survive restart/clock rollback, never auto-renew lifetime and never deny ordinary task mutation
10. Pause/cancel races with processing cannot commit new review publication after the fence; resume establishes the disclosed baseline and does not replay paused backlog
11. Expiry terminates watches without full AgentRun creation; owner logout blocks private API use but does not mint/extend a session for background work
12. Paired controllers, display/device agents, forged owner-shaped dictionaries and missing owner sessions cannot create/read/acknowledge these responsibilities
13. Hide→show, logout→new login, selection change, stale/offline and delayed successful/error response races cannot restore old titles or consume unread receipts; hidden pause/cancel still works
14. Same-key retries after privacy change return stable IDs only or privacy denial, never cached private content from operation responses; wrong-body reuse conflicts
15. Corrupt/missing selected source blocks once with a content-free code, preserves useful cursor state and never substitutes a different record; recheck is explicit
16. Source/artifact IDs, same-named new uploads, arbitrary URLs/predicates and prompt instructions in task text cannot enroll more sources, call a tool, authorize data transmission or change a task
17. Work handoff does not start on mount/click alone, bypass full-data retention, retain an old scope revision or add provider/memory/connector choices; cancellation of its form starts nothing
18. Work output records current actual source observations; a later task edit cannot be represented as the version that originally triggered the review. Removed selected tasks require a new reviewed choice, never silent scope shrinkage
19. Follow-up never marks watched task completed, accepts drafts, sends messages or changes calendar. Downloaded Markdown/CSV is genuinely read back and correctly escaped, not a UI-only success label
20. Calendar increment: exception edits/import/restore are detected; an unrelated occurrence stays quiet; removed/shifted recurrence does not enroll its replacement; whole-series scope never inferred from one occurrence
21. If direct linked start is implemented: crash at reserve/create/link, cancellation at each boundary, distinct client op IDs, colliding child receipts and unavailable result recovery do not duplicate/adopt unrelated work or bypass the trusted parent fence
22. All failure messages/UI states have English/Chinese parity, and readable historical metadata is never presented as proof of a source's historical title, complete intermediate history or live third-party capability

## Remaining limits to state plainly

This is a local committed-data change detector and deterministic review path. It cannot see a remote mailbox, watch arbitrary files, reconstruct every intermediate edit while stopped, reason semantically about whether changed content matters, guarantee a person saw a displayed card, run after the local service stops, or restore private context after access is revoked. Those limits do not prevent shipping the task-first useful path now.
