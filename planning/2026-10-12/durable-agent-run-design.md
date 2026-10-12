# Group 2｜Durable goal-driven agent runs

Date: 12 October 2026. Status: **implementation proposal, not a delivered capability**. This supersedes “add another voice provider next” as an engineering priority for the current personal-agent request. It does not supersede the product’s posture loop, owner approvals, privacy controls, A1 artwork, or unknown-write recovery rules.

## 1. Recommendation and the user-visible result

Add a **durable goal/run layer above the existing services**, not another task checkbox or a larger synchronous chat loop. A person should be able to request a result, inspect a bounded plan, supply missing information, leave the page, return to actual progress and artifacts, change constraints, and continue without repeating completed effects.

The first substantial vertical slice is a **research/work package**:

> “Use these selected project notes and requirements CSV, my chosen open tasks and next-week calendar, and these official reference pages. Produce a sourced gap comparison and an action list. Save a readable report and CSV. Prepare the two follow-up changes I select; ask before saving changes to my tasks or calendar.”

The run must actually ingest selected sources, preserve their provenance, calculate/check structured facts, produce downloadable immutable Markdown and CSV/JSON files, prepare the requested application edits, observe the owner’s decisions, reread the saved results, and report which requested outcomes exist. It must survive interruption after source collection, during review and after an external write with a missing receipt. A shorter useful variant uses selected local files and app records without web access. It is labeled accordingly, not sold as a web-research agent.

This is a reusable goal/plan/tool/result loop, not a hard-coded “create demo record” recipe. A deterministic report builder remains useful when no model is configured; arbitrary natural-language planning then explicitly remains unavailable. Scripted planner tests exercise orchestration, not real model intelligence.

**The full web/application journey is not accepted until a real adapter is integrated and exercised.** Available platform tools in the development conversation are not automatically tools inside Desk Companion. No LCU, browser, search engine, external account, remote desktop or model access is presumed by this design.

## 2. What the current code actually does

Reviewed the local first-checkpoint source on the `50e174f50a4130b3c666f836f666f6aa4cde4b32` base. The parent owns the final publication SHA; this document does not claim that a local checkpoint has been published.

| Current seam | Verified behavior | Missing responsibility |
| --- | --- | --- |
| `backend/desk/text_ai.py: TextPlan, TextAssistant._reply` | One structured tool decision per response; three iterations; only `last_tool_result` retained; exits on first proposal/job; request holds the text lock | Persisted plan, multiple accumulated observations, continuation after approval, resumable work, useful outcome verifier |
| `TextAssistant.generate` | Qwen/Gemini transport; JSON/Pydantic validation; 20-second request timeout; 1,600 output-token setting; numeric usage | Per-run budget reservation, invocation identity, uncertain provider-call recovery, bounded total input/response bytes, cancellation-safe late-return fence |
| `backend/desk/tasks.py` | Durable personal commitments, versioned progress, user-confirmed completion and check-ins | `TaskStep.done` is a user-facing checkbox, not an executable dependency or verified action |
| `backend/desk/jobs.py` | Immutable reviewed intent, single effect, version/hash approval, independent verification, cancellation and unknown recovery | A job is not a goal; no parent run resumes reasoning after job completion |
| `backend/desk/assistant.py` | Typed reads and proposals; no model confirmation tool; durable idempotent confirmation | Multiple review boundaries are not linked into one outcome; source/proposal/step provenance absent |
| `backend/desk/runtime.py` and `app.py: lifespan.worker` | Single-runtime SQLite services; separate rules/advice/job workers | No bounded run worker, lease generation or durable run progress/delivery log |
| `backend/desk/routines.py` | Durable deterministic local brief/task-review occurrences and delivery claims | No general agent orchestration; extending this table into a universal workflow would confuse recurring responsibility with one execution |
| `frontend/src/workspace/AssistantPanel.tsx`, `ComputerJobsPanel.tsx` | Chat/proposal/job UI, identity/private response fences, uncertainty-aware writes | Goal progress, plan revisions, source evidence, artifact viewer/download, steering and takeover |

Keep four concepts distinct: **conversation** (interaction), **personal task** (commitment), **agent run** (bounded work toward a result), **computer job/proposal** (one effect and its review). A run may link to each; none silently completes another.

## 3. Public-product lessons and limits

