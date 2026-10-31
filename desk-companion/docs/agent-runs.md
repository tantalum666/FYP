# Group 2 | Durable agent work packages

31 October 2026 integration: read [current compatibility and migration rules](pr5-integration.md) first. Dated October 12–13 acceptance statements below remain historical; this integration preserves Alice/current Omni and the current task/job/permission core.
Updated 13 October 2026. This document describes the implemented local run service. It is distinct from the larger [design and acceptance roadmap](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/planning/2026-10-12/durable-agent-run-design.md). Test evidence is synthetic-model protocol coverage and actual local SQLite/file operations, not a live-model quality assessment or general computer-use demonstration.

## 31 October: current application tools

Opted-in Work now connects to the existing office executor. [Current application contract](application-work.md) describes selected input hashes, task/version binding, Ask first/Full access, parent-run fences, exact recovery and immutable file versions. Real Chromium/Calc/Writer/PDF with offline decisions and web/phone actions are covered in [current QA](../../output/qa/2026-10-31-personal-agent-cross-app/verification.md). This addition does not turn the older public-browser tests below into live-model acceptance.

## What a run actually does

An owner selects immutable uploaded text/Markdown/CSV/JSON source snapshots, particular task/calendar records, fixed public browser sources or registered public/synthetic connector tools, enters a goal, reviews the selection and explicitly starts retained work. Optional personal continuity has its own explicit selection and retention acknowledgment. The run persists its goal, selected scope, plan, observations, progress, model-call reservations, review links and outcome requirements. Chat remains a separate interaction.

Two clearly different modes are available:

- **Deterministic evidence compilation:** local typed acquisition, CSV row counts and wholly numeric column sums (bounded magnitude and decimal scale), source excerpts, an evidence register, actual Markdown and CSV files, optional explicitly supplied task/calendar draft requests, owner review, independent saved-row verification. It does not interpret arbitrary natural-language goals or claim that a report proves the larger task finished
- **Configured bounded model coordination:** the existing approved Qwen/Gemini text transport makes a persisted decision at each reasoning boundary. Decisions can plan, read a selected item or bounded batch, request further source lines, select a registered executor tool, ask the owner a question, compose a cited report, propose permitted local task/calendar changes, or request final verification. Actual observations, owner answers and reviewed effect results accumulate. After review, the model receives the independently observed result on its next decision

Neither mode has an approval tool. Selecting a file does not authorize a provider to receive it. A model cannot add source IDs, choose an arbitrary host path, invent a browser capability, change grants, invoke shell code, or mark a run successful by returning a success flag.

The artifact writer creates real immutable files and independently reads their bytes. Source citations are structured snapshot ID/revision/line ranges plus hashes. Source labels and prose are untrusted; a citation does not fact-check the associated sentence. The CSV evidence register is deterministically encoded even when report prose comes from a model.

## Required outcomes and completion language

A code-owned manifest fixes Markdown plus CSV output, all selected evidence, complete declared source coverage and optional owner-entered section titles. Explicit mutation requests retain their required/optional status.

Final verification checks:

1. Both current-revision artifacts exist, report verified byte readback, and remain inspectable. Output coverage is bound to the observations captured at composition; reading a missing source later does not retroactively repair an old report
2. Every selected record was acquired. Every selected source has complete contiguous line coverage: the deterministic local parser's coverage and the model's actual transmitted ranges are distinct. Partial application excerpts in model mode are also disclosed as unmet evidence
3. Required section titles exist. This is structural validation, not a semantic score
4. Every required requested mutation has a linked review result and independent saved-row verification. Task fields/version and note evidence, calendar creation fields/count/version, and calendar change/exception state are checked. A missing, rejected, expired, changed or unknown required effect is not achieved

Missing evidence or required changes yields `partial`, with `unmet_requirements` and an explicit reason. Missing output files block completion. `succeeded` means **these structural outcomes are verified; prose quality and the owner's broader goal remain unassessed**. Files already written remain available when a later requirement fails. No run state automatically completes a personal task.

