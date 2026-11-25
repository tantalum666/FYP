# Group 2 · Contextual proactive assistance

## 24 November · Evidence, background delivery and mail authority

The existing desk worker checks the standing read-only source while the page is closed. It uses a bounded inbox preview window, excludes promotional, outgoing and verification-code mail, and considers approved local conversation context alongside current sources. The destination and personal settings fence each paid analysis. Existing normal OpenAI daily allowances govern dispatch. A closed allowance can still surface explicit mail action cues locally. Findings remain bound to the exact evidence, are deduplicated and respect quiet hours. The signed-in Conversation orders dated findings with the owner’s actual turns and links a current Gmail citation to its original thread. Lock-screen notifications use a generic attention message.

Google may invalidate a previously stored refresh credential. A real rejection is shown as requiring a fresh sign-in. Normal Gmail setup requests inbox reading and sending after owner review. Users can choose reminder-only access. Reconnect preserves the current grant profile and the narrower profile can be upgraded explicitly. The standing inbox monitor only reads previews. The Apps catalog retains the prior account until a new owner-bound PKCE flow succeeds. Browser notification enrollment is an owner gesture in calendar and companion preferences. [Verification](../../output/qa/2026-11-24-continuity/verification.md).

18 November 2026. Alice compares changed information with the owner's current saved facts, tasks and calendar, and offers a concise, cited finding when it is useful. A user does not have to create a timed reminder or approve each read. This implements the owner's requested standing read-only assistance; it does not grant background sending or purchasing. [Research and official reuse](../../research/2026-11-18-proactive-assistance-and-official-reuse.md), [acceptance](../../output/qa/2026-11-17-proactive-agent-merge/verification.md).

## Experience and controls

An unassigned change can matter: a connected email preview says a fictional repository became public, while a saved preference says it should remain private. Alice can point out that discrepancy, cite both sources and suggest checking the original. It does not require an existing task and does not assert that the email is independently verified. Consistent information produces no alert.

The home surface shows one concise Alice cue; Conversation contains the natural finding and current source labels. An Inbox initiative receipt’s View in conversation opens that bound finding with Sources expanded, without dismissing the receipt. Web, phone and the device layout use shared components. The existing Proactivity preference controls the behavior: Normal, Less often, or Off. Off halts research and selected-mail checks; private-context hiding also fences reads and publication. Quiet hours defer notification. Dismissal uses the original operation ID after an interrupted response. A changed or forgotten source invalidates its old finding.

Selected mail follow-up is a related explicit request: “find this email and follow replies” can start a read-only subscription under the current proactivity preference, even in Ask mode, without a second approval card. General writes and outgoing mail retain their own controls. [Mail contract](mail-thread-followup.md), [permission contract](assistant-permissions.md).

## Current source scope

`initiative_sources.py` projects existing canonical data; it owns no new mailbox, memory or calendar store.

- Up to 20 current saved facts and 20 recent tasks, including each task's latest progress note. Paused tasks are omitted.
- Up to 20 local calendar occurrences in the next seven days, through `Store.snapshot`. This reuses recurrence/exception expansion, completion and deletion rules. Each citation identifies the occurrence and its current version/content. Cancelled or deleted entries are not reported as current work.
- Existing authorized Gmail/Outlook readers provide at most ten recent previews per account; Google Calendar supplies a bounded seven-day view. This is not full-inbox ingestion, attachment reading or provider push subscriptions.
- Mail sources explicitly stopped by the owner are excluded, including after reconnecting the same mailbox. A later explicit new follow request can supersede the stop.

Categories share a 26,000-character evidence budget so one long category cannot crowd out all others. Account versions, hidden context and preference revisions are rechecked around provider access and publication. Unavailable sources are omitted instead of treating stale content as a new successful observation. Private source bodies are not copied into notification payloads.

## Official execution and product responsibilities

`initiative.py` calls the existing OpenAI Responses adapter once for changed evidence, with native strict JSON Schema and no action tools. It runs independently of interactive text sessions. The schema admits at most three findings, each with one to four exact source references. A conflict needs at least two references; all current fingerprints must still match when publishing. This is one bounded read-only inference, not another agent harness.

