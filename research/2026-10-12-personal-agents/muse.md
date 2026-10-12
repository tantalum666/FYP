# Muse: public architecture, reusable interfaces, and FYP implications

Research date: 12 October 2026 (UTC). Scope: Meta’s personal agent, its public developer ecosystem, and a clean-room design for the FYP’s one-user desktop/embodied agent. This is documentation research, not a claim of having installed, authenticated to, or tested these products. No accounts, keys, purchases, or external changes were made.

## 1. Executive conclusion

**The correct Muse is Meta’s personal AI agent at muse.ai.** The official announcement identifies the vendor and describes a persistent cloud-computer assistant that continues tasks after the app closes. The product was announced on 8 September 2026. Older video-hosting Muse documentation and unrelated products called Muse must not be used as evidence for this agent. [Official announcement](https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/)

There are four distinct integration opportunities:

| Surface | What is actually public | FYP decision |
|---|---|---|
| Consumer Muse | Product descriptions, public security architecture, connector submission | Use as a behavioral and safety reference; do not assume an embeddable personal-agent API |
| Meta Model API | HTTP inference, tools, computer-use actions, asynchronous responses, transcription | A real candidate model/perception backend for an agent we own |
| Muse Code + SDK | Local agent host, session protocol, TypeScript/Python clients, tools, approvals, durable session state | A real candidate agent harness for a Mac prototype; Developer Preview dependency |
| Muse Glimmer | Apache-2.0 open-weight multimodal model and deployment documentation | Optional local-model research on sufficiently capable hardware, not a default Pi choice |

The strongest FYP approach is to **own the user identity, device UI, task ledger, calendar connection, permission gate, hardware safety, scheduler, and evaluation**, with a replaceable model/harness adapter. Muse Code can accelerate a trial; the product must not depend on private consumer Muse internals. This recommendation is our synthesis, not a statement of Meta’s implementation.

## 2. What is known about consumer Muse

### Publicly documented behavior

