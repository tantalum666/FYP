# FYP agent baseline audit

Audit time: 2026-10-12 12:15 UTC. Read-only source audit; no source changes, real provider calls, user-computer access, hardware actions, merge or push were performed by this audit worker.

## Verified repository baseline

- Repository: `tantalum666/FYP`, private repository accessible through the authorized GitHub connector
- `main`: `ccfac48ce8c68e6f9c8796911bbe5f35728d7807`
- [PR #4](https://github.com/tantalum666/FYP/pull/4): open, unmerged, mergeable at audit time; branch `codex/full-body-3d-avatar`
- Exact PR head: `50e174f50a4130b3c666f836f666f6aa4cde4b32`, 23 commits ahead of main and zero behind
- Recursive Git-tree comparison finds no changed backend or backend-test blobs between this head and main. The note-job and voice-dispatch foundation is already on main; current PR adds the independent VRM/A1 frontend/art/document work
- Exact-head GitHub check-runs returned zero checks; no `.github` workflow appears in the full tree
- Materialization is possible through pinned GitHub text retrieval. Workspace preparation owns blob verification and the fuller snapshot at `/workspace/shared/fyp-agent-20261012`. Historical assets and live private runtime data are outside this audit copy; absence in a partial snapshot must never be committed as deletion

## Authority and preservation

Current project contract uses a React/TypeScript frontend, FastAPI modular backend and SQLite on a single owner-controlled host. Personal-agent computer/software operation and fixed-camera posture feedback are both required. Do not replace either with a purely conversational demo.

Preserve selected A1 as one whole unchanged 2D illustration. Segmented SVG, local deformation, 2.5D depth and the recent A1 3D derivative were rejected. The older licensed pixiv VRM is a separate feature. Preserve original art, prompts, license/provenance, school originals and Logsheet No. 2, and existing runtime data. Default A1 outfit and voice/provider are not finally selected. Local document completion is not school submission. PR #4 has not been merged.

AGENTS requires full project-authored Markdown reading and an exact ledger before implementation. This reader completed 17 assigned Markdown files, 1,311 lines and 164,187 bytes, including initial truncated material reread to EOF. See `reading-architecture-audit.json`; other workers own the remaining repository reading. This report does not claim full-repository reading.

## Actual implementation, verified from source

### Durable tasks and scheduling

`backend/desk/tasks.py` persists tasks, evidence and followups, with optimistic versions and shared operation IDs. `TaskService.schedule()` computes an explicit check or interval capped by a future deadline. `tick()` inserts one followup per task-version and clears the next check, preventing unanswered prompt spam. User actions resolve old followups. Completing a task is explicitly user-confirmed, distinct from a calendar block or successful file job.

`app.py:52-76` launches four process-local async loops that offload synchronous actions: rules each second, public-data poll each 10 seconds, optional task advice each 30 seconds, jobs each 0.5 seconds. Exceptions leave a safe `retrying_after_error` health state and the loop continues. There is no durable general-purpose schedule, external event subscription, outbox or distributed lease; this is deliberately a single API worker prototype.

### Model/tools and approvals

`assistant.py:45` defines typed allowlisted tools. `AssistantService.tool():195` dispatches reads or prepares calendar/task/output/job drafts. Model tools do not include confirmation. `decide():329` is a separately authenticated application operation with idempotent confirmation. Existing calendar/task/output confirmations may come from an authenticated paired control surface; computer approval is owner-only.

`text_ai.py` supports optional Qwen/Gemini text reasoning, JSON validation, at most three model/tool iterations, and at most one mutation draft. Background advice is default-off and limited to 20 attempted requests per UTC day, including failures. It checks current task version before publishing. Provider responses/prompts are not logged wholesale; usage persists numeric values only. Tool-returned text is described as untrusted data in the system instructions; actual action containment comes from typed handlers and approval boundaries, not that prompt alone.

### Jobs and independent verification

`jobs.py:27` limits `JobInput.action` to `save_note` and `verify_note`. `JobService` persists intent, exact hash, state/version, deadline, approved identity, run token, result and event history. Approvals bind complete intent hash plus version and recheck linked task versions. Queued jobs expire after 60 seconds; review expires after five minutes. Restart invalidates started run tokens and records `unknown`, rather than replaying writes. Only unstarted valid approved jobs can resume. Cancellation before dispatch is side-effect-free; cancellation after a real write does not falsely claim rollback. Reconciliation is read-only.

`computer.py:56` exposes a small executor protocol. `LocalNotesExecutor` writes only new generated-ID `.txt` files under the runtime's `computer-notes` directory using exclusive creation and no-follow flags, then fsyncs. Verification independently opens a regular non-hardlinked bounded file and compares bytes/hash. `jobs.py:293` additionally checks exact artifact name, byte length, SHA256, executor identity and scope. Unknown writes are never automatically retried.

This is a real local file operation, but it is not browser, third-party app, remote PC, LCU or generic computer control. The verifier currently has note-specific assumptions, so adding an arbitrary GUI adapter without changing the typed evidence contract would be architecturally wrong.

### Memory and conversation continuity

There is no personal-memory entity, memory management API, provenance/retention controls or explicit memory-per-provider consent. Current durable knowledge is calendar, task/progress, job and deduplication state.

`assistant.py:25` has `message`, `language`, `task_id` only. `text_ai.py:213` assembles a bounded task/calendar context; `assistant_replies` at line 110 is keyed by operation ID and is retry caching, not a conversation model. `frontend/src/workspace/AssistantPanel.tsx:61` stores only the last reply in React state. Voice transcript state is transient. Closing/reopening the panel therefore does not restore a continuous thread, and a follow-up utterance has no persisted conversation context beyond the selected task.

### Voice

`voice.py` adapts Qwen Audio and Gemini Live; input is PCM16/16kHz and output PCM/24kHz. Tickets are single-use and 30 seconds, sessions singleton and bounded to 600 seconds / 45 seconds idle. Revocation is checked during sessions. No automatic paid reconnect/session resumption exists. Audio and transcripts are not persisted by this backend.

`tool_dispatch.py` decouples tools from realtime receive: two normal concurrent calls, eight pending, 32 retained ordinary calls plus reserved Stop slot, results queue of 64, duplicate signatures, interruption generation fence and late-draft discard. Delivered-state marking requires the original result object, preserving the previously fixed duplicate-rejection regression. Approved jobs outlive a voice disconnect.

No current Grok/OpenAI adapter, server-side speech-session continuation, persistent conversation handoff or Python/cross-device amplitude bridge is implemented. Browsers meter actual output RMS for the independent avatar; that is amplitude mouth opening, not phoneme recognition. Provider naturalness, Cantonese, AEC and costs remain unmeasured.

### Network and identity

`app.py` validates Host and configured HTTPS origin, requires `X-Desk-Request` for API mutations, uses strict HttpOnly cookies, has a restrictive frontend CSP and default local binding. Owner, paired device and local-agent credentials are separate. Google integration is read-only OAuth with PKCE/state and encrypted server-side token storage. The prototype is not multi-tenant.

Text endpoints have provider restrictions and disable HTTP redirects, but voice endpoint validation is currently weaker: it accepts any `wss` host/path/port. `VoiceService.run()` then supplies provider credential headers to that accepted destination. This is a configuration-hardening gap, not a claim of remote exploitation. Synthetic/no-network class-level checks reproduced:
- Gemini `wss://unapproved.example.invalid/anything` accepted
- Qwen `wss://127.0.0.1:9443/private` accepted
- Voice malformed `:invalid` port accepted
- Text malformed allowed-host port raises `ValueError`, rather than returning unconfigured

Evidence: `baseline-provider-validation.json`. New providers should not multiply this inconsistency. Tests currently use `fixture.invalid` plus injected transport, so tighten production policy while preserving explicit test injection rather than allowing arbitrary production hosts.

### Lifecycle, data and frontend

`JobService.prepare()` stops at 1,000 lifetime jobs; `listing()` returns at most 200 with unresolved first. No archive/pagination/export exists. `ExchangeService.backup():365` includes calendar, settings and task bundle only. `TaskService.export():386` includes each task's latest 20 evidence rows. Jobs, note artifacts, conversation and future memory are not part of this business backup. SQLite raw backup may contain authentication data and is not an ordinary share artifact.

The UI already has owner review, unknown-result recovery, fresh-state approval gating and independent cancel for jobs. New management panels should reuse `api.ts` operation recovery, `DraftGuard`, workspace refresh and bilingual messaging rather than bypass these contracts. Assistant and TaskPanel are large but do not justify a wholesale rewrite.

## Verification status

Source/test code read shows substantial regression coverage for approval, unknown writes, crash recovery, cancellation windows, stale task versions, forged receipt fields, symlink/hardlink protection, privacy projection, background quotas, voice interruption and backpressure. Baseline test execution is owned by the workspace worker; this audit does not count those as freshly passed until its logs arrive.

Recorded historical results: October 9 integration 149 backend / 15 frontend; subsequent avatar work 22 frontend / 26 targeted backend; October 12 A1 work 28 frontend. These have different scopes and must not be summed or described as one fresh suite. No remote CI result exists for the audited head. Browser/device/provider evaluation claims remain separate from unit tests.

## Suggested bounded implementation milestones

### M0: Provider policy and reproducible baseline

One shared provider endpoint validator for text and voice; parsed exact scheme/host/path rules, no userinfo/query/fragment/unapproved port, robust invalid-URL handling, and deliberate redirect/proxy policy. Preserve official supported region/workspace endpoints. Add tests that rejected targets make no key-bearing request. Reproduce backend suite, frontend tests/typecheck/build, lint and integrity checks at the pinned baseline before changes. Optionally add deterministic CI only for synthetic/offline tests, with no real provider secrets or runtime assets altered.

### M1: Inspectable personal memory and meaningful conversation continuity

Add a small `MemoryService` with explicit user-confirmed facts/preferences/notes, source/time, version, status/expiry and user inspection/edit/revocation. Distinguish display visibility from permission to send memory to a model/provider. Add memory query + draft tools; no model self-approval. Use one bounded, privacy-filtered context builder shared by text and voice. Bilingual MemoryPanel and safe owner operations should be testable without any paid model.

Separately introduce bounded conversation/thread IDs and persisted user/assistant text with explicit retention behavior, link task/job/evidence IDs, support retrieval/deletion and exclude raw voice capture by default. Do not quietly turn every utterance into a durable personal fact. Conversation cache, memory and execution history are distinct data products. Tests: restart continuity, isolation, version conflicts, expiry/revocation, hidden/private context, non-confirmed drafts, provider payload limits and backup behavior.

### M2: One actual application workflow in the cloud sandbox

Choose a self-owned isolated test application and a fixed low-risk create/save operation. Adapt `JobInput`, `JobService.capabilities/prepare/_verify` and `ComputerExecutor` through a typed registry, keeping existing note behavior and tests. Scope the adapter to exact origin and owned test objects; do not add generic URL/path/JS/shell tools. Review immutable target/content, execute through a real browser or explicit application API, then independently verify app storage/state. Bind receipt to request hash, executor and target; read-only reconciliation after lost receipts. Bound execution and cancellation with executor-owned process/session cleanup; a cancelled Python `to_thread` is not a kill guarantee.

Evidence must include actual app state before/after, saved Unicode data, independent readback, blocked unauthorized target/navigation, duplicate request, cancellation before/after dispatch, crash/lost receipt and restart without duplicate writes. Call this cloud test-app execution only; it does not establish control of the user's Mac or an arbitrary external app.

### M3: Practical lifecycle/export

Add terminal-only archival and paginated history; unknown/active jobs must remain visible and cannot be hidden as success. Extend versioned business export with selected memory/conversation/job/note content and explicit limits. Restoring must never reconstitute credentials, approvals, run tokens or executable queued work; use imported-history status. Preserve existing data during migrations. Tests should prove capacity recovery, pagination, no execution on restore and absence of secrets.

### M4: Provider/voice upgrades after contracts stabilize

Grok/OpenAI or newer adapters should share provider policy, usage limits, typed tools, unified identity/context and cancellation contracts. Public availability does not authorize paid calls or credential setup. Synthetic protocol tests can be implemented now; real AEC, wake, naturalness, costs, session-resumption and target hardware claims require explicit service/device conditions. Do not add every provider before one end-to-end application task works.

General event streams, outboxes and external monitoring should be introduced only against a defined consumer/delivery scope. Current durable per-task checks already address basic scheduling. Polling every second is not the same as model polling; replacing it with unnecessary distributed infrastructure adds risk without completing the missing user journey.
