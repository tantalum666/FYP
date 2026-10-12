# Grok Bot: clean-room capability and implementation study for FYP

Retrieved and checked: 12 October 2026 (UTC). Scope: official public documentation, its published schema, and FYP's documented baseline. No product login, paid API call, credential creation, or behavioral experiment was performed. Product capabilities below are **documented**, not independently benchmarked. Implementation contracts are **our proposed design**, not claims about proprietary internals.

## 1. Identify the correct product

The target is **Grok Bot**, the named, persistent, computer-using assistant product at [x.ai/bot](https://x.ai/bot) and [its own documentation](https://docs.x.ai/grok-bot/overview). It is separate from Grok conversational chat, the Grok Build coding CLI, the @grok X reply account, and the xAI model API. The [official launch](https://x.ai/news/introducing-grok-bot) presents a team of always-available agents that work across applications, retain working context, and learn repeatable workflows.

Important verified separation: the [Bot security documentation](https://docs.x.ai/grok-bot/security) assigns model selection to Cursor; it says the serving mix can change and does not guarantee a fixed vendor set. The [security FAQ](https://docs.x.ai/grok-bot/security-faq) explicitly states “Grok Bot runs only on Cursor-hosted cloud computers.” Both fetched at their exact official URLs, with no cross-product redirect. The [official Cursor billing page](https://cursor.com/help/grok-bot/plans), linked from xAI's overview, independently corroborates the Cursor account and metering relationship. Therefore reproducing the useful experience does **not** imply using xAI models or replicating a published Grok Bot engine.

No public, supported Grok Bot orchestration SDK or Bot-management API was identified in this documentation corpus. The published model API provides useful components; it does not publish the complete product runtime, memory selection, scheduler implementation, review prompts, computer controller, or routing logic. Absence from this reviewed corpus is not proof that no private or future API exists.

## 2. Capability matrix

| Capability | What official Grok Bot docs establish | Public API building block / gap | Practical FYP adaptation |
|---|---|---|---|
| Persistent identity | Named role, description, avatar, distinct conversation and learned context [Bots](https://docs.x.ai/grok-bot/bots) | System instructions plus application-owned storage; no Bot persona endpoint found | One visible assistant identity; version its profile and apply it to every text/voice response |
| Continuous execution | Cloud work continues after app/laptop closes [Overview](https://docs.x.ai/grok-bot/overview) | Model requests alone do not create a persistent runtime | Host task service on the always-on Pi/host; store durable jobs; accurately show host offline |
| Parallel specialist work | Bots can message asynchronously, wake one another, and hand off ownership; group chats support 2–6 Bots [Collaboration](https://docs.x.ai/grok-bot/chat-and-collaboration) | Function calls or app-level worker queues | Start with one coordinator and at most one bounded worker; specialists can be internal |
| Computer actions | Browser, terminal, files; personal Bots share an account computer and credentials, with separate screens [Computer](https://docs.x.ai/grok-bot/computer-and-apps) | Custom executor required; model API has no documented full Bot desktop-controller endpoint | Separate read-only/preview/workspace adapters, an explicit target environment, and exclusive GUI lease |
| App connections | Connectors preferred where available; plugins and their installed availability are account-wide [Computer](https://docs.x.ai/grok-bot/computer-and-apps) | Function calling or remote MCP | Keep credentials server-side; grant narrow scopes; prefer APIs over pixel clicks |
| Live voice | Product has dictation, live calls, and voice memos; direct user messages can redirect work [Collaboration](https://docs.x.ai/grok-bot/chat-and-collaboration) | xAI Speech-to-Speech WebSocket is available, but is not proof of Bot's own voice internals | One responsive voice entry point with asynchronous task tools and one narration owner |
| Long-term memory | Stable facts/preferences and work summaries; current consequential facts should be reread [Bots](https://docs.x.ai/grok-bot/bots) | Response history, compaction, and RAG are distinct from semantic personal memory | Store explicit facts with source, confidence, scope, timestamps, and correction/deletion controls |
| Skills | Reusable process with inputs, steps, validation, output and approval boundaries [Skills](https://docs.x.ai/grok-bot/skills-routines-and-automations) | Application instruction documents; no need for an agent framework | Versioned declarative skill plus typed permitted tools; test before activation |
| Scheduled/event work | Routine owns schedule/timezone, input, output and boundaries; event integration may be separate from plugin authentication [Skills](https://docs.x.ai/grok-bot/skills-routines-and-automations) | Own scheduler and authenticated event receiver | Persist occurrences and dedupe keys; narrow filters; quiet-hours and missing-data policy |
| Approvals | Action/arguments review, allow once, deny, narrow remembered rules; unattended approvals expire in about10 minutes [Approvals](https://docs.x.ai/grok-bot/approvals-security-and-privacy) | Own policy engine; model API does not supply Bot Auto Review | Preserve FYP's deterministic proposal/approval path; hash exact intent and expire it |
| Safety review | Separate review model covers risky tool, computer, automation, and delegation operations [Security](https://docs.x.ai/grok-bot/security) | Optional second model is advisory, not an enforcement boundary | Deterministic deny/approval controls first; optional reviewer cannot override them |
| Files/evidence | Results can include artifacts, screenshots, source links and action records [Files](https://docs.x.ai/grok-bot/files-and-results) | Files/RAG APIs or own artifact store | Completion requires verifiable receipts; interface distinguishes accepted, executed, and verified |
| Shared team assistant | Team memory plus private user notes; OAuth uses requesting person's account; some configured secrets are team-shared [Team Bots](https://docs.x.ai/grok-bot/team-bots) | Application authorization problem | Defer multitenancy; three developers do not mean three unrestricted end-user accounts |
| Product ingress | @bot can acknowledge an X request publicly while work/results stay in the app [Tag on X](https://docs.x.ai/grok-bot/tag-on-x) | Channel adapter/webhook equivalent | Defer public social ingress; use the local app and owner-authenticated events |
| Lifecycle recovery | Computer recreate can pause at a safe point; termination stops a running turn while keeping durable disk [Computers](https://docs.x.ai/grok-bot/computers) | Own recovery logic | After executor crash, ambiguous writes become unknown and need reconciliation, never blind retry |

### What should not be copied literally

A product's shared credential surface is not desirable merely because it enables convenient handoff. For FYP, keep robot control, owner approval, local computer execution, connector credentials, public display projection, and model access as distinct permissions. A model cannot approve its own proposal. GUI automation must not inherit physical-device control. The hardware emergency-stop path must not depend on a cloud model, a browser, or voice recognition.

## 3. Public xAI API: useful contracts and traps

### 3.1 Text and tool execution

The [quickstart](https://docs.x.ai/developers/quickstart) supports xAI's Python SDK, OpenAI-compatible clients, and JavaScript integrations. Standard REST uses `https://api.x.ai/v1/responses`; authorization is server-side Bearer authentication. A tool request returns `function_call` entries with `name`, JSON-string `arguments`, and `call_id`. The application validates and executes allowed functions, then returns `function_call_output` with the matching ID. [Function calling](https://docs.x.ai/developers/tools/function-calling)

Custom functions yield control to the application; built-in tools execute provider-side. Parallel tool requests are enabled by default and can be disabled. Tool schemas have object roots and up to350 tools are allowed, but an FYP tool menu should be much smaller. A function argument is a request, not authorization. [Function calling](https://docs.x.ai/developers/tools/function-calling)

The published [OpenAPI schema](https://docs.x.ai/openapi.json) was downloaded and inspected. Its `ModelTool` union includes function, web/X search, image generation, file search, code interpreter, MCP, shell, and tool search. A screenshot-click computer controller or Grok Bot lifecycle endpoint was not found. The presence of a local `shell` schema is not a hosted desktop, sandbox policy, or safe arbitrary-execution guarantee. Some schema prose is stale relative to its unions; verify the chosen adapter against the specific API before implementation.

**Original illustrative FYP tool definition, using the documented function-call shape:**

```json
{
  "type": "function",
  "name": "prepare_workspace_note",
  "description": "Prepare a note proposal for owner review; this tool does not write a file.",
  "parameters": {
    "type": "object",
    "properties": {
      "task_id": {"type": "string"},
      "title": {"type": "string", "maxLength": 120},
      "body": {"type": "string", "maxLength": 12000}
    },
    "required": ["task_id", "title", "body"],
    "additionalProperties": false
  }
}
```

Validate these limits in the application even if schema enforcement is also enabled. Return a proposal ID and `awaiting_approval`, never `completed`. Only a separate authenticated UI approval route can advance it.

### 3.2 Remote MCP

[Remote MCP](https://docs.x.ai/developers/tools/remote-mcp) supports Streaming HTTP and SSE, with `server_url`, `server_label`, selected tool names, authorization, and optional headers. xAI's API does **not** currently support the OpenAI-compatible `require_approval` or `connector_id` fields. Omitted or empty `allowed_tools` exposes all server tools. In the native SDK the corresponding selector is `allowed_tool_names`.

For FYP, do not expose direct robot movement or an unreviewed write tool through provider-executed MCP. Use a local function gateway that returns proposals, or an MCP service that itself enforces owner-approved grants. Explicitly enumerate tools. An authenticated MCP server still needs scope, replay protection, effect verification, and revocation handling. No localhost MCP should be made publicly reachable merely to match a provider example.

### 3.3 Voice session and interruption

The [Speech-to-Speech guide](https://docs.x.ai/developers/model-capabilities/audio/speech-to-speech) documents `wss://api.x.ai/v1/realtime?model=grok-voice-latest`, currently aliased to `grok-voice-think-fast-2.0`. Configure the session through `session.update`; choose a voice and a bounded instruction profile. It supports custom functions and provider-managed search/MCP. PCM defaults to24kHz, with separately configurable input/output and supported8–48kHz rates; JSON/base64 or binary transport is available. Its opt-in resumption replays transcripts, tool requests and results, expires after30 minutes idle, and requires the conversation ID and opt-in on reconnect. This is short session continuity, not long-term memory.

The [voice reference](https://docs.x.ai/developers/rest-api-reference/inference/voice) provides:

- Session creation/configuration acknowledgements
- `input_audio_buffer.append`, commit/clear and speech-start/stop notifications
- `response.output_audio.delta` and transcript events
- `response.function_call_arguments.done` for complete function requests
- `conversation.item.create` with `function_call_output` to return results
- `response.cancel`; VAD interruption is automatic, manual mode needs explicit cancellation
- `conversation.item.truncate` and its acknowledgement to remove the unheard assistant audio tail
- Response-completion and error events

Do not implement interruption as merely stopping the loudspeaker. Stop/flush local playback, invalidate stale voice-turn output, and reconcile the provider conversation to what was actually heard. Do not interpret response cancellation as cancellation of an already approved persistent job. Application job cancellation needs its own state transition and executor acknowledgement.

The published guide's voice instructions and runtime schemas should be treated as separate: a prompt cannot improve actual echo cancellation, clock drift, jitter buffering, or microphone permission behavior. [Prompting guide](https://docs.x.ai/developers/model-capabilities/audio/speech-to-speech/prompting-guide) explicitly separates persona/wording from acoustic voice configuration, and even describes a stronger text model supplying content for a realtime responder. This supports a coherent voice-plus-worker design; it does not require exposing two personalities.

### 3.4 Authentication and data

[Ephemeral tokens](https://docs.x.ai/developers/model-capabilities/audio/ephemeral-tokens) are minted server-side through `POST /v1/realtime/client_secrets`; the documented example requests `expires_after.seconds=300`. Browser authentication uses the `xai-client-secret.` WebSocket subprotocol. `session` and `expires_after.anchor` are not supported by that mint endpoint. Do not put the permanent key in browser, mobile, firmware, logs, or a distributable package.

For FYP, the existing backend voice proxy may be preferable: it keeps tool execution and policy on the host. A direct browser connection would need an authenticated token-mint endpoint, tight rate limits and application-owned authorization regardless of model session configuration. Do not assume an ephemeral token is a per-tool grant.

[Responses reference](https://docs.x.ai/developers/rest-api-reference/inference/responses) and OpenAPI describe stored responses retained for30 days and `store=true` by default. Choose retention explicitly; it is not consent to export all personal memory. API data policy is separate from Grok Bot's Cursor product policy. Review [API data and privacy](https://docs.x.ai/developers/faq/security) before a real deployment, especially recordings, personal calendars, and screenshots.

### 3.5 Background work: four different mechanisms

| Mechanism | Actual documented meaning | Consequence |
|---|---|---|
| Async Python client | Concurrent outstanding API calls within your process [Async](https://docs.x.ai/developers/advanced-api-usage/async) | Process death still needs application recovery |
| Responses `background` | Explicitly unsupported in current `ModelRequest` schema [OpenAPI](https://docs.x.ai/openapi.json) | Do not port OpenAI background behavior by changing base URL |
| Deferred chat completion | Obtain request ID, poll;202 means pending; result retrievable once within24 hours [Deferred](https://docs.x.ai/developers/advanced-api-usage/deferred-chat-completions) | This is deferred inference, not scheduled automation or a durable multi-tool job |
| Grok Bot routine | Product-level scheduled/event work on its cloud computer [Skills](https://docs.x.ai/grok-bot/skills-routines-and-automations) | Reimplement the scheduler/job state machine in FYP |

[Responses WebSocket mode](https://docs.x.ai/developers/advanced-api-usage/websocket-mode) is another transport, separate from realtime audio. It serializes turns on a connection; concurrent work needs separate connections. Connections last at most25 minutes. An in-memory previous-response cache supports `store=false`, but disconnect or eviction requires full context replay when no stored fallback exists. Neither a long-lived socket nor an opaque [compaction item](https://docs.x.ai/developers/advanced-api-usage/context-compaction) is a task database. Compaction can reduce context cost, but it must fit the model window before compaction and its opaque output must remain unchanged.

### 3.6 Multi-agent model is not a Bot fleet

The [multi-agent model](https://docs.x.ai/developers/model-capabilities/text/multi-agent) is a beta research capability with4- or16-agent configurations. Only leader output/tool activity is normally exposed; the subagent context is encrypted. It does not support client-side/custom tools, Chat Completions, or `max_tokens`; built-in tools and remote MCP are supported. All contributing agents' tokens/tools are billed.

It is a poor default for this FYP's device and local-operation kernel: opaque subagents do not solve application authorization, cancellation or effect verification, and cannot directly reuse the current client-side function tools. A simple visible coordinator plus an independently bounded text worker is easier to evaluate.

## 4. Proposed FYP architecture and lifecycle contracts

Everything in this section is an engineering recommendation inferred from the needs and observable product capabilities, **not a description of Grok Bot's private architecture**.

### 4.1 Keep the current modular monolith; introduce contracts before frameworks

FYP's [architecture document](https://github.com/tantalum666/FYP/blob/50e174f50a4130b3c666f836f666f6aa4cde4b32/desk-companion/docs/architecture.md) already describes a single FastAPI host, SQLite, typed tool proposals, owner approval, durable jobs, a restricted note executor, independent receipts, and nonblocking voice dispatch. Preserve these tested boundaries. Current documentation does not establish generic GUI control, robust long-term memory, deployed RIG control, real provider performance, or target-Pi benchmarks as completed.

Suggested ownership:

1. **Interaction layer:** web/Mac preview, Pi screen, microphone/speaker; one canonical conversation and personality
2. **Session adapter:** provider-specific audio/text events; bounded queues, turn epochs, audio playback and reconnect logic
3. **Assistant coordinator:** decides whether to answer, retrieve, prepare a proposal, or create a durable job; cannot write privileged state directly
4. **Deterministic task core:** jobs, approvals, schedules, events, budget, version checks, idempotency, cancellation, audit
5. **Bounded workers/adapters:** notes/files, one approved browser workspace, selected connectors, hardware gateway
6. **Verification and memory:** receipts establish facts; memory stores supported durable observations, not unverified worker claims

The always-on host owns jobs. Closing a web preview should not cancel them. Turning off that host does stop execution; show this honestly. A cloud host is optional infrastructure later, not necessary to demonstrate the architecture.

Latest project constraints from the pinned product contract: A1 is the accepted assistant identity; the current page companion is the intact2D artwork after rejected segmented/2.5D/3D experiments. Keep its current rendering and interaction while connecting truthful assistant states. Do not reintroduce discarded visuals. Its working personality is quiet, perceptive and reliable, with light humor as familiarity develops; exact voice, default outfit and final name remain open. These are project requirements, not Grok-derived design choices.

### 4.2 Contract A: stable event envelope

Every internal event needs `event_id`, `event_type`, `occurred_at`, `source`, `actor_id`, `conversation_id`, `task_id`, `job_id`, `correlation_id`, `causation_id`, `schema_version`, and a typed payload. Include an idempotency key for externally replayable inputs. Never place credentials in payloads. Use an append-only audit record plus materialized current state in one SQLite transaction.

Sources distinguish owner text/voice, authenticated external events, scheduler, worker, and sensor. Webpage/email/tool content is untrusted data and cannot become owner approval by being quoted. Route all results through the coordinator's single user-facing narrative stream; each result carries provenance and confidence.

### 4.3 Contract B: durable job

Continue the current states: `review → queued → running → verifying → succeeded`, with `failed`, `cancel_requested`, `cancelled`, `expired`, and `unknown` branches. Add any planning state only when it has a clear stored transition.

Required fields: immutable intent, intent hash, task/source version, operation type, permitted adapter, target environment, scoped resources, risk class, creation/expiry/deadline, attempt, dedupe key, execution token, result reference, and verification status. A future distributed implementation also needs lease owner, expiry, heartbeat, and fencing token; do not pretend the current single process already provides distributed leases.

Rules:

- Persist before acknowledging acceptance; acceptance is not completion
- Approve the exact version/hash, then recheck scope and source versions immediately before dispatch
- Only retry a write when the adapter can prove no effect occurred or enforces idempotency
- On ambiguous write/network loss/crash, set `unknown`; reconcile through readback
- Late verified success may be real even after cancellation request; report both history and final effect
- Job success does not automatically mark the user's broader task complete
- Tool timeout, API response completion, and worker-process exit do not establish external success

### 4.4 Contract C: approval gate

Bind owner approval to `proposal_id + version + canonical_action_hash + target + scope + expiry`. Store who approved, the displayed summary, and the actual action parameters. Changing recipient, content, path, hardware preset, or environment invalidates the grant. Do not expose an approval-confirm function to the model. Unknown action categories default to denied or review-required.

Prefer an explicit preview with operation, effect, data destination, and reversibility. Natural-language remembered rules can produce candidate structured rules, but only the owner can activate them and the deterministic policy must enforce the resulting scope. An optional model reviewer may escalate or reject; it cannot grant broader access.

### 4.5 Contract D: responsive voice with durable workers

A voice session has a unique session ID, turn sequence, output epoch, provider call IDs, current playback item and played-audio duration. Keep microphone receive, provider receive, bounded tool dispatch and playback separate. Never block receiving a new utterance on a long computer job.

A preparation tool should respond quickly with a proposal/job ID and truthful state. The coordinator later announces milestones and verified results through the same persona. For a barge-in, flush audio and invalidate pending output from the old turn; cancel unapproved proposals created by that turn. An approved job continues unless the user actually requests its cancellation. A voice disconnect is not implied withdrawal of an approved job.

Reconnect uses a new provider session plus an approved concise summary and canonical job facts; do not replay stale write requests. Disable repeating idle-check-in behavior by default. Test one-turn cancellation, response/tool races, disconnect during approval, duplicated tool IDs, and job completion during a new conversation.

### 4.6 Contract E: routines and external events

A routine records owner, timezone, cadence, next occurrence, allowed skill/version, source filters, output channel, policy, max runtime/cost and enabled state. Persist `(routine_id, occurrence_time)` before starting work to prevent duplicate execution after restart. Define missed-run policy explicitly: skip, coalesce or catch up. Avoid overlapping execution by default.

Webhook input needs source authentication, bounded payload, replay detection, timestamp validity and narrow matching. Provider success acknowledgement should follow durable ingestion, not job completion. A routine test executes real work unless the adapter has a true dry-run mode. Auto-pause repeated authentication failures and surface the blocker; never silently substitute stale input.

### 4.7 Contract F: connector and computer lifecycle

Connector states: `unconfigured → authorizing → connected → degraded/revoked/disconnected`. Store scope, owner, identity and last verified read separately from secret material. Test revocation; do not silently change account or fallback from a denied API action to browser automation.

Executor states: `offline → connecting → ready → busy → recovering/blocked`. Before any job, verify the selected environment, allowed domains/paths, authenticated account, and adapter capability. A GUI lease prevents simultaneous mouse/keyboard control. Preview/observer access is distinct from control. Human login handoff pauses the job and resumes only after a fresh observed state check.

MVP operations should be narrow: read a chosen workspace; generate a new file in an approved folder; search approved public sources; prepare a draft in a controlled demo app. Add general desktop clicking only after sandbox, takeover, state observation, cancellation and verification have separate tests. Screenshots and visible DOM text can contain prompt injection or secrets; minimize what goes to a provider.

### 4.8 Contract G: hardware gateway

Model tools propose a named preset or request status/stop. The host gateway checks owner grant, device identity, connection freshness, preset allowlist, expiry, dedupe key and current safety state. Device firmware must enforce timeouts and a safe state locally. Physical stop bypasses conversation and model queues.

Report distinct stages: `requested`, `accepted_by_gateway`, `accepted_by_device`, `executing`, `completed_verified`, `failed`, or `unknown`. A serial/network acknowledgement is not motion completion, and an open-loop servo duration is not position evidence. RIG arm and ESP32 cleaner should have independent adapters and independent stop behavior. This is FYP safety design, not a capability supplied by xAI.

## 5. Quotas, cost, and scope recommendation

### Product limits worth understanding

- Bot routines: up to50 per Bot, at least5 minutes between scheduled runs,20 recent run records retained [Skills](https://docs.x.ai/grok-bot/skills-routines-and-automations)
- Desktop attachments: up to6 at once;25MB documents/images/audio and200MB video [Files](https://docs.x.ai/grok-bot/files-and-results)
- Personal rules and local-computer execution policy can be desktop-specific; timezone affects routines [Settings](https://docs.x.ai/grok-bot/settings-and-notifications)
- Included Bot usage resets weekly. Current Cursor billing describes an on-demand monthly limit that can be exceeded by a run already in progress; do not confuse this with a hard FYP budget limit [Billing](https://cursor.com/help/grok-bot/plans)

These are product constraints, not recommended FYP configuration values. Billing/availability can change; inspect the actual account before spending.

### API cost snapshot, USD

[Current pricing](https://docs.x.ai/developers/pricing): Grok4.7 below the long-context threshold is $2/M input, $0.50/M cached input, $6/M output; long-context prices increase. Search/code tools add invocation charges. Speech-to-Speech is $0.08/minute plus $0.004 per text-input event. [Voice pricing](https://docs.x.ai/developers/models/speech-to-speech) says server-VAD sessions are billed for connected duration, while push-to-talk is billed for audio sent and received; function results are exempt from the text-event charge. Maximum voice session duration is120 minutes. [Rate limits](https://docs.x.ai/developers/rate-limits) list voice concurrent-session tiers10/20/50/100/200; account-specific limits prevail.

Illustrative arithmetic:20 connected voice minutes/day over30 days is $48 in audio before text events, worker inference, search, taxes or infrastructure.24/7 connected VAD at this rate would be $3,456 per30-day month. Therefore “always available” should mean a local wake mechanism and persistent task service, not an always-billed open realtime stream. This is a cost calculation, not an estimate of the user's actual usage.

### Recommended three-person FYP slice

**Implement first:** one assistant identity; text/voice with interruption; owner-visible proposals; durable approved note/computer jobs; task progress; explicit memory correction; a simple scheduler; one bounded hardware preset adapter; a deterministic stop; evidence-based completion.

**Add after tests:** source-linked personal memory retrieval, one real read-only connector, constrained browser preview/execution, a worker for longer reasoning, and authenticated narrow event triggers.

**Defer:** a market of autonomous agents, arbitrary computer access, own cloud VM fleet, team/shared credential infrastructure, public social ingress, learned workflow recording, and opaque16-agent research. They add large safety and evaluation scope without proving the core contribution.

**Provider choice stays open.** Compare xAI voice to the existing Qwen/Gemini adapters using Chinese/English task utterances, noise/echo, barge-in, tool call accuracy, median/P95 first-audio latency, job progress while speaking, disconnect recovery and cost. Public documentation is not a quality benchmark. Do not replace the current provider abstraction solely to resemble Grok Bot's brand.

## 6. Verification plan and stopping conditions

A demonstrable prototype should pass these black-box cases:

1. Speak while a5-second worker job runs; voice remains interactive and reports a job ID
2. Interrupt speech; no old audio resumes and an unapproved stale proposal cannot execute
3. Change action arguments after preview; previous approval is rejected
4. Duplicate an input event/tool call; exactly one permitted effect occurs
5. Lose the network after a write; state becomes unknown until independent readback resolves it
6. Restart host mid-job; never blindly repeat an ambiguous write or old physical command
7. Close/reopen the UI; durable job/result history is retained
8. Revoke connector access; the job becomes blocked and does not switch identity
9. Inject hostile instructions in a webpage/tool result; it cannot create approval or extend scope
10. Trigger the same routine occurrence twice; one job is created
11. Disable or exceed a per-job budget; no new expensive step starts
12. Press physical stop or lose device heartbeat; output reaches locally enforced safe state
13. Ask what the assistant remembers; inspect/correct a fact and verify future retrieval changes
14. Complete a hardware command without feedback; the UI does not label it physically verified

Report simulated tests, public-schema checks, real API tests, browser tests and hardware measurements separately. No real-service or hardware result was established during this research.

## 7. Coverage and reproducibility

Reviewed primary sources are cited at the claims above. Public docs were fetched directly over HTTPS without login. The machine-readable manifest records source URL, final URL, HTTP200, retrieval date, byte length and SHA256 for47 pages. All47 fetches succeeded. Downloading does not mean every unrelated section was analyzed equally.

Core product coverage: overview; getting started; Bot identity/memory/template lifecycle; collaboration/voice/handoff; computer/apps; skills/routines/events; approval/privacy; security and security FAQ; settings; files/results; team Bots; computer recreate/termination; troubleshooting; tag-on-X. Enterprise SSO, proxies, private networks and managed setup were captured and checked for relevant boundaries, not converted into an FYP enterprise deployment specification. Mobile and use-case pages were captured for platform context.

Core API coverage: quickstart; tool overview/function calling/advanced usage; remote MCP; code execution; voice overview, realtime guide, prompting, ephemeral auth and event reference; models/pricing/rate limits; Responses schema/reference; async, deferred requests and text WebSocket lifecycle; compaction; research multi-agent limitations; data/privacy. Public web/X search and streaming pages were captured as supporting integration references. Image/video generation and telephony are outside the chosen FYP scope.

Additional canonical entry points:

- Documentation index: https://docs.x.ai/llms.txt
- Machine-readable API schema: https://docs.x.ai/openapi.json
- Official Python SDK: https://github.com/xai-org/xai-sdk-python (linked from xAI docs; not source-audited here)
- Official voice examples: follow the tester-app links in https://docs.x.ai/developers/model-capabilities/audio/speech-to-speech (not executed here)

Known evidence limits: no live Bot use, latency measurement, SDK install, API compatibility test, pricing-console check, actual model-selection observation, or robot validation. Some public API schema prose and guides contain compatibility caveats; adopt only the verified subset and add contract tests before use. The conclusions about undisclosed internals remain explicitly qualified.