Muse’s design article describes one main ongoing conversation, optional side chats, cross-conversation memory, concurrent work, scheduled/event-driven activity, and selective proactive notifications. Users can inspect activity and permissions, read/edit memory, track goals, and receive interactive artifacts. Its design explicitly distinguishes conversational interaction from deterministic approval UI. These are documented product behaviors, not public API contracts. [How We Designed Muse](https://introducing.muse.ai/)

The landing page describes mobile, Mac, and WhatsApp access; user-visible activity/audit trails; connected apps; and tools the agent can create. Its cloud browser and user-controlled intervention belong to that hosted product. Do not infer that a Model API request provides the same VM, connected accounts, or ongoing persona. [Muse product page](https://muse.ai/?return_to=%2Fplatform)

### Published security architecture: compact factual summary

Meta documents a per-user Linux VM with the agent in a restricted systemd-nspawn cell. Host-side services separately handle safety checks, privileged connectors, credentials, and permission decisions. Sentinel controls connector actions and network egress; surrogate credentials are substituted at the boundary. Approvals are scoped capabilities. The browser broker exposes a controlled accessibility-tree interface rather than arbitrary page JavaScript, and pauses the agent during user takeover/credential entry. Credentials and durable application state are separated from the agent runtime. The article also describes network/data-flow controls and prompt-injection defenses. Its launch architecture still permits operational Meta access; confidential VMs were described as forthcoming. It says training trajectories are sanitized and users can opt out. These are vendor-published claims, not independently audited guarantees in this report. [How We Built Safety Into Muse](https://research.meta.ai/blog/security-and-safety-for-ai-agents-our-approach-with-muse)

### Consumer connector availability

Muse Connector Platform offers submission, functional/security/legal review, testing, and approved-directory listing. The publicly accessible page does not provide a callable agent API, full connector manifest, webhook contract, or credential-exchange specification. The “Submit a connector” route returned a login page in this research. **A platform application is not evidence that an FYP can immediately embed or remotely drive consumer Muse.** [Connector Platform](https://muse.ai/platform)

**Unverified/unavailable:** exact consumer memory schemas, prioritization algorithms, private prompts, internal orchestration APIs, voice transport, connector SDK details behind login, precise consumer resource quotas/pricing, and the current deployment status of confidential VMs. We should not extract protected prompts or access private implementations to fill these gaps.

## 3. Meta Model API: implementable primitives

### Entry point and model selection

The API documentation identifies `https://api.meta.ai/v1`, bearer authentication, OpenAI-compatible Responses/Chat Completions, and an Anthropic-compatible Messages surface. It separates hosted inference from the consumer agent and from the locally run Glimmer model. [Overview](https://dev.meta.ai/docs/overview)

For new work, Meta recommends Responses. It supports reasoning continuity and agent-oriented features; Chat Completions is a compatibility path, while Messages accepts Anthropic-style requests. Compatibility is not equivalence with every feature of another vendor’s API. [Protocol comparison](https://dev.meta.ai/docs/protocols)

The model catalog recommends `muse-spark-1.3`, with a 1,048,576-token context, text output, and multiple input modalities. Important caveat: the current catalog says Spark 1.3 audio understanding is not fully supported and quality may degrade; use dedicated transcription or Spark 1.2 for audio. Glimmer is not served through this Model API. Query `GET /v1/models` after authorization to establish what the actual account can use. [Models](https://dev.meta.ai/docs/models)

### Authentication and data boundary

Ordinary HTTP requests use `Authorization: Bearer …`. Meta recommends separate application keys, server-side storage, revocation/rotation, and avoiding browser/mobile client exposure. The FYP should keep provider credentials in a backend or OS credential store; never send them to the ESP32, include them in prompts, or ship them in the web display bundle. Model API authentication does not supply Google Calendar OAuth or device enrollment. [Authentication](https://dev.meta.ai/docs/authentication)

The documented OpenAI Python/TypeScript and Anthropic client compatibility avoids a mandatory proprietary HTTP client. Still put provider-specific request construction behind an adapter; SDK-compatible naming alone does not guarantee parameter support. [SDKs and libraries](https://dev.meta.ai/docs/sdks)

### Tool execution contract

Functions are developer-defined and **developer-executed**. Responses produces `function_call` items and expects matching `function_call_output` items keyed by `call_id`. Streamed argument fragments are not yet executable requests. Only `tool_choice: "auto"` is documented; forcing a specific/required/none choice returns 400. `max_tool_calls` limits built-in tools, not arbitrary client tools. The harness must enforce its own action/turn budget. `parallel_tool_calls: false` can constrain parallel function calls. Function `strict` currently controls schema validation, not permission or physical safety. [Tool calling](https://dev.meta.ai/docs/tool-calling)

Tool search can defer tool schemas, with hosted or client-executed lookup. It supports namespaces and keeps the initial prompt smaller. It requires a tool-search entry and deferred functions; current documentation forbids combining tool search and `json_schema` structured output in the same request. For a small FYP tool inventory, explicit functions are simpler initially. [Tool search](https://dev.meta.ai/docs/tool-search)

Structured output has a strict JSON-schema subset: object roots, all properties required, `additionalProperties: false`, no `allOf`/`oneOf`, and documented depth/size caps. Use this for proposals and structured extraction, then apply application validation before execution. A schema-valid command can still be semantically unsafe. [Structured output](https://dev.meta.ai/docs/structured-output)

### State, background execution, and recovery

Responses offers either stored history through `previous_response_id` or stateless replay with `store: false` and opaque encrypted reasoning items. Default storage is true. Context compaction is the client’s responsibility; `truncation: "auto"` is rejected. Background creation uses `background: true`, cannot simultaneously request `stream: true`, and has a 1 MiB creation-body cap. It acknowledges a queued response, which is not proof of task completion. This is asynchronous inference, not a perpetual scheduler or autonomous calendar agent. [Responses guide](https://dev.meta.ai/docs/protocols/responses)

`GET /v1/responses/{id}` retrieves stored results. For an in-progress background response, streaming retrieval supports `starting_after` to resume after a sequence number. This provides a concrete recoverable job interface. [Retrieve response](https://dev.meta.ai/docs/api-reference/responses/retrieve-response)

`POST /v1/responses/{id}/cancel` applies to background responses. Keep inference cancellation separate from cancellation of a device operation already accepted by an actuator. [Cancel response](https://dev.meta.ai/docs/api-reference/responses/cancel-response)

**Webhook finding:** no documented Model API completion-webhook registration/signing contract appeared in the official documentation index or targeted searches. Build against polling/SSE retrieval unless Meta later documents a webhook. Likewise, no public consumer-Muse event subscription API was verified. This is a bounded search result, not a claim that no private partnership API exists.

### Files and context limits

Files can be inline or uploaded, but neither is a semantic personal-memory database. The guide lists 50 MB inline, 1 GiB upload, and 100 GiB per-team stored files. Uploaded files do not expire automatically. PDFs supply text from at most the first 100 pages and images from at most the first 50; those images count toward the 50-image request budget. Store minimal authorized material, clean up uploads, and explicitly detect truncated document coverage. [File handling](https://dev.meta.ai/docs/file-handling)

Reasoning tokens consume output budget and cost. Spark rejects reasoning `none`; `max` is specific to Standard Spark 1.3. Start interactive requests at low/minimal effort and measure actual latency and quality rather than assuming a huge context or high effort makes a voice assistant better. [Reasoning](https://dev.meta.ai/docs/reasoning)

## 4. Computer use and bounded Mac operations

The native Responses computer tool is real: `tools: [{"type":"computer"}]` returns `computer_call` actions for a driver to execute. The developer supplies the actual browser/desktop and returns screenshots. Actions include click, type, keypress, move, drag, scroll, wait, and screenshot. Coordinates refer to the exact preceding screenshot. A changed modal/navigation or failed action requires stopping a batch. Safety checks require deliberate handling, not automatic acknowledgement. The API does not provide an automatic desktop sandbox or a consumer Muse Secure VM. [Computer-use guide](https://dev.meta.ai/docs/computer-use)

An official cookbook alternatively uses OpenCode plus a Cua MCP bridge and disposable Linux desktop. It is useful for repeatable evaluation away from a user’s real desktop. The recipe has mixed Spark 1.1/1.3 references, so use a pinned tested model rather than copy all text blindly. [Sandbox computer-use recipe](https://dev.meta.ai/docs/cookbook/computer-use)

A particularly relevant official voice/Chess example uses a deterministic parser, exact application identity, accessibility-state validation, final-transcript gating, and post-action confirmation; it rejects ambiguous windows and stale/duplicate transcripts. That is a better pattern for a bounded FYP action than exposing a general mouse/keyboard controller for every command. [Voice-controlled Chess recipe](https://dev.meta.ai/docs/cookbook/voice-chess-cua)

**Our FYP recommendation:** first support named capabilities such as opening a particular app, revealing a selected file within a test folder, reading a calendar, or starting a timer. Require an allowlisted bundle ID, current state check, explicit user-intent ID, and outcome evidence. Broader screenshot-driven automation belongs in an isolated test desktop before any personal Mac trial. Never treat spoken text captured from a webpage, another person, or the agent’s own speaker as authorization.

## 5. Voice: what is reusable and what is missing

Muse Voice Transcribe is speech-to-text, not TTS or full speech-to-speech. The guide supports push-to-talk, endpointing, diarization, vocabulary/context biasing, and turn-level timestamps. Real-time sessions last up to 60 minutes and have no resume token. Audio must be real-time-paced raw mono 16-bit little-endian PCM at 16 or 24 kHz; active silent streams still require input. Diarization labels are session-local, not identity authentication. [Speech-to-text guide](https://dev.meta.ai/docs/speech-to-text)

The real-time endpoint is `wss://api.meta.ai/v1/asr/realtime`. Authentication goes in the first JSON handshake within 10 seconds, not an HTTP Authorization header or URL parameter. Wait for the acknowledgement before streaming binary audio, send `endStream`, then drain final events before normal close. The reference distinguishes malformed/pacing failures (1008), backend/session-duration failures (1011), and rate limits (1013). [Realtime reference](https://dev.meta.ai/docs/api-reference/voice/realtime)

File transcription uses `POST /v1/asr/transcribe`, multipart settings plus audio, with JSON, SSE, or plain text output. It caps a recording at 10 minutes and the body at 32 MB. [File transcription reference](https://dev.meta.ai/docs/api-reference/voice/transcribe)

**Build or source separately:** speech synthesis, wake-word/push-to-talk UI, echo suppression, barge-in, microphone/privacy indicators, transcript correction, conversation turn routing, reconnect stitching, and user authentication. For the first trial, push-to-talk plus a visible transcript and confirm button gives a controllable baseline. Only finalized, fresh utterances may create action proposals; partial transcripts may update the screen but must not move hardware.

## 6. Muse Code SDK: a real harness option, with boundaries

### Availability and licensing

The official public repository exposes `@muse-code/sdk`, protocol declarations, and TypeScript examples under MIT. It calls the SDK Developer Preview and explicitly says the actual `muse` host binary is separate and not included in the repository. Therefore the public SDK is not the full open-source agent harness, and its license does not by itself grant redistribution rights to the binary. [SDK repository](https://github.com/meta-models/muse-code-sdk)

The SDK docs also publish a Python client. The public navigation distinguishes integrating a client from extending the agent and includes generated wire/API references. These pages carry build provenance and schema fingerprints. Most detailed pages resolved under `/next/`; treat that as a documentation snapshot to compare with the installed host, not an unconditional stable contract. [Developer docs](https://meta-models.github.io/muse-code-sdk/next/)

### Minimal integration path

A supported path is: installed/authenticated host → spawn `muse serve` → initialize → subscribe immediately → `session/start` → `turn/start` → render item events → handle approvals/questions → await terminal turn event → resume later. TypeScript requires Node 20+; Python requires 3.10+ and its SDK/wire-type packages. The quickstart warns that notifications preceding subscription are not buffered, and that admission acknowledgement is not completion. `turn/cancel` is cooperative; wait for the terminal event. [SDK quickstart](https://meta-models.github.io/muse-code-sdk/next/guides/quickstart/)

MSP v1 uses a single spawner-owned stdio connection with NDJSON JSON-RPC 2.0, not a public WebSocket server. External socket/WebSocket transports are deferred. The default frame cap is 10 MiB; page larger results rather than retrying oversized frames unchanged. `clientInfo` identifies the client but is not authentication. A remote Pi/web client therefore needs our authenticated application gateway instead of direct exposure of this process protocol. [Wire framing](https://meta-models.github.io/muse-code-sdk/next/guides/msp-wire/framing-and-caps/)

### Durable lifecycle and exactly-once caveat

Each state-changing command has a client-minted UUIDv7 `commandId`. The documented durable admission ledger deduplicates retries, including across host restarts, and rejects reuse with a different payload. Events, rather than the acknowledgement alone, establish what happened. This is a valuable primitive for resilient UI commands. It does **not** prove exactly-once effects in an external calendar or ESP32; those need their own idempotency keys and reconciliation. [Commands and idempotency](https://meta-models.github.io/muse-code-sdk/next/guides/msp-concepts/commands-and-idempotency/)

Resume uses opaque cursors, snapshot/inline/suffix modes, and pending-request pointers. Do not parse a cursor or assume history always contains one full item array. Persist enough UI state to resume from an observed cursor and page missing material. [Resume](https://meta-models.github.io/muse-code-sdk/next/guides/msp-concepts/resume/)

A host can be durable or ephemeral. The latter loses session state with the process and has no resume/fork/read surface for that session. Unknown durability values must be treated conservatively. [Durability profiles](https://meta-models.github.io/muse-code-sdk/next/guides/msp-concepts/durability-profiles/)

The official host-death recipe explicitly warns that an unknown terminal result must not be resubmitted as though it never ran. This applies especially to physical operations: query current actuator state after reconnect and require a new deliberate action when the old result is ambiguous. [Host-death recovery](https://meta-models.github.io/muse-code-sdk/next/cookbook/survive-the-host-dying/)

### Interruptions and approvals

Busy-session input can start, queue, or steer; the acknowledgement’s `disposition` is authoritative. A queued turn has an identity and can be reclaimed before execution. Target a specific active turn when interrupting rather than accidentally steering a newer turn. [Queue/steer/reclaim](https://meta-models.github.io/muse-code-sdk/next/cookbook/queue-steer-and-reclaim-turns/)

Approvals have durable IDs, staged requirements, server-issued choices, and resolved events. Clients select offered choices, fail closed on unknown subject kinds, and handle stale/racing decisions. Pending v1 approvals do not simply expire. Recovery can issue a successor request under current policy, so the UI must not recycle an old approval blindly. This is a model for a proper authorization UI; it is not satisfied by a conversational “yes” untied to a concrete request. [Approvals](https://meta-models.github.io/muse-code-sdk/next/guides/msp-concepts/approvals/)

### Tools, memory, extensions, and safety

Muse Code supports parallel subagents, skills, lifecycle hooks, MCP, and headless JSONL output. It distinguishes required MCP servers, whose failure aborts a run, from optional ones. Its CLI exit status describes the run’s termination, not whether the requested work is correct. Read tool results and run acceptance checks. [Extending and automating](https://dev.meta.ai/docs/muse-code/extending)

Documented project memory is indexed Markdown with personal/project scopes and lazy recall. At session start, its memory index and up to 48 topic paths are surfaced. This is concrete and reusable, but does not establish the consumer Muse memory schema. Keep user-private memory out of shared repository scopes. [Configuration and context](https://dev.meta.ai/docs/muse-code/configuration)

The shell has OS-enforced isolation, approvals, and workspace/network controls. Platforms use different mechanisms; failure to prove containment blocks shell execution. Permission profiles and inherited child boundaries are documented. Avoid unrestricted modes in a desktop/robot trial. [Permissions and safety](https://dev.meta.ai/docs/muse-code/permissions)

**Critical exception:** MCP servers are outside the shell sandbox. A local MCP server is an ordinary child process; a remote one is a direct connection. The SDK extension docs explicitly require trust in those servers. Build a narrowly privileged `fyp-device`/`fyp-calendar` service, not a generic credential-bearing shell MCP. The newer extension docs use `mcpServers`; the user manual shows `mcp_servers`. Validate the actual release/schema rather than mixing examples. [MCP server guide](https://meta-models.github.io/muse-code-sdk/next/guides/extend/mcp-servers/)

Plugins package skills, commands, hooks, and tools; more powerful capabilities require separate review. Plugin MCP entries do not carry credentials in the documented format; authenticated machine-specific configuration belongs outside the distributable plugin. Plugin installation/approval is local management, not an MSP remote management API. [Plugin guide](https://meta-models.github.io/muse-code-sdk/next/guides/plugins/)

### Background scheduling limitations

The official loop/cron recipe says scheduling is session-scoped, local-time-based, requires a running Muse Code process, can add up to 30 minutes of deterministic jitter, and expires recurring jobs after seven days. Recovery performs bounded catch-up. It explicitly recommends external scheduling for indefinitely recurring work or work while Muse Code is closed. That prevents treating `/loop` as the FYP’s reliable reminder infrastructure. [Loop and cron](https://dev.meta.ai/docs/cookbook/loop-and-cron)

Goal tracking retains an objective and gates completion against acceptance evidence. It is useful as a task-completion pattern, but does not make a task safe or guarantee correct verification. Define an external oracle: returned calendar event ID, actual foreground app, or observed device state. [Goal tracking](https://dev.meta.ai/docs/cookbook/goal-tracking)

Session messaging is same-user/same-machine, currently macOS/Linux, and does not merge permissions or grant consent. It is not a Pi-to-Mac network bus. [Session messaging](https://dev.meta.ai/docs/muse-code/session-messaging)

### Version and release risk

The SDK remains preview despite the more mature Muse Code product. TypeScript tolerates a newer host with a fingerprint warning; Python requires a matching host fingerprint and raises a typed mismatch. Published compatibility rows include host/wheel pairings through 1.4.6 in the reviewed snapshot. Pin a known pair and add a handshake/conformance smoke test; do not infer availability from a documentation page alone. [Compatibility](https://meta-models.github.io/muse-code-sdk/next/compatibility/)

## 7. Local inference: Muse Glimmer and the Pi

Glimmer is a 30B dense multimodal model with a default 128K context and Apache-2.0 weights. It is a model, not an already personal assistant with memory, calendar, or hardware tools. [Glimmer overview](https://dev.meta.ai/docs/muse-glimmer)

Official quantization documentation lists a 16.8 GB text checkpoint, 1.4 GB vision projector, and measured 19 GiB VRAM for the described full-context vision setup. This makes “run Muse locally on the Pi” an unsupported default assumption when the Pi has less available memory than the model footprint. A capable Mac/workstation is the more plausible local-model experiment. Benchmark before promising responsiveness. [Quantization and memory](https://dev.meta.ai/docs/muse-glimmer/quantization)

The llama.cpp deployment guide specifies support from b10353, a required chat template, explicit model alias, and context/slot considerations. For a local research branch, pin runtime and model artifacts and measure loading RAM, first-token latency, tokens/sec, and tool-call correctness. [llama.cpp deployment](https://dev.meta.ai/docs/muse-glimmer/llama-cpp)

## 8. Cost and quota snapshot

As reviewed: Spark Standard input/cached-input/output cost $1.25/$0.15/$4.25 per million tokens. Contributor is $0.10/$0.002/$0.20 but permits training on prompts/completions. Standard is documented as not training on them. Transcription costs $0.18/hour; search adds $2.50/1,000 queries. Standard quotas are 3,000 RPM/4M TPM; Contributor 100 RPM/3M TPM. Background submissions have a separate 600/minute cap. Transcription allows 128 concurrent streams and 16,000 starts/hour. Limits are shared at team level. Reconfirm before implementation. [Pricing and rate limits](https://dev.meta.ai/docs/pricing-rate-limits)

Illustrative arithmetic, not a usage forecast: 2M uncached input tokens + 0.5M cached + 0.1M output + 10 transcription hours + 100 searches = **$5.05** at those rates. This excludes TTS, hosting, hardware, taxes, and repeated screenshots/tool-loop overhead. Log actual usage per completed task and enforce a budget. Do not choose Contributor solely for its low price when testing personal calendars or private transcripts.

Muse Code subscription pricing is a different commercial surface from inference billing; the product page lists $5/$15/$50 monthly usage plans. A consumer or coding subscription must not be assumed to cover arbitrary external Model API calls or redistribution. [Muse Code plans](https://dev.meta.ai/products/muse-code)

## 9. Proposed FYP architecture (our design, not Meta internals)

### Components and ownership

1. **Pi/display client:** avatar state, text, microphone control, speaker output, explicit approvals, and a physical stop button. The display is an interface, never the source of truth for successful execution.
2. **Single-user agent service:** one durable identity and task history accessible from Pi, web, and Mac clients. It owns tool proposals, event routing, cancellation, user-facing progress, and model/harness choice.
3. **Provider adapter:** either direct Model API calls or a local Muse Code SDK host. Expose the same FYP interface: submit, events, approve, cancel, resume, usage. Keep task records outside provider-specific history.
4. **Permission broker:** deterministic rules before every side effect. Validate caller, intended tool, arguments, approval, expiry, and current environment. The planner cannot change this policy.
5. **Calendar adapter:** separate read and write operations, explicit OAuth scopes, native API operations, and returned event IDs. Do not use a desktop mouse agent when a reliable provider API suffices.
6. **Mac companion:** a small authenticated local service with a finite action list, test-folder boundary, exact app checks, and audit records. It can use native automation/accessibility or a separate isolated computer-use driver.
7. **RIG arm / ESP32 cleaner service:** high-level, validated commands plus telemetry. Local controller owns motion constraints, watchdogs, emergency stop, and safe states. The LLM never writes raw motor PWM or bypasses interlocks.
8. **Durable scheduler:** stores UTC fire time plus user timezone, recurrence, last completion, retry policy, cancellation, and delivery status. It wakes the agent service, which rechecks authorization and relevance.
9. **Memory and audit store:** separate editable user facts, active tasks, raw conversation, approvals, and execution receipts. Each memory fact carries source, timestamp, confidence, and deletion status.

### Minimum action envelope

This is an FYP proposal, not a Muse API schema:

```json
{
  "action_id": "unique-id",
  "task_id": "task-id",
  "intent_event_id": "final-user-input-id",
  "tool": "cleaner.start_preset",
  "args": {"preset": "bounded_demo"},
  "target_device": "cleaner-01",
  "approval_id": "single-use-approval-id",
  "expires_at": "2026-10-12T12:30:00Z",
  "preconditions": {"estop_clear": true, "workspace_clear": true},
  "idempotency_key": "unique-id"
}
```

Tool names above are proposed FYP names, not existing vendor functions. The device service must ignore unsupported fields/actions, reject expired or replayed authorizations, and recheck sensor state locally. On an uncertain network result, query the same action ID; never blindly repeat a movement.

### Task state machine and UI

Use `proposed → awaiting_approval → queued → running → verifying → succeeded`, with explicit `failed`, `cancelled`, `blocked`, and `outcome_unknown` alternatives. Keep these distinct from a model response’s terminal status. A terminal model answer can still describe failed work. A UI “Stop” first blocks new effects and requests device stop, then cancels reasoning; cancellation of inference alone is not an emergency stop.

The avatar can expose simple states: listening, thinking, waiting for approval, working, paused, and result-ready. Show the exact task and target under the avatar so an embodied personality does not hide authority or state.

### Suggested trial sequence

1. **Text-only Mac/web baseline:** one persistent identity, explicit task records, mock calendar and device tools, all effects in a test sandbox.
2. **Voice:** push-to-talk → finalized transcript → visible proposal → deterministic tool validation → result → TTS. Measure transcription and confirmation errors separately.
3. **Real calendar read:** test retrieval, timezone handling, duplicate events, revoked authorization, and stale cache. Add writes only after a preview/confirm workflow works.
4. **Bounded Mac actions:** exact allowlist and test workspace; prove that disallowed apps, paths, and stale screen states fail closed.
5. **Hardware mock → dry run → low-energy physical demo:** test offline state, lost acknowledgements, duplicate messages, watchdog expiration, and stop latency before normal movement.
6. **Cross-surface continuity:** close the web UI while a safe task runs, reconnect from Pi, and verify the same task state and approval. Restart the service and reconcile in-flight operations.

### Evaluation targets

- Task completion verified by external state, not model self-report
- Unauthorized side effects: zero in the test suite
- Duplicate side effects under retry/reconnect: zero
- Voice false-trigger and transcript-to-intent error rates
- Approval comprehension and cancellation/stop latency
- Memory correction/deletion accuracy and cross-session continuity
- Reminder timing after restart and timezone changes
- End-to-end p50/p95 latency and cost per successfully completed task
- Prompt-injection tests: malicious calendar text, web text, tool output, and quoted messages must not grant permissions

## 10. Coverage ledger and remaining gaps

The research followed the official product launch → design/security links → developer home → documentation index and `llms.txt` → capability/API pages → SDK navigation. “Reviewed” below means relevant prose/contracts were read, not every repeated code example or every generated schema type.

| Area | Primary documents reviewed | Result |
|---|---|---|
| Identity/product | Announcement; Muse landing page; design article; safety article | Correct vendor confirmed; consumer behavior separated from API |
| Consumer extensibility | Muse Connector Platform and submission route | Public overview available; submission gated by login; no public callable agent contract verified |
| API entry | Overview; quickstart; protocols; authentication; SDKs; model catalog; documentation index | Concrete endpoints and client options identified |
| Tools | Tool calling; tool search; structured output | Execution ownership and parameter incompatibilities identified |
| Lifecycle | Responses; retrieve/cancel references; reasoning; file handling | Async operations, state options, caps, and recovery paths identified |
| Computer use | Native computer tool; Cua recipe; voice/Chess recipe | Model emits actions; our driver/environment and safety remain required |
| Voice | Speech-to-text guide; realtime/file references; model page | ASR contracts and limitations identified; TTS absent from this surface |
| SDK client | Public repo; docs home; quickstart; framing; sessions; idempotency; resume; durability; queueing; approvals; recovery; compatibility | Usable local harness client with preview/version risks |
| SDK extensions | Extending; configuration/memory; permissions; MCP; plugins; session messaging; hooks page | Real extension surfaces; MCP sandbox gap and config-version differences identified |
| Ongoing work | Loop/cron; goal tracking | Process-bound short-lived schedule unsuitable as sole FYP reminder system |
| Local model | Glimmer overview; llama.cpp; quantization | Local option exists; footprint must match hardware |
| Cost | Model API pricing; Muse Code plans | Distinct commercial surfaces and privacy tradeoff recorded |

Access failures/gaps: two direct requests for prompt-caching and workflows pages failed through the research tool, including Markdown alternatives; no claim of having reviewed those full pages. The API overview/pricing documents still establish that caching exists, but detailed cache behavior should be verified before optimization. SDK public docs were largely under `/next/`; on-device availability, rollout gates, binary platform support for the exact Pi architecture, SDK/binary licensing for redistribution, actual account availability, latency, and hardware behavior remain untested. Consumer voice, consumer pricing/quotas, and developer connector schemas behind login remain unverified.

**Final implementation gate:** before choosing Muse Code over a custom harness, run an authorized, pinned-version spike that proves start/stream/approval/cancel/restart plus one calendar mock and one device mock. Before choosing the Model API, run an authorized model-list/read-only inference and ASR smoke test. Neither check requires exposing raw credentials to the model. Maintain a fallback provider adapter so a preview protocol or regional rollout cannot block the FYP.

## 11. Reconciliation with the existing FYP baseline

The repository was read at pinned commit `50e174f50a4130b3c666f836f666f6aa4cde4b32`. The current `product.md` and `handoff.md`, rather than the September food-monitoring research, define the agent direction. This section is project-source reconciliation, not a Meta product claim.

- Preserve the existing React/TypeScript/Vite display and FastAPI/SQLite backend. The accepted A1 avatar is a full, unsliced 2D PNG with restrained global motion; Muse research gives no reason to restart the rejected 3D/segmented-avatar work.
- Preserve fixed-camera visible head/shoulder posture feedback as the established physical mainline, alongside voice, calendar, and bounded PC operations. A general agent kernel should integrate these capabilities instead of displacing them.
- Reuse and strengthen the existing task/job ledger, deterministic approvals bound to complete action content and target/version, device enrollment/revocation, and unknown-outcome reconciliation. Do not add a second approval authority inside a model prompt. Current note-only PC jobs do not establish a functioning general GUI executor.
- Pi 5 8GB, RIG Arm, and the detachable cleaner are candidates, not evidence of purchased or tested hardware. Existing sim/PCA9685 arm support does not establish a RIG/ESP32 adapter. Muse Glimmer’s documented footprint reinforces keeping Pi-side responsibilities small, but does not select final hardware.
- Calendar code, provider adapters, and repository tests are distinct from live authenticated calendar/provider success. This research executed no live API, voice, hardware, or computer-control trial and reran no project tests.
- The September 10–19 food, competition, branding, and nutrition research remains historical context. Preserve its discipline around source provenance, unknown values, immutable snapshots, and separating proposed capabilities from tested evidence. Do not reinstate the superseded Senplate food product or treat old competition/domain/trademark observations as current facts.

Reading coverage for this assigned historical subset is recorded in `output/qa/2026-10-12-agent-kernel/muse-research-reading-ledger.json`: 18 research files, 1,471 lines, 192,356 bytes, explicit repaired ranges for two truncated reads, EOF verification, and pinned Git-blob identity checks. Other readers cover the remaining repository Markdown.