## Authority and privacy

Creation requires a real owner session cookie, not an owner-shaped dictionary. Only the session's existing SHA-256 token hash is stored; no raw cookie, provider secret or new bearer authority is persisted. Before each dispatch and late-result publication, the service checks the actual session record/expiry, private-visibility setting, control generation, privacy revision, source integrity and 24-hour run deadline.

Model mode additionally binds an approved exact text-provider destination. Selected local source transmission requires a separate explicit per-run flag. Selected task/calendar context also requires the existing destination-bound business-context consent. Context is composed only from selected observations, explicitly selected eligible personal continuity and owner answers, never all stored tasks, memory or unrelated conversation history.

Privacy changes, sign-out, session expiry, missing/corrupt sources and provider destination changes block further work. A new valid owner session can explicitly resume an eligible run; switching providers cannot silently reuse the previous provider grant. Already transmitted bytes cannot be recalled. A late result cannot publish after a pause, cancel, shutdown or generation change.

Run-origin drafts are also filtered out of the legacy proposal list for paired controllers/displays and require a real visible owner session for both confirmation and cancellation. A pre-dispatch intent table joins the child operation receipt, so this guard covers the crash window before the parent run links the proposal. Unrelated legacy controller drafts retain their previous behavior.

Private-hidden list responses contain only metadata; detail and scope are denied. The owner UI now keeps that metadata list and its Pause/Cancel controls available while hidden; it does not load private run details. Valid owners can still cancel or pause while private information is hidden, with a metadata-only response. Paired controllers/displays and device agents do not receive this owner-only API.

Retention is explicit at start and separate from optional chat-history retention. Runs, selected-source snapshots, generated artifacts and dedupe receipts are retained locally. This batch does not provide run deletion or forensic erasure. Do not upload credentials. Source/artifact retention and file protections are specified in [sources and artifacts](sources-and-artifacts.md).

## Persistence, recovery and controls

One host/API process owns the database and one bounded worker advances a run step at a time. SQLite writes reserve model attempts before network dispatch. A returned structured decision is committed with its receipt before its consequences are applied. Restart can apply that saved decision without paying for a replacement call.

The shared text transport bounds raw JSON response bytes to 128 KiB, requests identity encoding and rejects compressed bodies, checks a 30-second monotonic deadline after headers and on each raw chunk, and uses five-second HTTPX phase inactivity timeouts. Under normal socket reads, an in-progress body read may overrun the nominal deadline by one read timeout. Header parsing and blocking OS calls are not forcibly interrupted; this is not an OS hard deadline or a worker-process kill guarantee. Cancellation fences publication even if an old synchronous request has not returned.

Local context assembly and the final dispatch fence reject known pre-network failures as `dispatch_refused`, preserving the original privacy/control error. A second fence runs as an HTTPX request hook after serialization and before transport dispatch, checks the actual request URL, and holds no privacy lock across network I/O. These refused reservations still consume the bounded attempt count; a local usage reservation may remain, and no provider billing claim is inferred. In-flight transmitted bytes cannot be recalled.

An interrupted provider request becomes `RUN_PROVIDER_OUTCOME_UNKNOWN`; ordinary resume is rejected. Explicit `retry_model` acknowledges a new provider attempt may cost money. The attempt budget is not reset by resume, steering or failure. No LLM call is made while polling a pending review.

A typed draft's immutable canonical typed-intent hash and server-generated operation key are saved before dispatch. The key stays stable across recovery. Recovered receipts must match the reserved tool/arguments and the actual saved proposal/request; a colliding unrelated legacy draft is neither adopted, classified as run-origin nor cancelled. If the child draft exists but its parent link was lost, recovery/cancellation finds the existing operation receipt and links or cancels that same draft. It never asks the model to invent a replacement draft after uncertain dispatch. Actual mutation confirmation stays in the existing application review flow. The canonical task/calendar confirmation request is checked both at the actual service transaction and during independent outcome verification; an unrelated preexisting receipt cannot satisfy a reviewed mutation. Public API operation IDs cannot use the internal `assistant-confirm/` namespace.

