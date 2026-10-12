# Grok Bot product breadth and the FYP capability gap

Research and checkpoint date: **2026-10-12 UTC**, with product provenance rechecked at 13:28 UTC. This is a clean-room study of public documentation, current FYP source and recorded tests. No Grok Bot account, paid inference, private runtime, or live product experiment was used. “Documented” below means a vendor claim, not an independently reproduced capability.

## Conclusion

The first FYP checkpoint establishes useful personal-agent foundations: reviewed memory, optional retained conversations, context permissions, local routines, durable approved jobs and independently verified narrow effects. It **does not establish the user’s requested breadth of cross-application work**. A private note writer and a self-authored record API are valid infrastructure tests; neither substitutes for operating existing applications. Passing hundreds of regression tests does not change that distinction.

The next proof should be an end-to-end task performed by **the FYP agent’s own execution runtime**, with a real source, a real existing destination application, bounded authority, visible progress, stop/recovery and independently checked output. After a deterministic path works, the agent must also demonstrate planning and adaptation within the same scope. A successful fixed click script alone is not broad agent competence.

## 1. Product identity and independent provenance check

The target is the persistent teammate product **Grok Bot**, not ordinary Grok chat, the @grok reply account, Grok Build, or the xAI model API. The [product page](https://x.ai/bot), [launch article dated August 11, 2026](https://x.ai/news/introducing-grok-bot), and [Grok Bot documentation overview](https://docs.x.ai/grok-bot/overview) all describe this product explicitly.

The surprising Cursor connection was checked again rather than assumed:

| Requested URL | HTTP / final URL | What supports the identity |
|---|---|---|
| `https://x.ai/bot` | 200; unchanged | Grok Bot product heading; download on `api2.cursor.sh`; sales and plan links on `cursor.com` |
| `https://x.ai/news/introducing-grok-bot` | 200; unchanged | Named launch and the same download/sales destinations |
| `https://docs.x.ai/grok-bot/overview` | 200; unchanged | Direct link to Cursor’s Grok Bot billing page; cloud computer, persistent context and cross-app work |
| `https://docs.x.ai/grok-bot/security-faq` | 200; unchanged | States: “Grok Bot runs only on Cursor-hosted cloud computers.” |
| `https://docs.x.ai/grok-bot/security` | 200; unchanged | States: “Cursor manages model selection.” Further says the serving mix can change, without a guaranteed fixed vendor set |
| `https://cursor.com/help/grok-bot/plans` | 200; unchanged | Cursor’s own documentation describes Grok Bot access, account linking and Cursor-account metering |

The official xAI overview links to the exact Cursor page, which itself links xAI’s help material. This is a reciprocal primary-source relationship, not a search snippet, user-generated claim, or redirect to another product. The fetched HTML, timestamps, byte counts and SHA256 are preserved in `grok-product-provenance/manifest.json`. It does **not** prove the private corporate arrangement, model-routing implementation, or actual behavior of a customer account. Those were not observed. Sources: [security FAQ](https://docs.x.ai/grok-bot/security-faq), [security](https://docs.x.ai/grok-bot/security), [Cursor plans](https://cursor.com/help/grok-bot/plans).

Documentation also has time-dependent differences: the August launch calls the product beta and puts enterprise access on a waitlist, while the current product page describes enterprise availability. Marketing highlights fewer client platforms than the October overview. Do not combine these into one timeless support matrix. A cloud-hosted Bot and separately permitted commands on a user’s local computer are different capabilities; “cloud-only hosting” does not imply local execution never exists.

No public supported Grok Bot orchestration SDK, complete computer-controller API, memory engine or durable-run protocol was found in the reviewed corpus. xAI’s Responses, function-calling and voice APIs are components, not a published implementation of this product. See the companion [API study](grok.md).

## 2. Product capability → current gap → convincing evidence

FYP status refers to the October 12 first checkpoint and its source/QA, not a future implementation. “Partial” never implies real-provider or real-desktop acceptance.

| Capability and official evidence | Current FYP position | Acceptance needed to close the meaningful gap |
|---|---|---|
| **Long-running autonomous work:** cloud tasks survive closing the client; parallel Bots and task ownership are documented. [Overview](https://docs.x.ai/grok-bot/overview) | Durable single-operation jobs and local routines survive UI closure while the host stays on. No general persistent multi-step planner | Start a multi-step task, close UI, reopen later; show step history, blocked reason and verified output. Restart between safe steps and retain ownership without replaying uncertain effects |
| **Cross-app outcomes:** product examples finish work in tools without clean APIs. [Launch](https://x.ai/news/introducing-grok-bot) | Notes and fictional-data record API only; no genuine third-party application workflow | Read approved public material, operate an existing editor UI, export a result and independently inspect it; all actions originate in FYP’s adapter |
| **Desktop observation and action:** desktop preview exposes interaction; each Bot gets one computer-use task per screen. [Computer/apps](https://docs.x.ai/grok-bot/computer-and-apps) | No FYP screenshot/window inventory/input bridge or GUI lease | Observe actual app/window identity, acquire a lease, perform a permitted action, inspect resulting state; reject a swapped or unapproved target |
| **Connectors plus browser fallback:** plugins offer structured actions, with browser use for missing features. [Computer/apps](https://docs.x.ai/grok-bot/computer-and-apps) | Limited existing calendar import and internal tools; no general connector discovery/auth/action broker | Demonstrate two separately scoped adapters with explicit capabilities; failure must not silently switch identity, broaden target or gain browser authority |
| **Research grounded in sources:** use cases combine gathering, comparison and reviewable outputs. [Use cases](https://docs.x.ai/grok-bot/use-cases) | No persistent research-to-artifact task pipeline | Preserve source URL, retrieval time and evidence span; label inference; stale or unavailable source produces a visible limitation rather than fabricated facts |
| **Files and artifacts:** documented inputs span office documents, media and code; outputs include documents, spreadsheets, slides and evidence. [Files/results](https://docs.x.ai/grok-bot/files-and-results) | Narrow notes/records; existing domain-specific import/export is not a general artifact system | Add typed artifact records with provenance, bounded storage and preview/download; validate one actual application export before expanding formats |
| **Revise existing work:** conversations can request revisions to the same artifact. [Files/results](https://docs.x.ai/grok-bot/files-and-results) | No general artifact revision lineage | Reopen a prior owned result, prepare a version-specific change, preserve the original, and prove the new revision satisfies the requested delta |
| **Reusable skills:** instructions capture inputs, steps, validation, outputs and approval boundaries. [Skills/routines](https://docs.x.ai/grok-bot/skills-routines-and-automations) | Code-owned local read-only routine skills; no reviewed reusable cross-app skill library | Turn a passed workflow into a versioned declarative skill; data inputs cannot introduce executable code, new tools or wider permissions |
| **Learning by demonstration:** limited-duration interaction recording produces a draft skill that should be tested. [Skills/routines](https://docs.x.ai/grok-bot/skills-routines-and-automations) | Absent | Defer until deterministic replay and consent exist; recording must avoid credentials and never convert observed actions into permanent authority |
| **Scheduled and event work:** routines have owner, timezone, source, destination and limits; event integrations can require separate setup. [Skills/routines](https://docs.x.ai/grok-bot/skills-routines-and-automations) | Once/daily/weekly deterministic local checks, persisted occurrences and in-app results; no external event ingress | Retain existing DST/dedupe tests; later add signed narrowly filtered events with replay protection. A triggered run inherits only the explicit routine grant |
| **Proactive delivery:** completion/input notifications and attention states are documented. [Settings](https://docs.x.ai/grok-bot/settings-and-notifications) | Local notification/result layer; no general proactive external delivery | Deliver one relevant result once, respect quiet hours, distinguish unseen/needs-input/working, and prove acknowledgment is not consumed merely by opening a page |
| **One identity across text and voice:** dictation, live calls, memos and in-progress redirection. [Collaboration](https://docs.x.ai/grok-bot/chat-and-collaboration) | Existing text/voice provider adapters and shared personal-context rules; voice quality unmeasured | A real authorized audio test must demonstrate interruption, consistent context and persona, a task continuing after call end, and no stale spoken completion |
| **Durable memory:** stable preferences and prior-work summaries; changing consequential facts should be reread. [Bots](https://docs.x.ai/grok-bot/bots) | Explicit owner-reviewed facts, versions and optional retained threads implemented | Existing software controls must be checked in real UI; evaluate appropriate recall, correction, forgetting and source freshness across later tasks, without treating memory as permission |
| **Coordination:** asynchronous Bot-to-Bot messages, wakeups and visible ownership handoffs. [Collaboration](https://docs.x.ai/grok-bot/chat-and-collaboration) | One agent-facing service; no durable specialist handoff graph | One coordinator plus one bounded worker with persisted parent/child ownership and cancellation propagation; avoid duplicate work and duplicate narration |
| **Approval and policy:** exact operation review, once/deny and scoped rules; model-based review supplements controls. [Approvals](https://docs.x.ai/grok-bot/approvals-security-and-privacy) | Strong exact-intent/version approval for current narrow jobs; model drafts only | Preserve this when adding steps. A changed target/content, external instruction or stale observation cannot reuse a prior approval. Read actions may be separately authorized without asking per click |
| **Authentication and human takeover:** credentials, verification and blocked human-only steps have separate handoff. [Approvals](https://docs.x.ai/grok-bot/approvals-security-and-privacy) | No general login or remote-control handoff | Initial real-app workflow needs no credentials. Later secure handoff must suspend effects, suppress credential observation, and re-observe scope before continuing |
| **Stop and redirect:** direct user instruction takes priority; stop cannot undo completed effects. [Collaboration](https://docs.x.ai/grok-bot/chat-and-collaboration) | Cooperative cancellation for narrow jobs and separate voice interruption | Process-owned browser cancellation, bounded cleanup and no new dispatch after cancellation; in-flight effects may still complete and must reconcile rather than be described as rolled back |
| **Recovery:** computer recreate can pause/resume safely; terminate preserves disk but loses the running turn. [Computers](https://docs.x.ai/grok-bot/computers) | Restart invalidates running tokens; unknown writes reconcile read-only. No GUI/session recovery | Crash after an uncertain click/export and independently find the result without repeating the effect; safe reads can resume, uncertain writes cannot |
| **Team/shared access:** team and private scopes, requestor-specific OAuth, shared configuration. [Team Bots](https://docs.x.ai/grok-bot/team-bots) | Single-owner prototype | Defer multi-user operation; three FYP developers do not imply a production multi-tenant authorization model |
| **Quota and budget:** weekly metering and on-demand limits; a current run may exceed the monthly limit. [Cursor plans](https://cursor.com/help/grok-bot/plans) | Some existing per-day suggestions/voice bounds; no run-level model/tool budget ledger | Persist maximum duration, steps, tool calls and planned costs; refuse new expensive work before the budget is exhausted, while preserving verified partial results |
| **Cloud and local environment selection:** local execution is separately allowed and cloud work is independent. [Settings](https://docs.x.ai/grok-bot/settings-and-notifications) | Host-local runtime and previews; no authenticated remote executor enrollment | Explicit environment identity, connection/readiness and operation scope; never infer authority from the UI device or silently move a task to another computer |

## 3. Security lessons worth retaining rather than copying blindly

The published product isolates users, but Bots belonging to one user share computer files and sessions. Separating personalities or screens is not credential isolation. Connector blocking also does not automatically block a service’s website; network restrictions are a separate control. A second review model cannot supply deterministic authorization or undo an external effect. These distinctions are relevant to FYP regardless of vendor implementation. [Security FAQ](https://docs.x.ai/grok-bot/security-faq)

FYP should keep owner identity, model destination consent, browser/application authority, artifact access and physical actuation separate. The agent must not grant itself access, and a document or web page must never expand an approved target. The Pi/ESP32 watchdog and emergency stop remain independent of the language model and desktop worker. These are **FYP design recommendations**, not claims about Grok Bot internals.

## 4. Concrete acceptance ladder

### Gate A: genuine bounded browser cross-application work

Proposed candidate: an approved public documentation page → the real **StackEdit** UI → a Markdown source brief exported by that application. The brief contains observed source title/heading, source link, timestamp and user-provided public/synthetic note. Perform the authorized read first, then prepare the exact preview and obtain owner approval before editor effects. Use an isolated context without accounts or cloud sync. FYP’s worker performs navigation/edit/export; a separate parser checks the export. Exact current UI selectors, asset origins and compatibility have not been tested. See [bounded browser comparison](bounded-browser-options.md).

The current cloud has an actual sandbox-launch failure, not merely a missing display. It remains blocked; no security flags or alternate launch bypass should manufacture a pass. Implement policy and unit contracts in cloud; use the existing authorized Mac QA task to run **the same FYP runtime** once prepared. A clean browser context does not isolate the Mac itself; record the actual sandbox and egress controls and qualify any routing-only result. Developer browser tools watching the UI are supporting evidence, not the executor implementation. Only the retained export survives closure of the nonpersistent editor workspace.

### Gate B: bounded agent behavior, not only replay

The agent receives a goal and permitted source/application catalog. It proposes a typed plan, observes current state and chooses among reviewed operations. Test different document titles, public source headings and harmless recoverable UI changes. It may replan within an approved read scope, but cannot broaden write authority. Evaluate successful completion, correct refusal/blocking, retries after read-only failures, and no duplicate effects. Fake planner tests prove protocol behavior; actual model task quality remains separately unmeasured until an authorized provider or local model is tested.

### Gate C: long-work continuity and control

Close the UI during work; restart after a safe observation; interrupt just before export; lose the export acknowledgment after creation; reopen and reconcile. Save the step graph, current owner, exact intent, observations, effects and verification separately. An ambiguous write remains unknown. A completion sentence or screenshot alone does not satisfy the output oracle.

### Gate D: a second independent task family

Only after Gate A–C pass, add another actual application such as Excalidraw or an already-provisioned document/spreadsheet API. Clearly label API automation versus visual UI control. Two materially different workflows, boundary tests and repeated runs are the minimum useful evidence toward breadth; arbitrary native desktop operation remains a separate target.

### Gate E: voice, proactivity and hardware integration

Use the same task identity from voice and text, keep one consistent assistant personality, announce only verified state, and retain physical stop independence. Real microphone latency, provider quality, Pi resource behavior, RIG-Arm feedback and ESP32 cleaner safety require their own tests. None follows from browser success.

## 5. Scope and coverage

The prior report captured 47 official pages: 22 Grok Bot product pages and 25 developer/API pages, plus the OpenAPI schema. This supplement reread the complete core product pages for Bots, collaboration, computer/apps, files/results, skills/routines, settings, approvals, computers, troubleshooting and security FAQ; overview/security/launch/product/billing provenance was independently rechecked. Team/enterprise/identity/network details remain supporting scope from the original study, not an implemented enterprise specification.

FYP evidence reviewed includes current `jobs.py`, `computer.py`, `executor_registry.py`, architecture, computer-jobs contract, implementation plan and checkpoint QA. Recorded checkpoint evidence is 361 backend and 50 frontend tests plus static/build checks and actual demo-app HTTP/SQLite proof. That count is **not** browser, provider, hardware, or commercial-product parity evidence. Exact publication/CI status is owned by the separate checkpoint delivery and must be verified there.

This report does not estimate a completion percentage: capability breadth, reliability, safety, integration quality and user experience cannot be reduced to a test-count percentage. The next milestone is the observable acceptance task, not a claim to have fully replicated a commercial assistant.
