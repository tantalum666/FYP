> **HISTORICAL RESEARCH — recovered 30 October 2026.** Original source: [PR #5](https://github.com/tantalum666/FYP/pull/5), commit `11dc2b84cebe6e8250b28ca4442fc91f0dfec676`. This restores research only, not the old implementation. Dated provider/API details, tests, next steps and instructions below are historical evidence; use the [current research entry](../personal-agent-research-index.md) and current product/handoff for decisions. References to old code/supporting files point to the pinned historical commit.

# Muse capability gap: from a safe kernel to a useful personal agent

Research and comparison date: **12 October 2026, UTC**. This supplements [the first Muse report](muse.md). It records a second pass through official product, developer, cookbook and public SDK material in response to the user's concern that Muse can do much more than memory and reminders. No frozen application source was changed, no vendor account was opened, and no paid model, real account connector, microphone or desktop-control test was performed for this report.

## 1. Direct answer and correction of scope

**The concern is justified. The first checkpoint is a useful safety and persistence foundation, not an implementation of Muse's breadth.** The first report did cover its cloud computer, connectors, concurrent work, artifacts and permission separation. But the implementation plan selected a narrow subset, and the research did not yet connect every important product capability to a concrete implementation and a real user task. “We researched Muse” and “we built a Muse-like personal agent” are different claims. Only the first, with the omissions below, was supportable.

The important next step is an agent that can accept a goal, gather authorized information across sources, produce a usable work product, perform a requested bounded application action, verify it, and continue or report a precise blocker after interruption. More memory controls or additional fixed reminder types alone will not reach that outcome.

This comparison uses the **12 October first software checkpoint**, described in [the implementation record](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/planning/2026-10-12/personal-agent-implementation.md) and its [verification record](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/output/qa/2026-10-12-agent-kernel/checkpoint-verification.md). Later work must update this comparison with its actual commit and receipts. The reported 361 backend and 50 frontend tests establish that checkpoint's software behavior, not live model quality or complete agent capability. Actual browser acceptance was still pending in the checkpoint record.

## 2. Identify the right Muse and separate the public surfaces

The relevant product is **Meta's Muse personal AI agent**. Meta's announcement, dated 8 September 2026, explicitly identifies its dedicated cloud computer, connected applications, continued background work, WhatsApp access and approval-gated consequential actions. The page also displays a 30 September date. This identity is not inferred from the word “Muse” or the domain alone. Older video-hosting documentation and unrelated products with that name are not evidence for this personal agent. [Meta launch announcement](https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/)

| Surface | Verified public evidence | What an FYP can actually reuse |
| --- | --- | --- |
| Consumer Muse | Product/design/security descriptions; a connector submission overview | Product behavior and published architectural principles. No public callable consumer-agent embedding contract was verified |
| Meta Model API | Model inference, function tools, search, files, computer-action protocol, asynchronous responses, transcription | Specific model services behind our own agent runtime, executor, authorization and storage |
| Muse Code | Local coding-agent host, workflows, skills, hooks, MCP, goals, retained sessions | A possible optional harness on a supported host, with separate installation, credentials and capability checks |
| Muse Code SDK | Public client packages and session/approval/event protocol; host binary is separate | An adapter to that local harness. It does not grant consumer Muse accounts, cloud VMs or connectors |
| Muse Glimmer / Muse Image / Muse Voice Transcribe | Distinct model families in the developer catalog | Optional inference, image generation or ASR components. None is a complete personal assistant |

The Model API guide also documents integration with the Claude Agent SDK and Codex app-server: those frameworks own their execution loop, while Muse Spark supplies inference. A compatible base URL is not a replacement for application permissions, task state or outcome checking. The Codex example even needs an explicit catalog because the model-list shapes differ. [Agent-framework integration](https://dev.meta.ai/docs/agent-frameworks)

The public connector page describes submission, review, testing and directory listing. It does not expose a complete consumer connector schema or consumer-agent control endpoint. The submission/login boundary was not crossed. This is **“no public contract verified in this research,” not “no API can exist.”** [Muse Connector Platform](https://muse.ai/platform)

## 3. What makes the consumer product broader

The official design article describes a continuing main conversation, side chats, simultaneous tasks, goals and progress, selective proactive updates, editable memory, documents and interactive artifacts. It also separates chat from explicit approval controls. These are product descriptions, not evidence that the underlying consumer orchestration is available as a downloadable SDK. [How We Designed Muse, September 2026](https://introducing.muse.ai/)

The security article supplies unusually concrete public architecture: a restricted per-user agent cell, privileged host services, scoped grants, credential surrogates, connector and network mediation, and a separate browser broker. During human takeover or credential entry, the browser agent pauses. The article describes launch-time operational access and future confidential VMs; it does not justify claiming that current consumer infrastructure is cryptographically inaccessible to Meta. These remain vendor claims rather than an independent audit. [How We Built Safety Into Muse, 8 September 2026](https://research.meta.ai/blog/security-and-safety-for-ai-agents-our-approach-with-muse)

For this project, the most important lesson is **breadth through a common task runtime and carefully mediated tools**, rather than an ever larger list of disconnected buttons. The implementation proposed below is our design, not a reconstruction of private prompts or proprietary source.

## 4. Capability → current implementation → missing work → acceptance

Status meanings: **Partial** means real relevant code exists but the broader task is missing; **Missing** means the checkpoint has no end-to-end implementation; **Unverified** means code or a vendor claim is not backed by the required live test. The acceptance column describes tests to perform, not tests already passed.

| Capability and public basis | Current FYP checkpoint | Concrete next implementation | Real task acceptance |
| --- | --- | --- | --- |
| **One continuing assistant across activities.** Consumer design includes main and side conversations | **Partial:** optional saved text threads, owner identity and tasks; temporary chat remains default | Separate conversation from durable work: a conversation can reference several `run_id`s; navigation and voice ending do not terminate work. Show selected thread, active runs and current evidence | Start a research task, ask an unrelated question, reopen the first task from another authorized surface and recover its real progress without mixing the two histories |
| **Goals, plans and completion criteria.** [Goal-tracking cookbook](https://dev.meta.ai/docs/cookbook/goal-tracking) | **Partial:** user-maintained tasks/steps and at most three text model/tool rounds; no general persisted executable plan | Add versioned goal, acceptance criteria, typed plan steps/dependencies, current blocker and evidence requirements. A model can propose/revise a plan; only a verifier closes it | “Read these documents and prepare a cited comparison.” The run cannot succeed until files exist, citations resolve and required sections are present, even if the model says it is done |
| **Parallel and dependent work.** [Muse Code workflows](https://dev.meta.ai/docs/muse-code/workflows) | **Missing:** fixed routines and task steps are not delegated agent workflows | Persist parent/child runs, limited fan-out, dependency edges, result references, join/synthesis and per-child budgets. Initially allow independent read-only research children; serialize conflicting writers | Research two independent topics concurrently, make synthesis depend on both, fail one source and show a precise partial result. No fabricated successful child or empty synthesis |
| **Work continuing in the background and across failure.** [Audit/resume cookbook](https://dev.meta.ai/docs/cookbook/audit-agent-sessions) | **Partial:** approved jobs and routines survive UI closure; uncertain job writes have read-only reconciliation. No general long-running agent recovery | Durable worker ownership/leases, append-only run events, model/tool checkpoints and effect-intent records. Recover a lost worker without blindly repeating an unresolved write | Close the UI; restart the service between an actual write and its receipt; resume the same run, independently inspect the target and prove only one write occurred |
| **Cross-app connectors and authorization.** Consumer platform/security; [Muse Code extensions](https://dev.meta.ai/docs/muse-code/extending) | **Partial:** Google Calendar read connector code; local task/calendar functions; no broad authenticated connector registry or verified live calendar connection | Connector capability registry, separate read/write scopes, account identity, references to a credential vault, expiration and revocation and live scope checks. API-first adapters before GUI fallback | With an authorized test calendar, read an event, propose a new event, approve the exact destination/time, create once and read back its provider ID. Revoke access and prove further calls fail |
| **Browser navigation and forms.** Consumer browser broker; [computer-use guide](https://dev.meta.ai/docs/computer-use) | **Missing:** no general browser driver. An HTTP demo-app executor does not operate its browser UI | Isolated browser profile/worker with origin and download policy, navigation observations, bounded actions, review before submission, human takeover and fresh-state resume | Navigate a real local test application's HTML UI, fill the requested record, stop for final approval, submit and independently verify storage. Repeat with injected page instructions and a redirect outside the allowed origin |
| **Actual desktop application operation.** [Native macOS cookbook](https://dev.meta.ai/docs/cookbook/computer-use-macos) | **Missing:** note filesystem and fixed demo API are real operations, but neither observes or controls a Mac app | Authenticated Mac companion; one selected app/window, per-action observations, normalized driver contract, permission status and local stop. No arbitrary shell by default | In an approved native test app, enter Unicode text into the intended document, save and verify it from independent state. A different foreground app, stale screenshot or changed document must stop the action |
| **Web research with source evidence.** [Search grounding](https://dev.meta.ai/docs/search-grounding) | **Missing:** no research run that fetches sources and delivers a cited result | Search/retrieve adapter with retrieval time, URL/title, source hash, excerpts/locations and coverage. Record actual searches and citation associations; tool output stays untrusted | Answer a concrete FYP research question from at least three relevant primary documents, distinguish conflicting claims and expose the exact sources used. No fabricated links or claim of a search when no search occurred |
| **Files as task inputs.** [File handling](https://dev.meta.ai/docs/file-handling) | **Missing:** saved notes/JSON backup are not an attachment ingestion and document-reading system | Explicit file selection, MIME/size validation, scoped extraction worker, page/section coverage, encrypted/private local storage as appropriate, provider-upload consent and retention cleanup | Read an authorized PDF and CSV, extract specified values with page/row provenance, flag unreadable or omitted pages and reject malicious embedded instructions |
| **Usable artifacts and deliverables.** Consumer artifacts; [slides recipe](https://dev.meta.ai/docs/cookbook/generating-slides) | **Partial only for plain notes:** no general cited document, spreadsheet or interactive artifact pipeline | Artifact registry, content hashes, format-specific renderer/validator, preview/download, provenance manifest and explicit share action. Isolate generated HTML from the authenticated UI | Produce Markdown plus CSV/JSON and a rendered report; open the outputs in their real viewer, verify tables/citations and show files rather than only a chat claim. Interactive HTML cannot access app credentials |
| **Learning and retrieving personal context.** Consumer editable memory; [Muse Code context configuration](https://dev.meta.ai/docs/muse-code/configuration) | **Partial:** owner facts/preferences/decisions, correction/forgetting and bounded thread projection. No semantic personal knowledge search or automatic evidence-linked extraction | Extend provenance, source references, conflicts, temporal validity and user-reviewed extraction. Keep memory separate from permission grants. Start with deterministic retrieval before adding an embedding service | A preference used in two tasks is inspectable and correctable; later tasks use the correction. Deleting the source or forgetting the fact prevents retrieval and cache resurrection |
| **Voice as an entry point to ongoing work.** [Muse speech-to-text surface](https://dev.meta.ai/docs/speech-to-text); consumer transport is not publicly established | **Partial / Unverified:** Qwen/Gemini voice code and consent fencing exist; real naturalness, echo and interruption behavior were not established by synthetic tests | Provider-neutral turn IDs, final-transcript routing, TTS or speech-to-speech adapter, barge-in, mic/processing indicators, cancellation semantics and task handoff. Never automatically retain voice transcript | Speak a task, correct it mid-turn, interrupt speech output, review the exact action and finish it. Repeated final events cannot duplicate actions; closing the voice session leaves the approved run visible |
| **Event-driven proactivity and delivery.** Consumer selective updates; [loop/cron constraints](https://dev.meta.ai/docs/cookbook/loop-and-cron) | **Partial:** deterministic scheduled task/calendar reviews, local explicit reveal and bounded pending results; no change subscriptions or external delivery | Authorized source watches or connector events, watermarks, meaningful-change rules, quiet hours, dedupe and a durable delivery outbox with stable IDs. Add channels separately with scoped permission | A selected document changes while the UI is closed; exactly one useful update appears after reconnect. Duplicate events, no meaningful change, revoked source access and paused watch produce no unwanted message |
| **Cancel, steer, pause and human takeover.** Workflows; [SDK queue/steer/reclaim](https://meta-models.github.io/muse-code-sdk/next/cookbook/queue-steer-and-reclaim-turns/) | **Partial:** job cancellation and routine pause/cancel; no whole-run/child orchestration or browser handover | Generation-fenced run controls; prevent new effects before asking workers to stop; cascade to descendants; show outstanding effects. Human takeover acquires exclusive control and invalidates stale planned actions | Cancel one of two concurrent tasks without stopping the other. Take over a browser, change the document, resume and require a new observation/review. Never claim cancellation undid an already completed write |
| **Permission, audit and secrets boundaries.** Consumer security; [Muse Code permissions](https://dev.meta.ai/docs/muse-code/permissions) | **Partial:** owner-only approval, exact intent/version hashes, destination-bound context consent, no model confirmation authority. No per-agent VM or comprehensive egress broker | Keep the existing deterministic gate; add capability/egress mediation, least-privilege worker credentials, sanitized event export and prompt-injection tests for every new input/tool | Malicious document text cannot send mail, reveal keys or expand scopes. A trace identifies who authorized each real effect. Raw screenshots, private text and provider secrets do not leak into ordinary logs |
| **Expandable skills and tools.** [Muse Code extensions](https://dev.meta.ai/docs/muse-code/extending) | **Partial:** hard-coded executor registry; no reviewed skill/plugin ecosystem | Versioned capability manifests, input/output schemas, resource policy and verifier contract; operator-reviewed adapters. Generated code belongs in isolated per-run workspaces, not automatic plugin installation | Add a new read-only adapter without changing core run states. An adapter with an undeclared destination/write capability is rejected. Failed optional tools do not silently acquire new access |
| **Transactions and real communications.** Consumer launch describes email/booking/shopping approval | **Missing and deliberately gated:** no email send, travel booking or purchase adapter | Represent these as explicit future capability classes with recipient, exact content/item, cost and final confirmation, rather than imply they follow from model configuration | First validate a real unsent email draft in an authorized test account. Sending or buying requires separate user authority and external receipt; a local fixture alone cannot pass live-service acceptance |

The checkpoint facts above are grounded in [personal context](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/desk-companion/docs/personal-context.md), [task tracking](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/desk-companion/docs/task-tracking.md), [computer jobs](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/desk-companion/docs/computer-jobs.md), [routines](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/desk-companion/docs/routines.md) and [provider policy](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/desk-companion/docs/provider-policy.md). The table does not count capabilities merely because their names appear in a prompt, UI button or future plan.

## 5. New developer findings that change the implementation plan

### 5.1 Real workflow orchestration exists in public Muse Code documentation

The correct path is `/docs/muse-code/workflows`, reached from the extensions navigation. It describes parallel groups, dependent stages, progress, background completion delivery and reusable JavaScript workflows. Controls include pause/resume/cancel and selected-child handling. It permits up to 1,000 child calls over a workflow lifetime, with a CPU-derived active-child limit capped at 16. Retained recovery is conditional on the workflow-enabled build and persisted records; no-session-log operation can lack durable scripts. [Workflow contract](https://dev.meta.ai/docs/muse-code/workflows)

**Our consequence:** build and test a small bounded run graph, not a 1,000-agent imitation. Start with two or three independent read workers and one deterministic artifact verifier. Concurrency limits, lifetime call limits and cost limits are separate controls. A read worker may never inherit the writer's grants just because they share a parent goal. Whether we use this harness or our own worker loop is an implementation choice; the product-level need remains the same.

### 5.2 Research and artifacts have implementable public recipes

Search grounding exposes search-call output and URL citations; full considered results are an optional additional field. Tool availability does not guarantee that the model actually searches. [Search API behavior](https://dev.meta.ai/docs/search-grounding)

The slides cookbook builds a research brief, structured outline, reveal.js HTML and a statistics JSON containing sources and usage. It is a working composition example, not a universal PPTX export endpoint. [Research-to-slides recipe](https://dev.meta.ai/docs/cookbook/generating-slides)

**Our consequence:** make evidence and artifacts first-class records. Store `source_id`, URL or local-file hash, retrieval time, covered pages/rows, excerpt location and citation links. An artifact needs its own hash, MIME type, producing run/step, source manifest and validation receipt. A final answer should link the completed files and disclose incomplete coverage. The reviewer must be able to open the artifact without trusting the model's final sentence.

### 5.3 Native Mac computer use is documented, but infrastructure is still ours

The native Mac recipe provides Swift/Python routes using macOS APIs, requiring Screen Recording/Accessibility permissions. It serializes model actions and warns that it operates on the real Mac. Its normalized coordinates differ from the native computer tool's screenshot-pixel coordinates. [macOS recipe](https://dev.meta.ai/docs/cookbook/computer-use-macos)

The Model API computer tool standardizes action requests and screenshot responses; the developer supplies the machine/browser, input driver, safety and recovery. [Computer-tool boundary](https://dev.meta.ai/docs/computer-use)

**Our consequence:** choose one explicit driver contract and test coordinate mapping, scale, window identity and stale observations. Do not mix examples from different coordinate systems. Prefer native application APIs when they provide reliable operations; use GUI actions only for tasks that need them. The Mac companion should be an authenticated, restricted capability service, not a model-accessible general shell. Real local permissions must be granted by the user before the trial.

### 5.4 Recovery needs evidence, not automatic resubmission

The audit cookbook describes an append-only effect-intent journal and distinguishes committed effects from unknown effects after a crash. Its default export contains raw local payloads; redacted export cannot erase what was already logged. [Audit and recovery recipe](https://dev.meta.ai/docs/cookbook/audit-agent-sessions)

**Our consequence:** extend the current job reconciliation pattern to the whole run. Record an intent before an external effect, then record its independent receipt. A crash in between means `outcome_unknown` and a read-only reconcile operation, not “retry until success.” Prefer minimal event payloads from the beginning; redaction at export is additional protection, not the privacy design. A resumed model must see reconciled state and current grants.

### 5.5 Background inference, local scheduling and hosted agent availability differ

The Responses API supports queued background inference, retrieval/stream retrieval and cancellation. The cancellation endpoint is limited to background responses. This does not supply our tool executor, scheduler or durable user-facing task. [Responses lifecycle](https://dev.meta.ai/docs/protocols/responses), [cancel reference](https://dev.meta.ai/docs/api-reference/responses/cancel-response)

Muse Code's loop/cron recipe requires a living process, uses session-local scheduling, expires recurring jobs after seven days and can introduce bounded jitter. It recommends another scheduler for indefinite work or work while the CLI is closed. [Loop and cron](https://dev.meta.ai/docs/cookbook/loop-and-cron)

**Our consequence:** distinguish closing a browser, stopping a worker, stopping the API service and powering off the host in the UI and tests. Our current local routines continue only while the local service runs; they are not an always-available cloud service. Choose deployment availability explicitly before promising an overnight agent.

### 5.6 Files and API compatibility require careful qualification

The Files guide supports **optional** expiry from one hour to 30 days; no expiry is only the default. It also limits PDF processing coverage, so accepting a long file does not mean every page was read. [File handling and expiration](https://dev.meta.ai/docs/file-handling)

A current documentation inconsistency remains: the Responses guide rejects `truncation: "auto"`, while the computer-use guide describes account-gated server-managed conversation/auto-truncation support. Likewise, the framework guide's broad forced-tool wording should not override the dedicated tool guide, which currently documents only `tool_choice: "auto"`. Treat these as explicit compatibility uncertainties. Use conservative stateless/replayed bounded context and application-controlled tool loops until a pinned account/model conformance test establishes otherwise. [Responses limitations](https://dev.meta.ai/docs/protocols/responses), [computer-use context management](https://dev.meta.ai/docs/computer-use), [tool-calling restrictions](https://dev.meta.ai/docs/tool-calling)

## 6. Concrete runtime and UI seams to implement

These are proposed FYP interfaces, not existing Muse endpoints or already implemented project modules. Preserve FastAPI/SQLite and one authoritative service initially; a message cluster is unnecessary for a few bounded workers.

### Durable records

- **Run:** owner, source conversation, goal, acceptance criteria, state, revision, privacy revision, approved capabilities, deadline, usage/cost ceilings, cancellation generation and final result references
- **Step:** run, dependencies, purpose, type, attempt, worker lease, tool policy, input references, output references and verifier requirement; no raw credential fields
- **Evidence:** measured source/target identity, observation time, current version/hash, provenance and any coverage limits
- **Artifact:** scoped file identifier, MIME/size/hash, source manifest, producing run, preview policy, validation status and retention setting
- **Effect intent:** exact tool, target, arguments hash, authorizer/grant, expiry, idempotency key, state and reconciliation method
- **Delivery:** run/result reference, chosen destination, stable delivery key, queued/sent/acknowledged/failed state and privacy-safe preview

Run states should separate `planning`, `running`, `waiting_input`, `waiting_approval`, `paused`, `verifying`, `succeeded`, `partial`, `failed`, `cancelled` and `outcome_unknown`. A step can finish while its parent still waits for synthesis or verification. Model completion is an event, not an acceptance decision.

### Services and adapters

1. **Planner:** produces a validated, bounded plan from authorized input references. It cannot manufacture grants, executor registration or proof of completion. Revisions explain what changed and retain fulfilled effects
2. **Worker supervisor:** acquires leases, enforces concurrency/time/token limits, emits durable progress and recovers interrupted read work. Separate total deadline and idle watchdog
3. **Tool broker:** rechecks user identity, current capability scope, provider/data consent, target version and cancellation fence immediately before every effect. Do not infer safety from tool metadata alone
4. **Source adapters:** explicit file selection, web retrieval and selected connector records. Treat their contents as data, including text that claims to be system instructions
5. **Executor adapters:** reuse current note/demo executor contracts, then add browser and Mac adapters behind the same proposal/approval/evidence lifecycle
6. **Verifier:** use deterministic validators or independent reads for concrete outcomes; retain unresolved quality checks for human review. A second model's agreement is not proof that a file was saved or mail sent
7. **Delivery worker:** publish a concise result with artifact/evidence links only after state commits. No duplicate notification on UI refresh; explicit channel permission and current privacy checks

The public Muse Code SDK remains a candidate adapter, with its host/version/licensing checks described in the first report. Direct Model API calls are another candidate. The task ledger and policy must remain outside provider-specific history so replacing a model does not destroy ongoing work. [Public SDK repository](https://github.com/meta-models/muse-code-sdk), [SDK quickstart](https://meta-models.github.io/muse-code-sdk/next/guides/quickstart/)

### User-facing decisions

- Keep conversation responsive while work runs. Display multiple runs, their actual current step, what is waiting and what can safely be stopped
- Show “needs your answer,” “needs permission,” “external effect unknown” and “verified result” as different states
- Approval must show the actual destination/account, requested change, complete relevant content and version. A general “continue” in chat cannot authorize a different or newly expanded action
- Provide plan revision, pause, cancel and continue controls. Disable obsolete approvals and fence late callbacks after hide/show, identity changes and navigation, preserving the current UI privacy work
- Human takeover must visibly own the browser/desktop. Resume only after capturing new state; reapprove if the intended target or content changed
- Artifacts need preview/download, source coverage and validation status. Generated HTML belongs on an isolated origin or tightly sandboxed frame, not the authenticated application's origin
- Memory settings, local transcript retention, provider sharing, screenshots/files and connector scopes remain separate consents. Never silently attach the whole disk or all saved chats to a run
- The existing A1 artwork, independent DeviceApp and posture workflow remain intact. Show agent state through existing restrained interaction rather than reopening rejected visual approaches

## 7. Outcome-based acceptance programme

**All journeys below are planned acceptance, not completed tests.** Synthetic/unit checks should run first, but the final evidence must include the indicated actual application, file or service. Use fictional data and isolated workspaces before requesting access to personal accounts.

### J1. A useful research deliverable

Request: “Compare three official approaches for this FYP, explain the tradeoffs and give me a report plus a comparison CSV.”

Required behavior: plan; search/fetch actual official documents; track publication/retrieval dates; identify disagreement and missing evidence; create Markdown, CSV and a rendered preview; return links. Open and inspect the files in their real viewers. Check all CSV rows, citations and mandatory sections against retrieved sources. Capture source hashes, artifact hashes, browser/viewer evidence, run events and usage. A plausible paragraph with no files fails.

### J2. Documents → plan → calendar → verified outcome

Request: “Read this selected assignment PDF and my selected calendar; propose two work sessions before the deadline.”

Required behavior: quote the deadline's page/location, disclose unread pages, resolve timezone, read only the approved calendar, identify conflicts, show exact proposed events and wait for approval. Then create and independently read back approved events from the actual authorized test account. Editing the deadline while approval is open invalidates the old plan. If credentials or a needed scope are absent, stop at an accurate proposal rather than invent a booking.

### J3. Browser operation with takeover

Request: “Create this record in the selected test app through its browser interface.”

Required behavior: use actual navigation and input, not the demo API shortcut for the action; take fresh observations at transitions; stop before final submission. The user takes over and changes a field. The agent must not execute its stale click, must reread the field, and must show a new review if necessary. After submission, verify the actual database/API state independently. Include screenshots and a target-state receipt. An injected page instruction to send private data elsewhere must fail.

### J4. A bounded native Mac task

Request: “In this approved test document, add the three reviewed bullet points and save.”

Required behavior: establish the app/window/document identity and granted OS permissions, perform real UI/API actions, observe the final state and verify saved content. Switch to another app midway, deny a permission, interrupt input and test display scaling. No off-target typing; no automatic privilege expansion; unresolved save result remains unknown. Do not generalize one-app success to all desktop software.

### J5. Two tasks, dependency failure and chat responsiveness

Start a cited research package and a separate selected-file analysis. Keep ordinary conversation available. Let one child source fail while the other succeeds. Show per-run progress and a useful partial result, allow cancellation of only the selected task and preserve finished evidence. Prove that a synthesis step does not run on a missing required dependency and that concurrent writers cannot race on the same artifact.

### J6. Restart without duplicated external effects

Terminate the worker after a real application write but before its completion receipt. Restart the service. Recover the same run/step identity and classify the effect as unknown. Only query current target state; do not repeat the write. Verify exactly one target record and a trace showing intent, interruption, reconciliation and outcome. Also test a crash before the write, after a terminal receipt and during artifact generation. These are different recovery cases.

### J7. A meaningful proactive update

Create an explicitly authorized watch over a selected local document or test connector record. Change a meaningful field while the UI is closed. On reconnect, show one update describing what changed, why it matters and the source evidence. Replay the event, make an irrelevant formatting edit, pause the watch and revoke the source scope. Test that none creates another unwanted delivery. Separately test service downtime catch-up and disclose the observed availability boundary.

### J8. Voice that joins ongoing work safely

With an authorized microphone/provider, speak a goal, revise an utterance, interrupt the assistant's speech and inspect its proposed task. Use final turn IDs rather than partial text to create intent. Duplicate/reorder final events and verify no duplicate work. End the voice session, reopen the run in text and continue. Measure end-of-speech-to-first-audio latency, interruption-to-silence latency and task-intent errors; do not substitute protocol-mock success for these measurements. Raw audio and automatic transcript retention remain off unless separately authorized.

### J9. Cross-capability privacy and authority regression

Put adversarial instructions in a retrieved page, file and calendar description. Attempt to expose another connector, send an email, install a tool and bypass approval. Change owner identity or hide private content while a worker is running; revoke provider sharing before result return. Verify blocked effects, cleared/fenced private UI and no stale result restoration after hide→show. Correct/forget a memory and ensure a later run cannot recover it from cached summaries or artifacts marked as derived context. Separately retained files/conversations need their own honest deletion semantics.

Each journey produces a receipt containing code commit, configured providers/versions, exact fictional input, authorized scope, run/step IDs, initial/final target evidence, negative-case results, latency/cost when applicable and remaining limitations. Screenshot evidence alone does not establish durable external state; a database/API receipt alone does not establish a GUI interaction occurred. Use the right evidence for the claim.

## 8. Practical implementation order

### Next outcome: research and a work package, not another settings panel

Implement the durable run/step/evidence/artifact contracts, bounded read workers, selected-file intake and actual public-source research. Ship J1 plus J5/J6/J9 protections. This produces useful work before introducing broad personal-account access. Initially deliver Markdown plus CSV/JSON and a trusted renderer; add richer formats after their rendering and validation pipeline exists.

### Then: execute one real cross-application task

Add one browser worker and one carefully selected native Mac action or real connector write, using the existing approval broker and independent verification. Ship J2/J3/J4 against actual approved targets. The demo app remains a regression fixture, not the final proof of general computer ability. Add email drafting and other connectors only with explicit account/scope contracts and real acceptance.

### Then: continuity, events and natural interaction

Add source watches, an honest delivery outbox and voice-to-run handoff; ship J7/J8. Keep schedules separate from event subscriptions and conversational continuity separate from raw transcript retention. Decide whether the authoritative service runs on an always-on host before offering overnight completion. Pi can remain the display/voice/posture endpoint; heavyweight browsing/model workloads can run elsewhere through an authenticated gateway.

### Preserve the embodied project

Keep fixed-camera posture → feedback → remeasurement as the existing physical mainline. RIG Arm and ESP32 cleaner integration still need selected hardware, local interlocks, watchdogs and physical stop evidence. A general computer agent must never gain raw motor or emergency-stop authority through a language-model tool. Nothing in Muse's product breadth changes that requirement.

### Resource and authorization gates

Set per-run model calls/tokens, wall-clock time, active workers, browser steps, downloaded bytes, artifact storage and total cost ceilings. Meter failed as well as successful attempts. Choose Standard/contributor data terms consciously; do not imply a consumer or coding subscription pays for arbitrary API use. Recheck the current [pricing and rate limits](https://dev.meta.ai/docs/pricing-rate-limits) before any approved live trial.

Live API keys, ongoing OAuth access, Mac permissions, external sending, payment and hardware movement each require their own authorized setup and test conditions. Research and local fictional-data engineering can proceed independently; missing authority should produce a named blocked capability, not an invented success or an attempt to work around the boundary.

## 9. First-round omissions and corrections

1. **Breadth was described but not operationalized.** The first report was more comprehensive than the first implementation batch, but the plan did not map the full research/artifact/computer/orchestration journey. This document supplies that missing mapping; it does not retroactively mark capabilities complete
2. **Workflow coverage was incomplete.** The first report disclosed a failed workflows-page fetch. Following the actual navigation now reached `/docs/muse-code/workflows`. Parallel/dependent orchestration and conditional recovery are substantive newly reviewed details, not merely a renamed reminder
3. **Native Mac and artifact recipes were omitted.** The first pass covered the native computer protocol, Linux sandbox and voice-Chess example, but not the dedicated macOS recipe or research-to-slides pipeline. They materially improve implementability
4. **File retention needs a correction.** “Uploaded files do not expire automatically” described the default too broadly. Explicit `expires_after` is documented. The project should use a deliberate retention choice and verified cleanup, rather than assume deletion is the only option
5. **API documentation is not perfectly consistent.** The server-managed conversation/truncation and forced-tool wording discrepancies above must remain visible. Do not blend examples into a claimed supported configuration without a version/account test
6. **Voice has not been proven by studying ASR.** Muse Voice Transcribe is speech-to-text. Consumer voice internals and a reusable full speech-to-speech agent contract were not established. Our existing voice transports also still require actual microphone/provider tests
7. **Product access was not exercised.** No consumer Muse account, authenticated connector submission, subscription, cloud VM or live task was tried. The linked official tour could not be inspected beyond available metadata; this report does not claim to have watched it
8. **Public source does not expose all internals.** Consumer memory ranking, private scheduling/planning heuristics, full connector schemas behind login, precise consumer quotas and current confidential-VM deployment remain unverified. A clean-room implementation should not invent those details
9. **The checkpoint is not commercial-product parity.** Narrow local scheduling, a saved-memory UI and one API-controlled test application do not establish broad personal assistance, general PC control or autonomous verified delivery. Future reports should lead with accepted real tasks, not component counts

The original report remains as the first-pass record; this supplement controls the corrections and expanded scope above.

## 10. Source coverage and remaining research boundaries

All links below were accessed on **12 October 2026**. Most developer pages display no publication date; the access date is not a claimed release date. “Read” means the relevant prose, constraints and lifecycle sections were inspected; repeated SDK-language examples and generated type catalogs were not all line-by-line audited. No private repository or protected implementation was accessed.

| Source group | Pages inspected in this second pass | Coverage/result |
| --- | --- | --- |
| Consumer identity/product | [Meta announcement](https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/), [design](https://introducing.muse.ai/), [security](https://research.meta.ai/blog/security-and-safety-for-ai-agents-our-approach-with-muse), [platform](https://muse.ai/platform) | Public product behavior, architecture, scope and gated connector boundary rechecked; main narrative read |
| Documentation discovery | [Official documentation index](https://dev.meta.ai/llms.txt) | Navigated relevant product/API/cookbook paths; did not treat same-name web search results as authoritative |
| Orchestration | [Workflows](https://dev.meta.ai/docs/muse-code/workflows), [extensions](https://dev.meta.ai/docs/muse-code/extending), [goals](https://dev.meta.ai/docs/cookbook/goal-tracking), [loop/cron](https://dev.meta.ai/docs/cookbook/loop-and-cron), [session messaging](https://dev.meta.ai/docs/muse-code/session-messaging) | Workflow, extensions, goal and scheduler prose read; session-messaging boundary rechecked, with first-pass detail retained |
| Runtime reuse | [Agent frameworks](https://dev.meta.ai/docs/agent-frameworks), [audit/resume](https://dev.meta.ai/docs/cookbook/audit-agent-sessions) | Framework configuration/production constraints and audit/recovery/redaction sections read; examples are not an authorization policy to copy blindly |
| Research/artifacts | [Search grounding](https://dev.meta.ai/docs/search-grounding), [file handling](https://dev.meta.ai/docs/file-handling), [generating slides](https://dev.meta.ai/docs/cookbook/generating-slides) | Search evidence/limitations; file size/coverage/expiry; complete slides recipe narrative. Repeated language examples not exhaustively audited |
| Computer use | [Computer guide](https://dev.meta.ai/docs/computer-use), [macOS recipe](https://dev.meta.ai/docs/cookbook/computer-use-macos) | Driver, observation/action/termination and native Mac requirements; no installation or execution |
| Lifecycle compatibility | [Responses](https://dev.meta.ai/docs/protocols/responses), [cancel](https://dev.meta.ai/docs/api-reference/responses/cancel-response), [tool calling](https://dev.meta.ai/docs/tool-calling) | Relevant background/state/restriction sections rechecked, including conflicting cross-page wording |
| Voice | [Speech-to-text](https://dev.meta.ai/docs/speech-to-text) | Rechecked ASR boundary, final-turn semantics and transport; no consumer voice/TTS equivalence inferred |
| Existing detailed SDK work | [First Muse report](muse.md) and its linked public SDK guides | Prior reviewed session/approval/idempotency/resume/MCP/preview findings retained; not a claim to have rerun host conformance |
| Project baseline | Implementation record; personal-context, routines, computer-jobs, provider-policy and task-tracking docs linked above | Read current capability contracts; comparisons pinned to the first software checkpoint, not speculative work in progress |

Navigation failures were handled by following the official index/navigation to working pages. Direct guessed paths for background/realtime pages and some Markdown variants returned research-tool errors; the actual Responses, speech and workflow paths supplied the relevant material. Consumer login and unavailable video content remain genuine coverage gaps. Prompt-caching details, image-generation internals and segmentation are not needed to establish the missing user journeys here and are not represented as fully audited in this supplement.

**Completion criterion for the next stage:** an ordinary user can request one of J1–J4, leave the chat usable, inspect progress and permissions, interrupt it, recover from a failure and receive a real verified result. Until those receipts exist, describe the system as a bounded personal-agent prototype under active implementation.