Artifact publication uses stable run/revision/index keys and the immutable writer's reconciliation rules. A missing response does not authorize blind file replacement. Cancellation between two artifact writes fences the second dispatch; the already-created artifact remains listed. Cancellation does not roll back a confirmed calendar/task effect.

Pause conservatively cancels outstanding unconfirmed drafts. Resume continues acquired work, but cancelled required changes are reported as unmet. Steering changes the goal under the same selected-source/provider scope, retains immutable prior artifact versions, reuses immutable source observations, refreshes application acquisitions, and never replays confirmed effects. At most two report revisions are admitted. Changes to source scope or destination require a new run.

Shutdown fences all active generations before asynchronous worker cancellation. In-flight provider outcomes remain unknown, not silently replayable. Graceful restart leaves work paused for explicit resumption. An abrupt restart recovers after the 60-second dispatch lease expires. This is single-host SQLite coordination, not a distributed multi-host lease guarantee.

## API and bounds

`agent_run_routes(runtime, owner, operation_id)` mounts `/api/agent-runs`:

- `GET /scope`: authoritative selection options, exact approved provider destinations, privacy/scope fingerprint and limits
- `GET /`: retained run list, private metadata projection when hidden
- `POST /`: strict `RunCreate`, including `retain: true`, selected IDs and current `scope_revision`; operation IDs deduplicate request retries
- `GET /{id}`: run, actual step records, content-free event references, linked proposal reviews and actual artifacts
- `POST /{id}/actions`: version-checked pause, resume, cancel, steer, answer and explicit provider retry

Creation defaults to deterministic mode. `mutation_requests` are schema-validated typed requests, not arbitrary JSON execution. Model-created proposals require `allow_mutation_proposals`; existing-record changes must name a selected and actually observed record/version. The initial UI may omit the advanced typed mutation editor while showing model-proposed reviews.

Ceilings:

- 4,000-character goal; at most 12 sources, 10 tasks, 10 calendar records; aggregate selected source bytes at most 4 MiB
- Model mode admits at most 10 selected evidence items total (including public browser selections and application input files). Owner-selected reasoning attempt budget defaults to 8 and is bounded 1–24; executor tool reservations default to 8 and are bounded 1–16. These are call/reservation caps, not currency budgets; read batches avoid one paid call per file
- 32 acquired observations; model source chunks at most 1,800 UTF-8 bytes on complete lines, with explicit line coverage; deterministic parser reads at most the source service's 1 MiB/file
- At most 30,000 bytes of serialized model context; exceeding it blocks rather than silently dropping evidence. Prompt/schema overhead is additional; this is not an exact tokenizer or monetary budget
- Three non-application proposal effects plus explicitly admitted application jobs (default6, maximum8); four report artifacts/1 MiB per run, two report revisions, four owner answers, 64 retained control receipts per run (final cancellation remains available), 100 retained runs, 24-hour deadline, and the shorter valid-owner-session boundary
- Source/artifact services enforce their own file/type/byte/count caps. Limits count failed/uncertain reservations where appropriate

A selected source can exceed the model's context/read budget. The service must then report partial coverage or a clear block; it cannot imply the entire file was reasoned about. CSV numeric sums do not infer units, weighted quantities or the meaning of a column.

## Integration and acceptance boundaries

Runtime constructs source/artifact services and `AgentRunService` after text AI configuration, then the app mounts owner-only routes. A worker calls `advance_one()` through thread offload. Lifespan calls `shutdown()` before cancelling workers. No changes to the current Alice companion layer, DeviceApp layout, school files, hardware control or existing calendar/task semantics are required.