Public dot documentation describes independently inspectable work, scoped task context, steering existing work, and work that can pause/continue without every check being a recurring timer. It also warns that a completed run alone does not prove the result was achieved. These support a visible run and evidence model, not a claim about its private implementation. [Tasks and memory](https://learn.chatgpt.com/docs/dots/tasks-and-memory)

Work controls should distinguish pausing the coordinator, stopping a delegated activity, and cancelling future schedules. Completed actions are not undone by stopping. Our first slice uses one worker and explicit child-job links; it does not invent parallel delegated agents or undo guarantees. [Control your dot](https://learn.chatgpt.com/docs/dots/controls)

Public changes also emphasize continuing existing threads and inspecting/revising work. The design therefore keeps stable run IDs and revisions rather than restarting a new run for every clarification. [October 5–9 dot update](https://learn.chatgpt.com/docs/whats-new/dots-october-9-2026)

Muse’s public workflow documentation describes dependent stages, progress and separate child controls. The first FYP slice keeps chat and multiple run views usable, with a single bounded worker; it does not claim parallel child-agent execution. Dependency failures block affected dependents while completed evidence remains inspectable. [Muse Code workflows](https://dev.meta.ai/docs/muse-code/workflows)

The expanded [dot capability map](../../research/2026-10-12-personal-agents/dot-capability-gap.md), [Muse capability map](../../research/2026-10-12-personal-agents/muse-capability-gap.md) and [Grok](../../research/2026-10-12-personal-agents/grok.md) capability studies inform the roadmap. Their consumer capabilities are not SDK guarantees. LCU findings must be incorporated at the adapter boundary before claiming actual computer use.

## 4. Bounded implementation scope

### Deliver together

1. Owner-only run creation/detail/list/actions, persisted plan/steps/attempts/events, one bounded background worker, restart recovery and explicit pause/cancel/resume/steer/takeover
2. Typed read registry for selected source IDs, task/calendar queries, capability discovery and deterministic table calculations; all existing owner/destination/privacy checks preserved
3. An accumulated evidence bundle and provider planner adapter; model decisions cannot confirm effects, expand grants, register tools or choose arbitrary execution code
4. Existing proposal/job linkage, durable continuation when review and execution change, independent outcome verification
5. Immutable owner-private Markdown/TXT/CSV/JSON artifacts, list/read/download and provenance; source ingestion by opaque IDs, never model-supplied host paths
6. A run panel with plan, current block, activity, review links, evidence and results, usable after page reload; English and Simplified Chinese
7. Deterministic and scripted-planner integration tests using real SQLite and filesystem effects; actual browser/application adapter tests when that adapter is ready

### Exclude from this slice, while keeping extension points

No arbitrary shell/code interpreter, arbitrary filesystem access, recursive multi-agent spawning, general external messaging, purchase/login automation, hardware action planning, self-created permissions, scheduling arbitrary writes, public hosting, HTML/JavaScript execution, or unlimited research loop. Rich PDF/DOCX/HTML export, search discovery, additional authenticated apps and background watches are subsequent adapters with separate evidence. A provided-URL fetch is not a search engine.

These are capability limits, not a reason to stop at a mock: the selected file/app workflow must generate useful actual files and, after review, actual application records before the slice is called complete.

## 5. Data contracts

All inputs use `StrictModel` with forbidden extra fields. All persisted record IDs are generated by the server; model-local plan keys are validated and mapped to server step IDs, never treated as authority. Labels and source text are untrusted. Proposed limits are engineering defaults, not measured capacity or user-approved paid spending.

### RunCreate

- `goal`: 1–4,000 characters; `title`: optional 1–160; `language`: `en|zh`
- `source_ids`: at most 12 selected immutable source references; `task_ids`: at most 10; optional explicit timezone-aware `calendar_range` of at most 31 days
- `requested_outputs`: at most four `{format: markdown|text|csv|json, label, acceptance_kind}` entries
- `requested_effects`: optional named action families, limited to the installed typed capabilities; not executable arguments and not approval
- `conversation_id`, `task_id`: optional owner-visible links; no automatic transcript retention, memory saving or task completion
- `planner_mode`: `configured_model|deterministic_work_package`; `limits`: values at or below operator ceilings
- `persist_run`: explicit `true` in this “Start persistent task” flow, with a short retention explanation; a temporary chat does not silently become a durable goal
- `scope_revision`: binds the visible source selections, installed capability set and destination/consent state shown at creation

Creation authorizes the bounded local run record and the requested local output generation, not arbitrary business writes or cloud transmission. Existing consent plus per-source destination grants govern which selected files or web excerpts can be sent to a model. A browser-open grant does not authorize uploading its screenshot to a model.

### Run record and tables

Use additive tables; do not replace tasks, routines, jobs or assistant proposals.

| Table | Required columns / invariants |
| --- | --- |
| `agent_runs` | `id`, owner, goal/title, state, state_reason, version, plan_revision, control_generation, created/updated timestamps, optional parent conversation/task IDs, authorization grant reference, budget JSON, usage counters, lease/run token, last_event_seq; bounded required-outcome manifest |
| `agent_steps` | run ID, stable step ID, plan revision, ordinal, label, kind, capability ID, dependency IDs, state, expected-input digest, required/optional, acceptance kind, linked proposal/job/artifact IDs, safe result code; unique run/revision/step |
| `agent_attempts` | attempt ID, run/step/generation, operation key, canonical argument hash, phase, start/end, provider/tool identity, numeric usage, bounded observation reference/result digest, error code; unique operation key |
| `agent_events` | monotonic sequence, run ID/version, time, event kind and content-free references; created transactionally with every transition; resumable UI cursor |
| `agent_run_inputs` | user clarifications/steering revisions and selected source refs, author, previous version and scope digest; never model authority; bounded retained text |
| `agent_effects` (browser adapter dependency) | Immutable typed browser intent, exact target/environment/observation/content digest, approval/version/expiry, dispatch generation, outcome and cleanup state. Existing local proposals/jobs keep their current tables |
| `agent_deliveries` | run ID, result version, destination `owner_in_app`, state; unique run/result/destination. Client claim/ack is repeat-safe, no outside communication |

Source/artifact storage is a separate service. Observation bodies can live in bounded source snapshots referenced by attempts, not be copied into event logs or operation receipts. Store compact decision summaries and executable state, **not hidden reasoning traces**. Content-free metadata still needs capacity limits; a cap must fail visibly rather than silently discard unknown effects.

### PlanDraft and decisions

`PlanDraft` contains at most 12 steps. Each step has `id`, `label`, `kind` (`read|compose|propose|verify`), known `capability_id`, prior-step dependencies, `required`, and a **code-owned acceptance kind**. Reject unknown IDs, cycles, duplicate step IDs, unsupported capabilities and excessive fan-out before saving a plan.

A plan is an inspectable approach, not blanket execution approval. The first ready safe read may run once the run scope is accepted; consequential effects still stop at their exact existing review boundary.

`RunDecision` is a discriminated union:

- `read(step_id, capability_id, typed_arguments)`
- `compose(step_id, artifact_format, structured_content, source_refs)`
- `propose(step_id, capability_id, typed_arguments)`
- `ask(step_id, question, reason_code)`
- `finish(summary, claimed_outcome_refs)`

Decisions cannot contain a confirmation, approval token, shell command, executor registration, arbitrary path, grant update, scheduler mutation or a success flag accepted as evidence. Every ID/version used for a mutation must match a recorded observation or a new current read. Bindings resolve only explicitly supported typed fields; no `eval`, templates with code, arbitrary JSONPath or model-authored predicates.

`finish` invokes the deterministic outcome verifier. It does not set success itself. The provider adapter is injected for testing; a scripted planner is never selectable as a genuine model in production UI.

### First typed capability set

- `source_read(source_id, start_line, max_lines)` with recorded coverage and at most 12 KiB returned text; selected-source grant enforced
- `table_compute(source_id, operation, columns, filters)` for code-owned select/filter/count/sum/min/max/group-count operations over validated CSV/JSON rows; no formulas, Python, SQL or expression language; decimal/unit handling explicit
- `task_query_selected`, `task_details_selected`, `calendar_query_selected` projected from existing services, **filtered before provider transmission** to the selected IDs/range/fields. Broad business consent does not expand a narrower run grant
- `capabilities_read` lists only configured, admitted runtime capabilities, not every registered future adapter
- `artifact_compose` accepts supported format/structured rows and real source references; byte generation/validation stays deterministic even when prose is model-authored
- `task_create_draft`, `task_change_draft`, `calendar_create_draft`, `calendar_change_draft`, and existing `computer_job_draft` only through the scoped effect-linking path; their results are not confirmations
- `public_source_read` and the exact browser/app workflow are advertised only after their separate adapter admission succeeds. Search remains absent until an actual search adapter is configured

A missing capability creates an explicit block or a proposed smaller scope for owner review; it does not trigger an unapproved provider switch or substitute a fabricated read result.

### Source / observation envelope

`{source_id, kind, selected_scope_id, observed_at, source_version_or_etag, content_sha256, locator, bounded_content_ref, untrusted: true, truncated, retrieval_status}`.

A document citation is `{source_id, source_revision, section_or_line_range}` resolved by the server. A web citation also stores the validated final URL and retrieval time. A reference proving that a source exists does not prove the model’s claim follows from it; label semantic review separately. Do not fabricate unavailable pages, quietly treat truncated data as complete, or let instructions in a source alter run authority.

## 6. State machines and completion semantics

### Run states

`queued → planning → running → waiting_input|waiting_review|waiting_effect|blocked|paused → running → verifying → succeeded|partial|failed`

From any nonterminal state, owner cancellation enters `cancelling`; it reaches `cancelled` only after dispatch has stopped and all in-flight child effects are classified. `control_generation` increases on pause, cancel, steering, takeover and authorization change, fencing late results.

- `blocked` has a typed reason: missing adapter, source unavailable, context revoked, budget exhausted, expired review, stale observation, uncertain provider request or unresolved effect
- `waiting_review` names the exact existing proposal/job; it does not call `confirm` itself
- `waiting_effect` observes an approved job or confirmed local application mutation; no busy LLM polling
- `paused` retains progress but dispatches nothing; closing a tab alone does not pause the server run
- `partial` lists completed and unmet outcomes, used only after an explicit user choice to finish with omissions or a terminal failure that leaves useful artifacts
- `succeeded` requires all required acceptance checks. Run completion never marks the linked personal task completed automatically

### Step states

`pending → ready → running → completed` with explicit `waiting_input`, `waiting_review`, `waiting_effect`, `unknown`, `failed`, `skipped` and `superseded` branches. Required steps cannot be silently skipped. `unknown` effect outcomes block dependent steps. Plan revisions retain old step/history references instead of overwriting the past.

### Three separate kinds of evidence

1. **Transport/execution:** a tool returned or bytes were written
2. **Structural verification:** independent readback matches exact IDs, versions, hash, rows and expected artifact MIME/shape
3. **Task-quality review:** claims, comparison and recommendation are accurate/useful

A Markdown file can be verified as saved while its analysis remains model-authored and unreviewed. A proposed schedule can be structurally valid while not approved. The UI/result JSON must retain these distinctions.

## 7. Worker algorithm and recovery

Add `AgentRunService.advance_one()` to its own low-frequency lifespan worker. It claims at most one ready transition using SQLite compare-and-set plus a persisted lease token. Start with one active run transition at a time and one browser/computer lease, independent from immediate physical stop and ordinary chat. Never hold a SQLite write transaction or personal-context lock over network/GUI work.

Each advance does one bounded operation:

1. Atomically claim run/step, reserve budget, persist generation, canonical arguments/digest and attempt state before dispatch
2. Resolve current authorization, source/capability identity, owner privacy and exact provider destination; gather a bounded evidence projection
3. Perform one read, one model decision, one local composition, or prepare/link one existing proposal/job outside the transaction
4. Check the same generation, live authorization and relevant source versions after returning; discard stale model text, cancel undelivered drafts, never hide already committed effects
5. Atomically record the accepted observation/result, state transition and event/outbox item; release lease
6. Next advance uses persisted state, not the previous Python stack or a browser tab

Use stable idempotency keys derived from run ID + plan revision + step ID + action revision. A network timeout never generates a new operation key. Store only request hashes/content-free receipt references in generic operation logs; otherwise deleted run content could survive in caches.

### Supervised browser/process boundary

A browser/desktop action cannot run as an unkillable `asyncio.to_thread` call in the FastAPI worker. Use a separately owned process with an explicit command/result channel, run/step/generation identifiers, deadline, cancellation message and bounded shutdown grace. Persist only opaque session/environment references. The supervisor closes contexts and the browser, then terminates only its owned process group if necessary; never kill a user browser or a process selected by model arguments. Cleanup failure blocks admission of another action on that environment. Browser process disappearance is not proof an earlier action failed.

The existing computer job’s 60-second approval deadline and synchronous single-effect executor are not a browser workflow scheduler. Reuse its exact approval/unknown-effect principles, but place browser execution claims in a separate adapter-specific effect record with a reviewed bounded duration, current observation version and cleanup receipt. Do not silently expand old note-job approval semantics.

### Existing effect linkage

- Draft through `AssistantService.tool` with explicit principal/provider context and a stable step operation key; record its proposal ID before advancing
- After the owner confirms, resolve the existing durable confirmation operation (`assistant-confirm/<proposal_id>`) and independently reread the saved record/version; if linking crashed, recover by the same operation key rather than creating another draft
- Prepare a computer job through `JobService.prepare`, link its ID, wait for the existing owner approval, then observe `JobService.detail`
- Reconciliation calls only the existing read-only verification path. A dispatched unknown write never gets re-executed because the run resumed
- Proposal expiration is a visible review block. Regenerate a new draft only after current-source reread and explicit continuation; old approval cannot authorize changed content
- Do not nest `Store.operation` transactions around service calls. Either add transaction-aware internal helpers or use the existing durable operation receipt as the recovery bridge, with tests at every crash boundary

### Recovery table

| Interruption point | Restart action |
| --- | --- |
| Before attempt dispatch marker | Reclaim only after lease expiry/current-generation check; safe operation has not started |
| Read request in flight | Mark interrupted; an explicitly bounded read-only retry may occur once under the same grant; record new observation and attempt |
| Model request in flight | Mark `provider_outcome_unknown`; no automatic paid replay. Owner Continue permits a fresh budgeted attempt; old late output is fenced |
| Local artifact reservation/file publish in flight | Reconcile DB reservation and exact generated file/hash; adopt matching bytes, reject mismatch, never overwrite by blind retry |
| Draft/job created, parent link missing | Recover its stable operation receipt/reference; link the same child, no duplicate effect |
| Owner confirmation happened, parent not notified | Read durable confirmation receipt and current record; continue exactly once |
| External action dispatched, receipt missing | Child remains unknown; only independent readback can resolve it. No click/POST replay |
| Browser session lost | Mark session stale, reattach only the same authorized environment, re-observe; do not restore authority or replay clicks from a transcript |
| Source/privacy/provider destination changed | Invalidate affected context and unapproved drafts; pause/block for fresh scope/replan. Already sent bytes cannot be recalled |
| Process shutdown / stale worker later returns | Increment/invalidate generation and lease. Late responses cannot advance run or report success; committed child effects remain discoverable |

The existing single-runtime deployment remains a requirement. Leases protect recovery and accidental concurrent advances, not a claim of supported multi-host distributed execution.

## 8. Pause, cancel, steering and human takeover

- **Pause:** stop dispatching new work immediately, cancel undelivered drafts, request child-job pause/cancel only where supported, wait for in-flight uncertainty to be classified. A running write may have completed
- **Cancel:** same dispatch fence, cancel queued/review children, record partial artifacts and effects, no rollback or automatic deletion. Do not cancel unrelated runs/routines
- **Steer:** `expected_version` + user instruction. Increment plan revision/generation; keep completed evidence, invalidate affected pending steps/drafts, show changed plan and any expanded scope for review. Never quietly replace a queued job’s approved intent
- **Take over:** pause the runner and release input control to the owner for the exact browser/application session. Record an opaque handoff reference and last observation; never log credentials. Resume only after the owner returns control and a fresh observation verifies environment/target/state
- **Resume:** requires a current signed-in owner, current sources and consent, unresolved-effect review, and remaining budget. It is not permission to enlarge the goal, destination, target app or cost

A cancelled run can be inspected and cloned into a new explicitly scoped run, but should not be silently resurrected. An unknown child effect remains inspectable even after the parent is cancelled.

## 9. Authorization, privacy and source handling

Introduce a bounded run authorization record: owner, originating session hash reference (never the raw cookie), expiry, source selections, capability IDs, target environment/app/origins, provider destination IDs and control generation. The runner resolves this grant through a dedicated policy function before every boundary; it must not manufacture `{'kind':'owner'}` as a shortcut around a revoked session.

For v1, closing the page keeps the existing session/grant valid; explicit sign-out, session expiry, private-hide or consent revocation pauses the run. Continuing after sign-out would require a distinct durable background authorization design, not accidental reuse of an owner-shaped dictionary.

Retained run goals/results are private by default. The start UI explicitly explains that persistent work stores the goal, selected source references, decisions and artifacts. Chat-history retention remains separate. Paired/device projections show only safe run state and block indicators unless a separate projection contract is implemented. Hidden/offline/stale UI masks cached goals, observations, drafts and artifact previews.

The current `share_business_context` covers task/calendar/job projections, not arbitrary files or screenshots. Add per-run/per-source provider transmission grants for new files, fetched excerpts and screenshots. Consent UI identifies data categories, exact provider destination and purpose; local file selection alone is not permission to upload it. A grant cannot override protected credential fields or operator-level access limits.

On memory/source removal, omit the removed content from new model contexts and invalidate derived unapproved proposals. Previously generated artifacts remain a separate inspectable retained output until the owner deletes them; do not promise that forgetting a memory rewrites old files. Run deletion/retention must scrub duplicate goal/observation caches while preserving minimal effect references needed to avoid replay. Unknown effects are never automatically purged. SQLite deletion is not forensic erasure, and no provider recall is claimed.

## 10. Artifacts and selected-file input contract

This is the first useful shared service, independent of the planner. Suggested `ArtifactService` operations:

- `prepare(run_id, step_id, format, display_name, content_or_structured_rows, provenance, operation_id)` → immutable reserved ID and canonical byte/hash manifest
- `publish(reservation)` → atomic no-overwrite publish followed by independent safe file readback; result `verified|unknown|failed`
- `reconcile(artifact_id)` → read-only exact hash/size/format check
- `list`, `metadata`, `read`, `download` → owner/private authorization each time; bounded cursor paging

Suggested routes: `GET /api/artifacts`, `GET /api/artifacts/{id}`, `GET /api/artifacts/{id}/content`, `GET /api/artifacts/{id}/download`; server-controlled creation via run steps or explicit owner API. No path parameter ever represents a filesystem path. Model creation is bounded by the accepted run’s requested output types/count, while business effects still require their own review.

Manifest: `{id, run_id, step_id, format, mime, byte_count, sha256, created_at, version, provenance:[source_id,revision,range], authorship: model|deterministic|owner, verification: byte_readback|unverified, supersedes_id?}`. Filenames are generated IDs with fixed extensions; a display name is sanitized metadata only. Revisions create new IDs. Reports cite source IDs that resolve to actual selected snapshots, not strings invented by a model.

Filesystem: private application-owned artifact root, no-follow/open-at checks, regular-file/link-count checks, exclusive creation, bounded writes, flush/fsync, no clobbering. Reserve metadata before disk work; atomically publish only within the trusted root; on crash reconcile exact bytes rather than repeating a write. The SQLite/file boundary is not falsely described as one atomic transaction. Orphan cleanup handles only verified test-owned/reserved temporary objects, never unknown published effects.

Initial output ceilings: 256 KiB per Markdown/TXT/CSV/JSON artifact; four artifacts and 1 MiB per run; UTF-8 only; max 1,000 CSV rows/40 columns and bounded JSON depth. Start with plain-text previews; downloads use attachment disposition, `nosniff` and no executable HTML. CSV writer quotes correctly and prevents spreadsheet formula execution for string cells beginning with `=`, `+`, `-`, `@`, tab or CR; document any escaping. Structured numeric cells can preserve actual numbers. Markdown preview must not render raw HTML, fetch remote images or execute links automatically.

For input files, add an owner-controlled source-ingestion endpoint that streams to a size-limited private store and returns an opaque source ID. Initial input formats: TXT/Markdown/CSV/JSON only; stream-limit 1 MiB/file and 4 MiB/run, validate encoding, maximum rows/depth, reject archives, symlinks and executable formats. A parser reading the whole table does not mean the model saw the whole document; record chunk coverage and disclose omissions. Never ask the model to enumerate a home directory. Selected existing artifacts can become inputs via immutable source refs without re-upload or copying secrets into logs.

Output existence/hash validation does not establish report accuracy. Quality checks include required sections/columns, each citation resolving to an existing observed source, numeric totals recomputed from parsed data, and an explicit list of unavailable/truncated inputs. Semantic claims remain marked model-authored until reviewed.

## 11. Real browser/application adapter contract

Do not widen `JobInput` to a free-form URL, selector or JavaScript payload. Keep a code-owned capability registry, with separate read/observe and effect methods:

`capabilities()`, `open_authorized_scope(grant)`, `observe(session_ref)`, `prepare_effect(typed_intent)`, `execute_once(intent, checkpoint)`, `verify(intent, observation)`, `request_takeover(session_ref)`, `close_owned_session()`.

Each receipt binds adapter/version, environment ID, application/origin, session generation, observation version, action digest and observed outcome. Screenshots and document text are untrusted observations, never approval. A model can suggest an action; the adapter resolves it against the exact allowed application/element state and fails closed if the target changed. No arbitrary JavaScript execution exposed as a universal tool.

For a public-reference workflow, start from owner-selected HTTPS URLs and exact allowed origins, no logged-in profile, cookies, downloads or form submission. A safe fetch/browser adapter must enforce private-network/loopback/link-local/metadata exclusion, DNS and redirect revalidation, byte/time/request limits and no secret-bearing URL/query use. The existing loopback demo adapter is a **separate explicitly local scope**, not an exception available to generic public fetching. If these boundaries cannot be enforced by a fetch implementation, use an isolated browser/network policy or leave that capability unavailable.

For application edits, start with one chosen real app and two exact actions whose results can be independently read: for example create a named task/calendar draft, approve the exact content, save, then reread the actual record ID/fields. A click completing without an independent result is `unverified`, not success. For GUI-only targets, the acceptance evidence and uncertainty threshold must be specified by that adapter; screenshots alone do not guarantee persistence.

LCU source review is now pinned to `146fe73fe08bf034756b91903269f6806eac2290`. Its `createCuaClient` forwards a locally supplied CUA runtime’s `js`/`js_reset` descriptors, original elicitations and text/image results; it is not a stable typed desktop-action API. Session/turn identity and explicit turn-end/reset/close cleanup are required. FYP must own the durable run and narrowly map reviewed operations; it must never expose generic JavaScript to the planner. [Pinned LCU adapter contract](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/docs/ADAPTERS.md)

On Linux, native per-app approval is absent; the desktop worker has broad UI authority, and a successful doctor exit does not prove a working sandbox. Treat missing/unknown confinement as unavailable, not a reason to disable it. Installation, actual runtime signatures/versions, application isolation and source trust are separate admission gates. The “Pi” framework adapter is not Raspberry Pi validation. No LCU runtime has been installed or exercised in this work, and no user-computer access is granted by this design. [Pinned LCU installation guidance](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/docs/INSTALLATION.md)

The executor researcher recommends an FYP-owned typed Playwright Python adapter first, instead of stock LCU JavaScript or an unrestricted browser MCP surface. A candidate authentic path is: read one approved official page, operate the existing StackEdit editor through its actual UI, create a source brief and export Markdown, then independently parse/hash the export. Exact selectors, dependency origins, no-login behavior, disabled service-worker compatibility and export behavior remain acceptance gates. Do not write the final file directly and call that an editor workflow. [StackEdit](https://stackedit.io/), [upstream export guide](https://github.com/benweet/stackedit/blob/master/src/data/welcomeFile.md)

The already-recorded cloud browser launch is blocked by the environment’s sandbox restriction. Installed Playwright/Chromium binaries are not proof of availability; do not retry with insecure flags or bypass the restriction. Cloud source/protocol tests can proceed; the existing authorized isolated Mac task must run the **FYP-owned adapter** for real-browser acceptance. Its developer QA browser is not evidence that FYP itself controls a browser. Playwright’s sandbox must be explicitly enabled and verified; a launch option is not a whole-process egress boundary. [Playwright launch options](https://playwright.dev/python/docs/api/class-browsertype#browser-type-launch)

## 12. Budgets, scheduling and progress delivery

Proposed first-run defaults/ceilings:

| Resource | Default ceiling / behavior |
| --- | --- |
| Plan | 12 steps; three plan revisions before explicit continuation |
| Model | 8 calls/run, 2,000 output tokens/call, bounded 32-KiB projected context; operator ceilings may be lower |
| Reads | 24 calls/run, per-tool response limit; one read-only retry; identical input/result loop detected |
| Effects | Three reviewed effects/run, one outstanding review at a time; no automatic dispatched-write retry |
| Time | 10 minutes active work, 24-hour run deadline; wait-for-owner time does not silently consume active compute budget |
| Browser | One owned session, 20 navigation/interaction actions; no background tabs outside scope |
| Results | Four artifacts, 1 MiB total; bounded observations/events and max 100 retained runs initially |

Reserve counters transactionally **before** each model/tool dispatch. Timeouts and unknown model results still consume an attempt. Actual numeric provider usage is recorded when supplied; missing usage remains unknown. Tokens/call ceilings are not a currency guarantee: a money limit needs an explicit, versioned price model and configured operator budget. Never claim “free” or a verified cost from synthetic tests. A loop or budget stop records a readable blocked reason and remaining useful artifacts.

No model call occurs merely because a 0.5/1-second worker wakes. Ready step state, owner input, review outcome or child-job completion permits an advance. Deferred checks carry a specific predicate and `next_check_at`; only supported sources can be watched. General recurring agent work is not added to routines in v1.

Persist progress events and a single in-app completion/block notification keyed by run/result version. Polling with a sequence cursor is sufficient initially and avoids a new distributed bus; SSE may later expose the same durable log. Claim/ack prevents repeated toasts on reconnect. Report meaningful changes, not every token or timer tick. Do not send email/Slack/phone notifications from this slice.

## 13. API and UI integration

Owner endpoints under `/api/agent/runs`:

- `POST /` create with idempotent operation ID
- `GET /` bounded cursor list; `GET /{id}` projected goal/plan/results; `GET /{id}/events?after=<sequence>` durable activity
- `POST /{id}/actions` with `expected_version` and `pause|resume|cancel|steer|takeover|finish_partial`
- `POST /{id}/input` bound to the outstanding question/version
- Existing proposal/job review endpoints remain authoritative; run responses contain links/IDs, never “approve all” model tools
- `POST /{id}/notifications/ack` acknowledges only the owner-in-app result version

Add an “Ask me to work on this” entry beside ordinary chat rather than turning every message into a background job. Show the result requested, sources, provider destination and scope, current step, explicit block, completed evidence, next owner action, elapsed active time and budget. Chat stays usable while the worker waits on a model or app.

A detail panel shows a concise plan and timestamped action/result summaries; it does not expose private reasoning traces. Artifacts display type, authorship, verified bytes/hash and source list, with download and “revise this result” continuing the same run lineage. Never label a generated report “fact-checked” just because its checksum matched.

Reuse `ResponseFence`, `usePrivateMutation`, stale/hidden masking and draft guards. Repeated clicks, unknown responses, navigation, modal dismissal and newer selections cannot attach a response to another run. Cancellation has an independent control path even while approval/write recovery is pending. A stale page cannot approve an effect. DeviceApp initially receives a safe status/attention projection only; A1 and its artwork are unchanged.

## 14. Implementation seams and ownership proposal

| Change | Location / boundary |
| --- | --- |
| Run schema, state machine and recovery | New `backend/desk/agent_runs.py`, `agent_run_schemas.py`, tests |
| Planner protocol and bounded context | New `backend/desk/agent_planner.py`; reuse `TextAssistant.generate` through an explicit injected interface, do not extend the three-turn chat loop into a background stack |
| Typed read registry / source references | New `backend/desk/agent_tools.py`, source service; reuse existing business methods behind grants/consent |
| Immutable file outputs | New `backend/desk/artifacts.py`, artifact routes/tests; independent owner to parallelize |
| Runtime integration | Small `Runtime.__init__`, `tick`/run worker health and `app.py` lifespan/router additions; parent integrates to avoid races |
| Effect linking | Adapter around `AssistantService.tool/decide` and `JobService.prepare/detail/reconcile`; avoid changing original effect semantics |
| UI | New `workspace/agent/RunPanel`, `RunDetail`, `ArtifactList` and typed API helpers; minimal AssistantPanel entry |
| Browser/LCU | Separate worker owns reviewed adapter and platform experiment; registry only advertises proven available capabilities |
| Tests/docs | New run/serialization/recovery/privacy tests, browser acceptance script, this contract and a precise implemented-scope doc |

Suggested delivery order is **contracts + artifact/source service**, then **run worker + scripted planner + existing app reads/reviewed effects**, then **real browser/application adapter**, then **actual configured-model evaluation**. These may be independently reviewed but the overall journey remains incomplete until the relevant dependencies have passed. Adding a scheduler or an artifact icon alone does not satisfy the slice.

## 15. Acceptance tasks and failure matrix

### A. Useful local work package, actual storage

Seed a known project with selected Markdown/TXT notes, a requirements CSV, five real application tasks and explicit calendar entries. Request a gap/action report. Run a deterministic builder and a scripted planner separately; each must gather sources, retain provenance, produce actual Markdown plus CSV files, and show missing facts instead of inventing them. Independently reopen the files, parse CSV, recompute counts and check every cited source/range. Prepare two requested follow-up edits, confirm one and reject one in the owner UI; exactly one application effect exists after independent reread. The result identifies the rejected outcome, rather than claiming all work succeeded.

### B. Real public-page/browser addition

Once the adapter is available, collect at least two authorized real public reference pages and one controlled hostile/injection page in an isolated browser. Record actual final URLs, timestamps and readable excerpts; reconcile a missing/changed page honestly. Produce a source-linked comparison and downloaded artifacts. No login, private network, arbitrary download, injected new destination or hidden screenshot upload occurs. This proves real browsing/data movement, not live model reasoning.

### C. Real application edit and takeover

On the exact allowed app/environment, prepare two bounded edits from observed fields. Pause for owner review; save only the approved edit and independently reread it. Interrupt after dispatch but before receipt; restart and reconcile without a second effect. Take over, modify the target manually, then resume; fresh observation must invalidate the stale action and require replanning/review. A demo-record API can exercise the contract but does not substitute for this target-app acceptance.

### D. Genuine model evaluation, conditional

When an approved configured provider/budget exists, repeat at least three varied goals (report/comparison, work planning with reviewed edits, revise an existing artifact). Record model/provider/version, selected-data consent, calls, latency, available numeric usage, actual outputs and human-scored correctness/completion. Include an ambiguous request and an unavailable capability. Until then, publish protocol/unit/real-storage results only and explicitly mark natural-language multi-step success untested.

### Mandatory adversarial/recovery cases

- Restart after every persisted transition; no duplicate draft/job/artifact or repeated POST/click
- Two workers/double submit/stale generation; one claim and one linked effect
- Cancel/pause during slow model call, read, draft creation, owner confirmation and dispatched write
- Unknown write stays unknown until independent evidence; “cancelled” never means rolled back
- Malformed/cyclic plan, invented tool/ID/version, arbitrary path/URL/code, out-of-scope app and prompt-injected instructions rejected
- Source changed after observation, private mode on/off, consent/provider change and sign-out fence late results and new dispatch
- Budget exhausted, provider timeout/malformed JSON, infinite repeated decisions, inaccessible source and unavailable adapter produce inspectable blocks
- Crash between artifact reservation/write/fsync/publish/DB update; symlink/hardlink/path attacks, MIME mismatch, oversized input/output, CSV formula and Markdown HTML injection
- Required outcome missing, rejected edit, stale source, empty artifact or mismatched readback cannot become success
- Offline/reload/Back/Cancel/repeated input/newer run selection masks stale private data and preserves the right unsent draft
- Unrelated routine, task, A1, device stop and existing unknown-job recovery remain unchanged

## 16. Decisions to settle before code and remaining evidence

Engineering recommendations to approve as a batch, not new user product decisions:

1. Accept the source-bound research/work-package outcome and state/receipt model; do not narrow it to a single demo write
2. Split artifact/source service, orchestration and browser adapter ownership; parent alone integrates Runtime/app/common UI seams
3. Use one bounded worker and no automatic paid retry. Default natural-language planner unavailable until configured; deterministic mode is labeled
4. Pin run authorization to the current owner session in v1; broader unattended runs after sign-out need explicit policy and revocation semantics
5. Keep local artifact output within the started run’s requested types/count; existing business/target-app effects retain exact review, and new data transmission needs its own scope
6. Choose the first real browser/application target from the LCU/platform findings. Do not claim support for an untested OS or reinstall privileged software merely because a repository documents it
7. Confirm output/source retention UI and initial caps before accepting long-running personal data; no automatic destructive cleanup of uncertain effects

Unresolved external conditions: verified adapter API/runtime/install route and OS isolation; configured provider access and paid evaluation allowance; any authenticated target app and screenshot/data-sharing permission; actual browser/UI usability and later device/hardware validation. None blocks deterministic protocol, durability, consent, file, record and failure-path testing now.

## 17. Verification of this design document

This is a design deliverable only. Current source was inspected independently; the earlier full reading gate is inherited, and relevant changed project contracts were reread. No frozen application source, runtime data, school document or artwork was edited for this design. Implementation and actual-model/browser claims remain explicitly conditional. The parent owns root handoff/decision/work-log updates and publication coordination.