The existing Runtime worker checks initiative every 15 seconds. A five-minute provider-read fallback supplies changes where push integration is absent; it is not a fixed user reminder or a model call every five minutes. A persisted source signature prevents repeated successful inference on unchanged context. One delayed five-minute retry is allowed after a failed attempt, with at most two attempts per signature. The old `task_advice` inference worker is retired to avoid duplicate background analysis. Its compatibility method remains callable by older paths.

Normal allows at most eight research attempts and six in-app deliveries per UTC day; Less often allows three attempts, only high-importance findings, and two deliveries. Attempts include failures. Clock rollback cannot reset the persisted analysis budget. These are attempt limits, not a verified dollar cap. The existing `DESK_TEXT_BACKGROUND` configuration must be enabled before model-backed research runs; this batch did not change the normal installed runtime's setting.

A bounded database lease fences concurrent analysis/restarts. Up to 100 derived findings and 500 hash-only seen IDs are retained. Pruning resolved/obsolete research notes never deletes the original task, memory, email or business history. Existing Notifier handles quiet delivery and idempotency. Full findings are owner-only; public/display snapshots exclude them. Current valid findings enter the shared bounded text/voice context.

OpenAI Responses read timeouts are now 30 seconds for initiative and 15 seconds for other complete responses, retaining five-second connect/write limits and the existing total body deadline. Real reasoning calls exposed the old five-second response timeout. No automatic send or unknown write retry was added.

Multi-step browser execution remains official Agents Sessions/computer use. Future deliberate scheduled reasoning should use official Agents Automations; FYP still supplies account grants, source freshness, task identity, domain-specific controls and independent outcomes. Ordinary OpenAI text now uses [official sessions and functions](official-text-sessions.md) on the source branch.

## Batched notification delivery

After quiet hours Alice can put up to three currently valid findings behind one content-free notification. Higher-importance findings appear first on the home cue. Normal mode uses a 30-minute gap between interruptions, and Less often uses a two-hour gap and high-importance findings. The existing daily caps also apply. The in-app delivery receipt and finding IDs commit together. Dismissing one member keeps the notice open until its remaining members are dismissed or obsolete. The original single-notice receipts are reconciled on upgrade. This delivery step needs no extra model inference. [Always-on design review](../../research/2026-11-18-always-on-personal-agent.md) · [verification](../../output/qa/2026-11-18-official-text-sessions/verification.md).

## Approved orders in their original conversation

The desk's existing worker infrastructure checks due, already-approved shopping and flight records. It reuses the provider readers, observes their existing backoff, and commits a changed outcome only while the original login, chat, privacy and proactivity settings still permit it. Off pauses background checks. The client keeps only order identity, version and state for unfinished work in that window. It reports a newly verified result or a changed decision in the original conversation. No paid inference or external notification is needed for this receipt. [Verification](../../output/qa/2026-11-21-quiet-order-followup/verification.md).

## Acceptance and remaining work

Local tests cover no initial request, silence, duplicate changes, quiet/off controls, stale/deleted sources, stopped mail, late permissions, bounded retries, clock rollback, dismissal recovery and calendar changes. Desktop and Chinese-phone flows were exercised in installed Chromium with scripted providers. Six real Responses research cases include an unassigned contradiction and quiet controls; a real model also selected follow/stop tools over synthetic mail. No real mailbox subscription or outgoing mail was enabled by those tests.

The normal Mac Web service, native iOS Simulator and Pi kiosk received `c607759e` on 18 November. Both servers reported background research off on 18 November. The normal Mac enabled it with the owner’s 24 November consent. The owner-facing research endpoint is available, and existing Google authorizations passed fresh reads. Sustained real-mail usefulness, closed-phone push delivery, Microsoft consent and production spending controls remain open. [Deployment evidence](../../output/qa/2026-11-18-three-end-rollout/verification.md).