The optional browser service now joins the same planner through the typed registry below. Preparation remains an exact owner review, never a model-approved external write. The development assistant's browser access is not an application capability. General desktop control, arbitrary web search, authenticated-account writes, recurring agent runs, process takeover, rich PDF/HTML output and parallel child agents remain later work. The optional MCP bridge extends explicitly registered anonymous public/synthetic tools; it does not establish authenticated external-account or general application acceptance.

Automated tests exercise actual source files, immutable output files, SQLite proposals and records, source-range accounting, restart, uncertain paid calls, generation races, privacy and required-outcome negatives. Scripted `AgentDecision` responses demonstrate protocol/orchestration behavior only. Genuine model usefulness, natural-language generalization, paid usage and browser/application desktop outcomes require separately authorized live acceptance evidence.


## Registered executor bridge

`AgentDecision(action="tool", tool_call={tool, arguments, required})` selects only an entry in the code-owned registry. Each adapter supplies a strict argument schema and separate availability, validation, dispatch, read-only recovery, verification and cancellation methods. Runtime-owned extensions use `runtime.agent_tool_adapters`; neither the model nor HTTP input can register a callback, schema or grant. The model sees the exact selected schemas and accumulated typed results. There is no approve tool.

A canonical tool/argument digest fixes the operation key before dispatch. The run persists the reservation, exact arguments, child reference, result and whether that effect is required. The child service independently checks its own operation receipt against the actual immutable request. Repeated identical intent reuses its child even after an unknown or rejected outcome; it never creates a replacement effect to guess at completion. Required status cannot be downgraded on reuse. Cancellation recovers matching unlinked children without adopting or cancelling a colliding unrelated receipt. The three-effect ceiling remains shared by non-application tools and task/calendar drafts. Explicit application Work has a separate1–8 job cap (default6), within the shared tool-attempt limit.

`tool_results` contain `tool`, `arguments`, `operation_key`, `reference_id`, `state` and bounded `result`; linked external effects have `kind="tool"`. A state of `observed` means data was returned, not that the requested effect was independently verified. `verified` requires the adapter's separate outcome proof. Required unverified effects yield `partial`; model prose never changes this. Tool observations have typed bounded excerpt, original response digest, declared coverage and untrusted semantics, with no fabricated local source-file provenance.

### Public browser tools

An owner explicitly selects `browser_source_ids` from the current fixed catalog and sets `browser_public_only: true`. Browser-only model runs are supported. Admission requires the existing experimental browser capability to be ready; readiness is not live acceptance. The available tools are:

- `browser_public_observe({source_id})`: uses FYP's BrowserService to observe one selected public excerpt. The returned observation ID, hash, URL, heading, acquisition time and excerpt enter the run's evidence. This never claims whole-page coverage
- `browser_public_brief({observation_id})`: accepts only an observation already acquired by this run. The exact title and note are code-owned constants/catalog text; the remaining content comes from the verified public observation. It accepts no model-authored title, note, body, URL, path, goal, source text, task data, memory or answer. Private selected evidence may coexist with this browser grant because it has no outbound payload path

Preparing a brief creates the existing immutable BrowserService owner review. `detail.browser_jobs` contains those full reviews; `run.browser_job_ids` retains their linkage. Existing `/api/browser/jobs/{id}/approve` still requires the exact version/hash and a fresh explicit public-only acknowledgment. The run waits without model polling. After the browser worker returns, the run reconciles its original receipt, independently reopens actual exported bytes and verifies digest, byte count and confirmed cleanup before accepting `verified`. Verified bytes with unconfirmed cleanup remain `unknown`; a missing or changed export never satisfies the required effect.

Public observation passes a private server-side checkpoint into the existing supervised worker fence. Pause, cancel, owner expiry, hide/show or other generation/privacy changes prevent further stages and late observation publication. Graceful shutdown also cancels pending/queued child effects before leaving the parent paused. An interrupted read is recovered as failed/unknown without another browser read; an interrupted destination write is never replayed. Running cancellation does not undo already-exported bytes or prove process cleanup.

