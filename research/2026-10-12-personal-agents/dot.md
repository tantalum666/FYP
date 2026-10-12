# OpenAI dot and reusable agent primitives: clean-room FYP research

Research date: 12 October 2026 (UTC). Scope: official, publicly accessible OpenAI product and developer documentation. No private assistant instructions, private operational records, or unpublished implementation details are used as evidence of product architecture. No paid model call, purchase, credential creation, OAuth grant, installation, or live computer-control experiment was performed.

## 1. Decision summary

**Recommended FYP direction (engineering inference):** retain the project's own deterministic identity, calendar, task, approval, execution, and verification core. Add a replaceable agent backend and voice frontend. Evaluate the current OpenAI Agents API as one backend option, alongside the Agents SDK/Responses route. Use a narrow function interface for business writes and keep actual approval outside the model. Start computer use with an isolated test application and independently verified results. Do not attempt to reproduce all of dot or make a continuously open voice connection the definition of persistence.

**A material update to older comparisons:** the current official documentation now describes a managed **Agents API**, not merely the earlier open-source Agents SDK. It exposes durable sessions with a managed Codex harness, tools, compaction, optional sandboxes, and multi-agent support. This is a reusable developer API. It is distinct from the finished dot product. [Agents API](https://developers.openai.com/api/docs/guides/agents-api/overview), [runtime comparison](https://developers.openai.com/api/docs/guides/agents#compare-agent-runtimes).

**Public API boundary:** I found no dot-specific public API in the inspected dot documentation, its linked developer navigation, or the OpenAI API documentation index. This is an evidence-limited finding, not proof that no private/partner interface exists. Do not invent dot endpoints or assume that a dot subscription exposes its memory, schedules, credentials, or computers to FYP. The documented embedding primitives are generic OpenAI APIs. [dot documentation](https://learn.chatgpt.com/docs/dots), [API index](https://developers.openai.com/api/docs/llms.txt).

## 2. What dot publicly promises, and what remains unspecified

Labels: **Fact** means expressly documented; **inference** means our design conclusion; **unknown** means not established by reviewed public material.

### Product behavior

- **Fact:** dot is an ongoing cloud agent with its own computer/browser. It can keep working while the user's computer is off, accept conversation while other work proceeds, and bring back results or decisions. The overview currently identifies GPT-6 Astra as its underlying model. **Unknown:** the complete production architecture, hidden state schemas, orchestration implementation, and exact system prompts. These are unnecessary for a clean-room implementation. [Meet dots](https://learn.chatgpt.com/docs/dots).
- **Fact:** users can give multiple responsibilities, modify priorities, request fixed schedules with a timezone/end date, or use supported source events. Connections for apps, messaging, and a personal computer are separate. **Inference:** FYP should represent these as separate permissions and capabilities rather than a single “connected” switch. [Getting started](https://learn.chatgpt.com/docs/dots/getting-started).
- **Fact:** dot can divide work into parallel background tasks and separate visible threads, and can use a previously configured coding environment. A task has its own supplied context; it does not automatically receive all conversation history. Product documentation warns that a completed run does not prove the requested result was achieved. [Tasks and memory](https://learn.chatgpt.com/docs/dots/tasks-and-memory).
- **Fact:** calls, ChatGPT, Slack, and Teams reach the same dot but maintain distinct visible conversations. Calling is user-initiated; dot-initiated calls are described as planned, and texting as coming soon. A call ending does not necessarily stop assigned work. **Unknown:** a public dot telephony API or a guarantee of autonomous outbound calling. [Messaging](https://learn.chatgpt.com/docs/dots/channels).

### Memory, proactive work, and controls

- **Fact:** dot combines current context, relevant ChatGPT memory, and its own saved notes; notes are not a complete transcript. Selected voice context can differ from background-task context. Cross-channel context use does not authorize disclosure to another audience. Background research itself is read-only; follow-up actions remain subject to permissions. **Inference:** FYP needs provenance and audience restrictions for memory independently of conversation transport. [Tasks and memory](https://learn.chatgpt.com/docs/dots/tasks-and-memory#context-and-memory).
- **Fact:** the product distinguishes automatic action review, user instructions, custom rules, and app permissions. Rules do not remove built-in safeguards or grant app access. Pause stops current main work; delegated work and schedules require separate stopping. Stopping cannot undo completed actions. **Inference:** make stop scopes explicit in FYP and avoid an ambiguous “Stop everything” UI unless it actually traverses children and schedules. [Controls](https://learn.chatgpt.com/docs/dots/controls).
- **Fact:** cloud browser sessions are separate from personal browser sessions. Website sign-in can be completed through a private form or takeover. Optional saved credentials are distinct from an active login session. A connected personal computer must be online with its app open; only one personal computer is supported at a time in the product documentation. These are **product limits**, not blanket limits of all developer APIs. [Computers and apps](https://learn.chatgpt.com/docs/dots/computers-and-apps).
- **Fact:** product event-triggered tasks currently document Gmail incoming messages, selected Slack-channel new messages, and GitHub PR activity. Slack reactions/edits/deletes/DMs are excluded. One task cannot combine time schedules with event triggers; availability depends on plan/surface/workspace. This is not a generic webhook API for FYP. **Inference:** implement FYP triggers through explicitly supported adapters and its own scheduler. [Scheduled tasks](https://learn.chatgpt.com/docs/automations#trigger-tasks-from-app-events).

### Product availability and limits

The overview currently lists a gradual rollout to Pro 100/200/500 adults outside EEA/UK/Switzerland, Business Premium worldwide, and Enterprise worldwide with administrator enablement. dot conversations have a different usage treatment from Work/Codex tasks it starts. These entitlements are not developer API credit or access. The October 5–9 release adds mobile setup and improved coordination with existing Codex threads/automations. Availability must be rechecked rather than copied as a permanent requirement. [Access](https://learn.chatgpt.com/docs/dots#access), [October update](https://learn.chatgpt.com/docs/whats-new/dots-october-9-2026).

## 3. Runtime choices that FYP can actually integrate

| Route | Public contract | Best FYP use | What FYP still owns |
|---|---|---|---|
| Agents API | Managed Codex harness and durable sessions | Optional long-running research/planning worker | Identity, authority, task semantics, external action receipts, adapter lifecycle, application UX |
| Agents SDK | Agent loop in the application; tools, handoffs, approvals, resumable state | Strong default when existing FastAPI services and deterministic tools are central | Hosting, storage policy, background scheduling, execution isolation, all business correctness |
| Responses API | Direct model/tool interface, optional hosted tools and orchestration | Small explicit planner/tool loop or provider-neutral adapter | Tool execution, persistence choices, jobs, retries, approvals, verification |
| GPT-Live | Full-duplex voice with backend delegation | Optional natural voice frontend over the same task core | Permissions, confirmed business state, task continuation/cancellation, delivery verification |
| Realtime API | Speech-to-speech event protocol with functions/MCP | Alternative direct voice/tool integration | Playback handling, tool safety, durable tasks, context restoration |

The runtime comparison explicitly distinguishes Agents API sessions, SDK sessions, Responses conversations, and sandboxes. Do not store one ID as if it names all four. [Runtime comparison](https://developers.openai.com/api/docs/guides/agents).

### Agents API: useful capabilities and hard boundaries

**Configuration and environment.** An agent declares model/instructions/tools; a session holds work. Environments can be none, OpenAI-hosted, or self-hosted. Without an environment, remote MCP/function tools remain possible but no built-in shell/workspace exists. An application handles function calls; simply attaching an environment does not run those functions there. Current SDK examples use beta namespaces and `OpenAI-Beta: agents=v1`. Keys need appropriate Agents and Responses scopes. No keys were created in this research. [Architecture](https://developers.openai.com/api/docs/guides/agents-api/architecture), [quickstart](https://developers.openai.com/api/docs/guides/agents-api/quickstart), [functions](https://developers.openai.com/api/docs/guides/agents-api/tools/functions).

**Lifecycle.** A message to an idle session begins a turn; input during active work steers it. Save an idempotency key per logical input before sending and reuse it only for that same submission. Track completed/failed/cancelled turn outcomes separately from session idle. Cancelling a turn preserves session history. Streams are not a replay log. [Run and continue sessions](https://developers.openai.com/api/docs/guides/agents-api/sessions).

**Recovery.** After disconnection: subscribe and buffer events, fetch saved session/items, restore by item ID, then merge live updates. Rebuild pending forms from current `required_actions`, not historical requests. Text deltas may be absent; the complete text event replaces the relevant accumulated part. Paginate saved history. **Inference:** this maps naturally to an application event reducer with an authoritative snapshot refresh, not append-only UI guesses. [Events and items](https://developers.openai.com/api/docs/guides/agents-api/sessions/events).

**Webhooks.** Session webhooks include created, action_required, in_progress, idle, and failed. Notice the naming difference: webhook `agent.session.action_required`, stream `agent.session.requires_action`. Retrieve the current session for actionable details. Verify signatures, durably enqueue work before acknowledging, and deduplicate webhook IDs. OpenAI retries delivery up to 72 hours; duplicates can occur. These events do not certify external business success. [Session webhooks](https://developers.openai.com/api/docs/guides/agents-api/sessions/webhooks), [webhook delivery](https://developers.openai.com/api/docs/guides/webhooks).

**Important durability limitation.** Self-hosted environment connection waits are up to five minutes. This is not a durable pending-input queue; late connection does not replay timed-out input. Mid-turn disconnect may fail a tool without automatically reconnecting or restarting the command. Environment IDs do not restore replacement-machine files. Session deletion does not stop provider compute. **Inference:** keep the FYP outbox, execution ledger, reconciliation, and explicit cleanup even with managed sessions. [Sandbox lifecycle](https://developers.openai.com/api/docs/guides/agents-api/environments/lifecycle).

**Tools and recovery.** Function results use pending turn ID/call ID. Store a side-effecting call's outcome durably; after uncertainty inspect the actual target before executing again. MCP can connect from OpenAI over HTTP or from an environment over HTTP/stdio. Limit allowed tools and set required startup where a missing tool should fail the turn. Credentials and network reachability differ by connection origin. [Function recovery](https://developers.openai.com/api/docs/guides/agents-api/tools/functions#recover-after-a-disconnect), [MCP connections](https://developers.openai.com/api/docs/guides/agents-api/tools/mcp).

**Delegation caveat.** Agents API subagents inherit MCP tools/credentials and share an environment filesystem; they do not support application function tools. Default maximum concurrent subagents is six excluding the coordinator. Separate contexts are not separate security boundaries. By contrast, Responses multi-agent has a different contract: beta, model-specific support, default concurrency three, and client functions may originate from any agent. Do not mix their event schemas or assumptions. [Agents API multi-agent](https://developers.openai.com/api/docs/guides/agents-api/multi-agent), [Responses multi-agent](https://developers.openai.com/api/docs/guides/responses-multi-agent).

**Resource limits.** The managed API documents roughly 4 MiB request/configuration/tool-result boundaries. Hosted small/medium/large sandboxes are 1/4/16 GB with 1/2/4 vCPUs. Restricted networking accepts 1–100 exact hosts; hosted stdio MCP currently requires enabled networking. Hosted workspaces may expire after an hour without activity/keep-alives. Published artifacts survive environment expiration; self-hosted outputs are not automatically published through that Artifacts API. [Configuration](https://developers.openai.com/api/docs/guides/agents-api/configuration), [hosted environments](https://developers.openai.com/api/docs/guides/agents-api/environments/openai-hosted), [files](https://developers.openai.com/api/docs/guides/agents-api/environments/files).

### SDK and Responses: still valid, often simpler for this project

SDK approval interruptions return resumable state. Serialize that state for delayed review and resume the same run, rather than submitting approval as an unrelated fresh turn. Agent input/output guardrails do not wrap every intermediate tool; put enforcement on the side-effecting tool itself. SDK/Responses applications do not automatically inherit the finished product's approval system. [SDK running](https://developers.openai.com/api/docs/guides/agents/running-agents), [guardrails and approvals](https://developers.openai.com/api/docs/guides/agents/guardrails-approvals), [result state](https://developers.openai.com/api/docs/guides/agents/results).

Responses can use application history, response chaining, or a durable Conversations object. Conversation persistence is not a personalized memory policy. All prior chain input can remain billable. Background mode makes a response asynchronous, with polling/cancellation and resumable streaming when originally requested, but it is not the project scheduler. Async function calls are another separate feature: application jobs run outside OpenAI while the model continues; result matching still uses the original call ID. Current async support is model-specific and excludes hosted built-in tools/programmatic tool calling; multi-agent combinations have restrictions. [Conversation state](https://developers.openai.com/api/docs/guides/conversation-state), [background](https://developers.openai.com/api/docs/guides/background), [async tools](https://developers.openai.com/api/docs/guides/async-tool-calling).

The old Assistants API is documented as sunset on 26 August 2026. A new FYP implementation should not follow archived tutorials built around Assistant/Thread/Run objects. [Migration](https://developers.openai.com/api/docs/assistants/migration).

## 4. Voice: a frontend for persistent work

**GPT-Live facts.** It supports simultaneous listening/speaking and separates voice from backend reasoning. Client delegation can call the project's existing backend, including non-OpenAI services. Responses delegation handles context/connection management but supports a subset of standalone Responses configuration. Either way, the application owns permissions and task state. **Recommendation:** prototype client delegation if OpenAI voice is selected, because FYP already has an authoritative tool/approval/job layer and needs to filter stale results before they are spoken. [GPT-Live](https://developers.openai.com/api/docs/guides/live).

For client delegation, a delegation-created event identifies the delegation but does not contain task text. Maintain timestamped input/output transcripts and application state. A fragment is not a full user turn. Return concise results tied to the delegation; progress, speech-directed commentary, and instructions are different events. An append acknowledgment is not proof of audio delivery, and interrupting speech does not cancel backend work. Assign application operation IDs/task revisions in addition to delegation IDs. [Delegation](https://developers.openai.com/api/docs/guides/live-delegation).

Long voice context is summarized and can omit details; keep confirmed records in the application. Close idle sessions and rehydrate relevant text/task state on reconnect. Optional stored-session forking requires storage enablement and a completed recording; recordings are available for 30 days, and ZDR disables forking. Graceful close requires waiting for `session.closed`; otherwise final usage remains unconfirmed. **Unknown:** observed Cantonese quality, mixed-language quality, actual Pi latency, and acoustic echo cancellation in the intended hardware. [Live sessions](https://developers.openai.com/api/docs/guides/live-conversations).

Realtime is a different protocol, with a documented 60-minute maximum session. For WebSocket interruption the application must stop playback and truncate unplayed output; WebRTC/SIP handle more of that automatically. Server and semantic VAD offer different turn-ending behavior. These do not remove the need for application-level cancellation. [Realtime conversations](https://developers.openai.com/api/docs/guides/realtime-conversations), [VAD](https://developers.openai.com/api/docs/guides/realtime-vad).

Realtime functions execute in the application; remote MCP executes through OpenAI and has a separate approval lifecycle. A response can finish before MCP calls finish; follow-up response creation is application-controlled. Legacy `connector_id` is deprecated for models released after 1 September 2026. Do not build new Google Calendar integration around an old connector example without checking model compatibility; use the project's business adapter or a supported MCP server. [Realtime tools](https://developers.openai.com/api/docs/guides/realtime-mcp).

## 5. Computer use and permission enforcement

Public developer docs offer two substantially different paths:

1. **Managed hosted browser:** Agents API `computer_use` with an OpenAI-hosted desktop. Each new origin requires approval, and dedicated authentication requests keep entered credentials outside model input. The guide explicitly warns that origin approval does **not** enforce action-by-action confirmation for purchases or destructive writes. Authentication currently excludes passkeys and QR sign-in. No general local-desktop equivalence should be inferred. [Managed browser](https://developers.openai.com/api/docs/guides/agents-api/tools/computer-use).
2. **Runtime controlled by FYP:** Responses computer actions or code-execution tools over a browser/desktop environment supplied by the application. OpenAI recommends code execution for GPT-6 Astra, but the execution service, persistence, permission checks, and limits belong to the application. Continuing API context does not restore browser state. A model-generated call marked completed still needs execution and verification. [Computer-use guide](https://developers.openai.com/api/docs/guides/tools-computer-use).

**FYP design inference:** use API-level tools first, a controlled browser fixture second, and unrestricted desktop control only after an actual enforceable sandbox exists. A prompt asking the model to request approval is insufficient if the same model can reach the write through another tool. Approval must be checked in the execution broker, with no alternate free shell/browser path to the target. Separate workload environments, minimal network hosts, and credential brokering are documented recommended controls. [Sandbox security](https://developers.openai.com/api/docs/guides/agents-api/environments/security).

An environment key is deliberately more limited than an application key but may still be readable by generated code. No secrets should be placed in repository files or model-visible results. MCP is a transport/tool interface, not automatically an authorization policy, job queue, successful-action proof, or persistence guarantee. [Self-hosted authentication](https://developers.openai.com/api/docs/guides/agents-api/environments/self-hosted#authentication), [MCP connections](https://developers.openai.com/api/docs/guides/agents-api/tools/mcp).

## 6. Implementable FYP architecture (our proposal, not a claim about dot internals)

Keep the existing FastAPI/SQLite single-service prototype and evolve these boundaries:

1. **Ingress:** touchscreen/web/mobile/voice normalize owner, channel, message, and task correlation. A new voice session does not create a new owner or task.
2. **Context builder:** selects recent conversation, verified task facts, calendar state, relevant permitted memories, tool capabilities, and current revision. Excludes credentials, unrelated private material, revoked permissions, and obsolete instructions.
3. **Planner adapter:** Responses, SDK, Agents API, or another provider produces proposals and read requests. It never calls the owner approval endpoint.
4. **Policy/approval service:** validates target, operation type, exact arguments, source revision, expiry, user identity, and permitted data destination. Approval is represented by a server-issued immutable record, not model text saying “approved.”
5. **Durable job core:** accepts an operation once, commits it with an outbox entry, assigns a lease/fencing token, and tracks planned, awaiting approval, queued, running, waiting external, verifying, succeeded, failed, cancelled, or unknown outcome.
6. **Executors:** existing calendar/task services, a narrow paired-computer agent, a fixture browser, then a reviewed desktop adapter. Workers claim capabilities; they do not expand their authority from content seen on screen.
7. **Verifier:** reads target state independently and compares the approved intent. Screenshot, generated answer, provider turn completion, and an executor success flag are insufficient alone where a stronger check exists.
8. **Scheduler and event inbox:** owns due times, source cursors, timezones, recurrence end dates, source reauthorization, deduplication, stale-event rejection, retry policy, and notification suppression. Read-only research and writes use different capability sets.
9. **Memory service:** stores explicit/inferred preference status, source, timestamp, audience, expiry/supersession, and user correction/deletion. Keep authorization records separate from descriptive memory.
10. **Delivery and safety:** record verified facts before formatting them for speech/chat. Late voice results must match the current task revision. Hardware emergency stop, watchdog, limits, and power isolation remain local and independent of cloud reasoning.

Suggested persistent records: `agent_runs`, `input_outbox`, `external_call_ledger`, `approval_records`, `execution_events`, `source_cursors`, `memory_facts`, and `notification_deliveries`. Reuse existing tables/services where they already satisfy the contract; these names are conceptual, not a demand for a schema rewrite.

Suggested per-operation fields: owner/task/job IDs; task revision; logical operation ID; tool-call/provider IDs; target and normalized arguments hash; approval ID/scope/expiry; execution lease/cancellation generation; submitted/result timestamps; outcome certainty; external receipt; verification evidence; sanitized error; retry/reconciliation state.

### Three end-to-end demonstration scenarios

- **Calendar correction:** “Move tomorrow's study session to Thursday.” Resolve the exact occurrence/timezone, show the proposed change, obtain owner confirmation, write through the existing calendar service, independently fetch the event, and preserve provenance. Voice interruption before approval produces no write.
- **Actual computer task:** create specified Unicode content in an isolated test application/file location, using a paired executor with a scoped grant. Confirm exact content/destination and read back independently. Simulate a lost receipt after write and demonstrate reconciliation without a second write.
- **Ongoing responsibility:** monitor one approved source or scheduled fixture for a deadline change, update the same task, and notify only on a material change. Restart the application before the due check, show that the check persists, and demonstrate that cancelling the schedule prevents future runs without rewriting history.

These scenarios prove useful agent behavior with a realistic student scope. A generic cloud assistant that chats, remembers, and claims success without real authorized effects would fail the stated personal-agent requirement.

## 7. Acceptance tests and evidence requirements

All following are proposed FYP tests, not claims of completed validation:

| Area | Required test and passing evidence |
|---|---|
| Same assistant continuity | Start on voice, continue in web, reconnect voice; same owner/task/approved facts, no duplicate task |
| Durable submission | Kill process after database commit and before provider request; outbox restores one logical submission |
| Idempotency | Re-deliver the same input/webhook/tool call; one side effect and stable receipt; different content with same key rejected |
| Provider disconnect | Drop stream after action; restore session snapshot/history, do not repeat original task blindly |
| Unknown external write | Drop acknowledgment after target changed; state becomes unknown, independent read establishes outcome |
| Approval binding | Change target/content/task version after approval; execution is blocked until the new intent is reviewed |
| Model self-approval | Crafted tool call or retrieved text claims authorization; server refuses and target remains unchanged |
| Source injection | Page/email asks to ignore constraints, export data, or contact a third party; no authority expansion |
| Scope enforcement | Unauthorized path/origin/application rejected outside the model; independent target check proves no mutation |
| Cancellation race | Cancel before dispatch versus after submission; no false rollback claim, later steps stopped, true result retained |
| Voice race | Speak correction while tool runs; late obsolete result cannot overwrite newer task or be announced as current |
| Stop availability | Audio queues and ordinary tool quota saturated; stop control still reaches deterministic core |
| Memory correction | Correct/delete a fact; new contexts exclude superseded/deleted data; other audiences cannot retrieve it |
| Schedule correctness | Restart, timezone boundary, repeated event, cancellation, and expired auth; no missed/duplicate unintended action |
| Success criteria | Model turn completed with failed tool is not application success; independent verifier controls terminal result |
| Resource cleanup | End voice/session/job; no orphan execution lease or sandbox, and retained artifact remains accessible as intended |
| Cost exhaustion | Local budget/turn/tool limit stops new calls safely; no silent expensive retry loop |
| Privacy | Secrets absent from prompts/logs/artifacts; snapshots are minimized and only shown to authorized viewers |

Collect fixture input, approved intent, target version, event timeline, raw transport status, sanitized tool result, independent receipt, app state, and UI/speech delivery status. Report software-fixture success separately from real paid-model, real-device, and human-language tests. Run Mandarin, Cantonese, and mixed-language tasks under silence, speech overlap, ambient noise, and hardware noise before choosing the voice provider.

## 8. Cost, retention, and operational caveats

Current public standard short-context token rates per million tokens: GPT-6 Luna $0.10 input/$0.50 output; GPT-6.1 Sol $2/$10; GPT-6 Astra $10/$50. Cached input, cache writes, long-context rates, service tiers, reasoning output, tools, and retries can change totals. GPT-Live 1 is $0.05 per minute billed per second, plus backend usage. These are 12 October 2026 observations, not a quote or purchase authorization. [API pricing](https://developers.openai.com/api/docs/pricing), [GPT-Live model](https://developers.openai.com/api/docs/models/gpt-live-1).

At that voice rate, ten active minutes are $0.50 and an eight-hour open connection is $24 before backend costs (arithmetic, not a tested bill). Silence and backend waiting count as active GPT-Live session time; muting does not close it. WebRTC creation bills 15 seconds at initialization credited against running duration, so do not double-count it. Use measured final usage and cost per successfully verified task. [Voice cost guide](https://developers.openai.com/api/docs/guides/voice-latency-cost).

Agents API cost includes all root/subagent model calls and tool/sandbox charges. Usage counters are best effort, may be null/change, and do not expose every price-relevant cache-write count. Missing usage is not zero cost. Platform alerts differ from hard limits; hard enforcement is not instantaneous. Keep an application budget and bounded job/tool/turn counts as well. [Usage](https://developers.openai.com/api/docs/guides/agents-api/observability), [spend limits](https://developers.openai.com/api/docs/guides/spend-limits).

API data is not used for training by default, but “not trained on” is not “not retained.” The Agents API retains application state until deleted, is not ZDR-eligible, and currently documents US-only residency. Self-hosting the executor does not remove cloud-model/session retention. Conversations also retain state until deleted. GPT-Live optional stored recordings and ordinary abuse-monitoring retention are separate. FYP needs an explicit data map and deletion behavior for both its own database and external resources. [Data controls](https://developers.openai.com/api/docs/guides/your-data), [Agents API residency](https://developers.openai.com/api/docs/guides/agents-api/overview).

The Decisions API is a potentially inexpensive classifier/router, currently public beta with GPT-6 Luna, typed predicate/choice/score results and input-only pricing. Its probabilities are model estimates requiring calibration. It is optional; it should not decide user authorization or replace deterministic safety checks. [Decisions](https://developers.openai.com/api/docs/guides/decisions).

## 9. Realistic gaps and non-claims

Current implementation status must be established independently from the pinned FYP checkout and tests. This public-source report does not certify an existing implementation, real-device integration, or paid-service performance. The separate repository-reading ledger records which project documents were read for the implementation team.

Public documentation does not prove that the FYP account has access to the newest API/model, that an existing key has required scopes, that the intended school network permits connections, or that Raspberry Pi hardware meets latency and thermal goals. No source establishes that dot itself is embeddable, self-hostable, or automatically available through API billing.

A sensible minimum release includes unified task state, durable execution, scoped approvals, memory review/correction, one genuine controlled computer workflow, and a voice adapter proved against the same tools. Broad email/Slack/Teams integrations, arbitrary desktop automation, unconstrained autonomous outreach, all-provider support, and fully equivalent dot behavior are later expansions, not prerequisites for an honest FYP demonstration.

## 10. Documentation coverage and reproducibility

The official ChatGPT and API indexes and dot navigation were used to identify the pages. All six core dot guides were read in full. Relevant developer guides were read for substantive contract prose; repeated language-specific example blocks were not all reviewed line by line. Exact API field/event claims above were checked against the relevant examples or prose. This is architectural research, not executable SDK compatibility testing.

Core product pages reviewed: dot overview, getting started, messaging, tasks/memory, computers/apps, controls; also scheduled tasks, the DevDay release, and October mobile/coordination update. Enterprise/admin and general-memory pages were downloaded for reference but are not relied on for implementation details here.

Core developer pages reviewed: Agents runtime comparison; Agents API overview, quickstart, architecture, configuration, sessions, events/items, management, webhooks, functions, MCP, multi-agent, hosted/self-hosted environments, lifecycle, security, browser, files, errors and usage; SDK running, guardrails/approvals, results; Responses conversation state, background, async tools, multi-agent; GPT-Live getting started, delegation, sessions, model and voice-cost guides; Realtime tools, VAD, conversation lifecycle/interruption; Decisions; API pricing/spend limits and relevant retention sections.

Supplementary downloaded documentation (not a claim of full review): tracing, vaults, plugins, prewarming, broad deprecations, broad rate limits, and computer-use integration recipes. Provider-specific sandbox recipes were indexed but not downloaded or reviewed. These and all language-specific implementations require targeted review if adopted. Public source-cache files are research working material and should not be republished wholesale into the project; this synthesized report and direct source links are the deliverable.
