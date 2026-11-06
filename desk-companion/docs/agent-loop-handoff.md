# Group 2 · Agent loop handoff

28 October 2026. Current integration of Grok PRs20–59 and the Alice/mobile/Omni baseline in #60. Publication state belongs to the [root handoff](../../handoff.md); this module note does not claim deployment or live-provider acceptance.

## Current implementation

- HTTP text uses AgentLoop with three steps, a45-second between-step budget and per-tool limits. Realtime voice keeps its existing protocol/turn lifecycle and uses the same execute_tool policy; it does not start a second HTTP model loop.
- Registered tools only read, prepare drafts, cancel or request software stop. There is no model confirmation tool. Pydantic validation preserves omitted fields so a calendar move cannot erase unmentioned metadata.
- Durable effect receipts prevent repeated drafts/cancels/stops. Read tools always query current state. Late unapproved drafts are discarded after timeout; a thread timeout is not a forced rollback.
- Qwen/Gemini text streaming uses the shared SSE contract; fake demonstration works without network. Each actual network fallback consumes a separate daily attempt. Partial streams without a terminal receipt retain the same operation key for explicit recovery.
- Short-term text is a view of the existing login/task-scoped RAM Conversations, never a global SQL transcript table. Paired/local-agent channels do not acquire owner replay history. Memory revisions invalidate replay. A known owner business receipt can be recovered after reauthentication without replaying the old chat.
- Memory facts, deterministic profile/goals/aliases, contextual search and bounded plans remain distinct from temporary conversation. Goal drafts retain owner gates on list and decision.
- Audit is owner-only and reachable through the assistant's More menu. Read-result caches do not reintroduce forgotten facts.

## 31 October persistent application continuation

The short HTTP loop remains unchanged. Separately admitted Work now uses the existing office executor through [application adapters](application-work.md), waits without model polling, and continues from independently verified results. Source scope, task versions and the owner's captured software permission are checked outside the model. Real-app tests use offline decisions. An explicit goal change from ordinary text, a held-out source layout, or a reviewed voice snapshot can steer an existing run without a provider call. That same conversation then shows one verified result from the offline deterministic executor. See [conversation goal changes](conversation-work.md). Live-model quality remains unverified. The voice review screen can update one current run with the reviewed snapshot, or start new work when none is current.

## Extension points

Use the existing `assistant.TOOLS`, `CAPABILITIES`, `TextPlan`, provider adapters and JobService. Add a real boundary test for changes to permissions, lifecycle or persisted effects. Use scripted providers or mock transports until a new live-model budget is explicitly authorized. Detailed contracts: [agent loop](agent-loop.md), [stream](assistant-stream.md), [memory](memory.md), [maintenance](software-maintenance.md).

## Remaining limits

- Realtime provider follow-up calls do not inherit the HTTP loop's three-step cap. The existing10-second per-turn guard, tool limits and600-second session bound remain; a new policy must preserve the current Omni connection and approval rules.
- The12000-character context budget excludes tool schemas and protected approval/task fields, so it is not a total prompt/token hard limit.
- `memory_query` currently searches its latest40-fact input; `owner_search` and context ranking inspect all active facts.
- Native HTTP may deliver a buffered SSE body and may continue after the client stops waiting. No per-token native bridge claim.
- Protocol/evaluation tests do not establish new live-model quality, costs, natural acoustics or device performance.

The old PR58 proposal to call an additional text model from realtime voice is historical, not an adopted implementation plan. It would need separate architecture and spending approval. Follow the one next step in the root handoff; do not resume paid or hardware work from this note.