This is a planner-connected fixed public-documentation → StackEdit adapter, not general model-authored browsing, arbitrary desktop control or a proven network sandbox. Live-model decisions and real browser operation remain untested in this cloud slice; tests use explicitly labelled scripted decisions/fake-browser protocol while exercising real SQLite and immutable-file storage.

### Public/synthetic MCP tools

The owner selects finite `connector_tool_ids` from `scope.connectors`; operator configuration supplies the exact HTTPS endpoint, tool schema, descriptor/grant hashes and declared read/write effect. Selection pins the connector scope revision. `share_connector_results_with_provider: true` separately permits returned public tool content to reach the exact selected approved model destination. Selected tool IDs alone do not grant data transmission or approval.

Every connector call, including a declared read, prepares an exact owner review of arguments, endpoint and grant. The model's public-only field is never approval. This initial public/synthetic slice rejects combining connector grants with private uploaded sources, selected task/calendar records or personal memory/history. Model output is not trusted to declassify private material. Exact owner review is still required for freeform arguments derived from the goal or answers. Provider, session, visibility and connector-grant changes fence work.

MCP response text and structured content become bounded untrusted observations. A remote `saved` claim is not independent proof: an observed required write remains unverified and produces `partial`, even when the server response says success. General private-data connectors, credential/OAuth provisioning and authenticated external-account acceptance remain outside this implementation.

### Selected personal continuity and publication fences

`personal_context` is optional and explicit: selected memory IDs and/or one retained conversation, with a separate `retain_derived_context: true` acknowledgment. See [personal-context run binding](agent-personal-context.md). The run stores content-free references/hashes, projects only eligible selected text immediately before provider dispatch, and never treats memory/history as source evidence, approval or tool scope. Derived plans/reports may retain selected facts under that acknowledgment; forgetting a memory does not erase already-retained artifacts.

Generation, owner/session, private visibility, consent revision and personal binding are checked at model-return/checkpoint commits. Artifact publication has a server-only callback at reservation and immediately before final linking under a short SQLite write transaction; forgetting/cancelling between a preflight check and file publication cannot expose a new final artifact. On a known pre-link denial, the writer best-effort removes only the temporary file created by that invocation. Unknown/crash-prior files or reservations may remain; final retained artifacts are never deleted and this is not forensic erasure. Run-origin task/calendar confirmation is also rechecked within the actual application operation transaction, closing the gap between owner review and local mutation. Unrelated legacy drafts retain their existing behavior.

### Owner interface

The Work panel exposes selected application tasks/input files and exact job cards, public catalog selection, optional personal-context selection, configured connector choices, explicit sharing/retention acknowledgments, and bounded model/tool attempt caps. A chat handoff prefills the requested goal and selects model mode only when advertised available; it does not automatically select data, start a run or grant an effect. Linked browser/connector reviews use their existing exact-review panels, and hidden mode retains only metadata plus stop controls. UI checks and current limitations are recorded in the [interface verification](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/output/qa/2026-10-13-agent-work-interface/verification.md).

A transient run-list/scope/detail refresh failure retains only the same privacy/session epoch and selected-run snapshot so unsent editors and their original in-memory retry operation IDs are not silently unmounted. The UI labels that snapshot stale and disables new work, run controls, retries, linked review handoffs and source uploads until a successful refresh. An upload rechecks freshness after local file reading and before dispatch. Authorization/privacy failures, missing resources, unexpected errors, selection/epoch changes and workspace disconnection clear private views instead of preserving them. A late access denial from a parallel read still clears a snapshot after an earlier transient failure. This behavior is covered by deterministic hook-state tests and source wiring checks; actual mounted-browser interruption acceptance remains separate.
