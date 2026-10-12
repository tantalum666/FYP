# Group 2 | Durable agent work packages

Updated 12 October 2026. This document describes the implemented local run service. It is distinct from the larger [design and acceptance roadmap](../../planning/2026-10-12/durable-agent-run-design.md). Test evidence is synthetic-model protocol coverage and actual local SQLite/file operations, not a live-model quality assessment or general computer-use demonstration.

## What a run actually does

An owner selects immutable uploaded text/Markdown/CSV/JSON source snapshots and/or particular task/calendar records, enters a goal, reviews the selection and explicitly starts retained work. The run persists its goal, selected scope, plan, observations, progress, model-call reservations, review links and outcome requirements. Chat remains a separate interaction.

Two clearly different modes are available:

- **Deterministic evidence compilation:** local typed acquisition, CSV row counts and wholly numeric column sums (bounded magnitude and decimal scale), source excerpts, an evidence register, actual Markdown and CSV files, optional explicitly supplied task/calendar draft requests, owner review, independent saved-row verification. It does not interpret arbitrary natural-language goals or claim that a report proves the larger task finished
- **Configured bounded model coordination:** the existing approved Qwen/Gemini text transport makes a persisted decision at each reasoning boundary. Decisions can plan, read a selected item or bounded batch, request further source lines, ask the owner a question, compose a cited report, propose permitted local task/calendar changes, or request final verification. Actual observations, owner answers and reviewed effect results accumulate. After review, the model receives the independently observed result on its next decision

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

Model mode additionally binds an approved exact text-provider destination. Selected local source transmission requires a separate explicit per-run flag. Selected task/calendar context also requires the existing destination-bound business-context consent. Context is composed only from selected observations and owner answers, never all stored tasks, memory or unrelated conversation history.

Privacy changes, sign-out, session expiry, missing/corrupt sources and provider destination changes block further work. A new valid owner session can explicitly resume an eligible run; switching providers cannot silently reuse the previous provider grant. Already transmitted bytes cannot be recalled. A late result cannot publish after a pause, cancel, shutdown or generation change.

Run-origin drafts are also filtered out of the legacy proposal list for paired controllers/displays and require a real visible owner session for both confirmation and cancellation. A pre-dispatch intent table joins the child operation receipt, so this guard covers the crash window before the parent run links the proposal. Unrelated legacy controller drafts retain their previous behavior.

Private-hidden list responses contain only metadata; detail and scope are denied. Valid owners can still cancel or pause while private information is hidden, with a metadata-only response. Paired controllers/displays and device agents do not receive this owner-only API.

Retention is explicit at start and separate from optional chat-history retention. Runs, selected-source snapshots, generated artifacts and dedupe receipts are retained locally. This batch does not provide run deletion or forensic erasure. Do not upload credentials. Source/artifact retention and file protections are specified in [sources and artifacts](sources-and-artifacts.md).

## Persistence, recovery and controls

One host/API process owns the database and one bounded worker advances a run step at a time. SQLite writes reserve model attempts before network dispatch. A returned structured decision is committed with its receipt before its consequences are applied. Restart can apply that saved decision without paying for a replacement call.

The shared text transport bounds raw JSON response bytes to 128 KiB, requests identity encoding and rejects compressed bodies, checks a 30-second monotonic deadline after headers and on each raw chunk, and uses five-second HTTPX phase inactivity timeouts. Under normal socket reads, an in-progress body read may overrun the nominal deadline by one read timeout. Header parsing and blocking OS calls are not forcibly interrupted; this is not an OS hard deadline or a worker-process kill guarantee. Cancellation fences publication even if an old synchronous request has not returned.

An interrupted provider request becomes `RUN_PROVIDER_OUTCOME_UNKNOWN`; ordinary resume is rejected. Explicit `retry_model` acknowledges a new provider attempt may cost money. The attempt budget is not reset by resume, steering or failure. No LLM call is made while polling a pending review.

A typed draft's immutable canonical typed-intent hash and server-generated operation key are saved before dispatch. The key stays stable across recovery. Recovered receipts must match the reserved tool/arguments and the actual saved proposal/request; a colliding unrelated legacy draft is neither adopted, classified as run-origin nor cancelled. If the child draft exists but its parent link was lost, recovery/cancellation finds the existing operation receipt and links or cancels that same draft. It never asks the model to invent a replacement draft after uncertain dispatch. Actual mutation confirmation stays in the existing application review flow.

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
- Model mode admits at most 10 selected items total and 8 reasoning attempts for the entire run; read batches avoid one paid call per file
- 32 acquired observations; model source chunks at most 1,800 UTF-8 bytes on complete lines, with explicit line coverage; deterministic parser reads at most the source service's 1 MiB/file
- At most 30,000 bytes of serialized model context; exceeding it blocks rather than silently dropping evidence. Prompt/schema overhead is additional; this is not an exact tokenizer or monetary budget
- Three proposal effects, four artifacts/1 MiB per run, two report revisions, four owner answers, 64 retained control receipts per run (final cancellation remains available), 100 retained runs, 24-hour deadline, and the shorter valid-owner-session boundary
- Source/artifact services enforce their own file/type/byte/count caps. Limits count failed/uncertain reservations where appropriate

A selected source can exceed the model's context/read budget. The service must then report partial coverage or a clear block; it cannot imply the entire file was reasoned about. CSV numeric sums do not infer units, weighted quantities or the meaning of a column.

## Integration and acceptance boundaries

Runtime constructs source/artifact services and `AgentRunService` after text AI configuration, then the app mounts owner-only routes. A worker calls `advance_one()` through thread offload. Lifespan calls `shutdown()` before cancelling workers. No changes to the A1 companion layer, DeviceApp layout, school files, hardware control or existing calendar/task semantics are required.

The optional browser service is separately admitted and reviewed. This run service has no model-facing browser write tool in this batch. The development assistant's browser access is not an application capability. General desktop control, arbitrary web search, external messages, authenticated-account writes, recurring agent runs, process takeover, rich PDF/HTML output and parallel child agents remain later work.

Automated tests exercise actual source files, immutable output files, SQLite proposals and records, source-range accounting, restart, uncertain paid calls, generation races, privacy and required-outcome negatives. Scripted `AgentDecision` responses demonstrate protocol/orchestration behavior only. Genuine model usefulness, natural-language generalization, paid usage and browser/application desktop outcomes require separately authorized live acceptance evidence.
