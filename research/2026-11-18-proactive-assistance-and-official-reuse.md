# Group 2 · Proactive assistance and official capability reuse

Checked 17–18 November 2026. The owner requests spontaneous, useful follow-up comparable to Dot/Muse/Grok and requires OpenAI-first implementation. The supplied competitor screenshot illustrates the desired experience. It does not grant access to the unrelated projects/accounts shown there.

## What the primary sources establish

| Product | Publicly described behavior | Implication for FYP |
|---|---|---|
| OpenAI Your dot | Proactive research connects newly available information to earlier context; assigned tasks, schedules and supported events are distinct. Existing app access and owner controls determine permitted actions. | Do not require a separately scheduled reminder or per-item read approval for every useful discovery. A finding can be unsolicited while outward actions keep their existing controls. [Tasks and memory](https://learn.chatgpt.com/docs/dots/tasks-and-memory), [controls](https://learn.chatgpt.com/docs/dots/controls), [getting started](https://learn.chatgpt.com/docs/dots/getting-started) |
| Muse | Uses relevant events and schedules, reports meaningful developments, and exposes adjustable proactivity. Its public architecture separates agent execution, credential access and action review. | Timing is one trigger, not the definition of proactive assistance. Relevance, continuity and accountable results matter. [Design](https://muse.ai/blog/how-we-designed-muse), [architecture](https://muse.ai/blog/security-and-safety-for-ai-agents-our-approach-with-muse) |
| Grok Bot | Initiative includes contextual offers, connection issues and conversational follow-ups; reusable routines support schedules and selected event triggers. | Preserve ongoing context and report useful changes without turning every message into a noisy routine. [Initiative](https://docs.x.ai/grok-bot/initiative), [routines](https://docs.x.ai/grok-bot/skills-routines-and-automations) |

These are product descriptions, not an audit of vendors' private schedulers or prompts. It would be incorrect to claim these products never use timed work. The user-facing distinction is that a person can receive a relevant discovery without first creating a separate timer or reauthorizing the same read. Having permission to inspect evidence also does not automatically authorize sending, paying or booking.

## Reuse decisions made before implementation

| Need | Current choice | Why |
|---|---|---|
| Read-only relevance/contradiction analysis | Existing OpenAI Responses request with strict native JSON Schema | One bounded inference over changed evidence needs no custom agent controller. No action tools or legacy AgentLoop are used. [Structured output](https://developers.openai.com/api/docs/guides/structured-outputs#supported-schemas) |
| Multiple browser steps, environment and conversation state | Existing official Agents Sessions/computer-use execution | Keep official planning/execution; FYP binds origin/account authority and verifies receipts. [Computer use](https://developers.openai.com/api/docs/guides/agents-api/tools/computer-use) |
| Future deliberate scheduled reasoning | Official Agents Automations | Reuse the supplied service when adding scheduled agent work. No remote automation resource was created in this batch. [Automations](https://developers.openai.com/api/docs/guides/agents-api/sessions/automations) |
| Current local task/calendar/fact state, account grants, dedupe and notification delivery | Existing FYP stores/readers/Notifier plus a small derived finding projection | These are product responsibilities. Official function execution still needs application handlers; it is not the user's business database. [Functions](https://developers.openai.com/api/docs/guides/agents-api/tools/functions) |
| Primary text planning | Preserve the old controller only for compatibility; explicit next migration | Do not claim the whole application is already official-session based, and do not expand that old controller into a competing framework. |

The old task_advice background inference worker is retired. A single existing worker checks changed evidence, with a five-minute provider-read fallback; unchanged successful input does not call a model. This is neither full provider push integration nor an always-running cloud personal agent. [Implemented contract](../desk-companion/docs/proactive-research.md).

`AGENTS.md` now makes official capability/API/SDK verification a normal pre-code step. A guide's conceptual words are insufficient to implement protocol enums: exact reference/types must be checked. Record adopted capabilities, retained product glue, deferred migrations and actual acceptance before claiming completion.

## Defects found by actual provider trials

1. The old five-second response read limit cut off real Responses reasoning. Retain the two timed-out requests as unknown-cost reservations, then use 30 seconds for initiative and 15 seconds for ordinary complete responses; connection/write bounds remain five seconds.
2. The old 45-second browser deadline included environment provisioning. Separate bounded setup from active work, enqueue the task once before lazy readiness, and still honor the outer job deadline.
3. A readiness implementation inferred `provisioning` from prose. The actual reference lists `pending`, `ready`, `connected`, `disconnected`, `suspended`, `expired` and `failed`. Match the reference and preserve compatibility for observed transitional states. [Environment retrieval](https://developers.openai.com/api/reference/resources/beta/subresources/agents/subresources/environments/methods/retrieve)
4. Cancelling an active turn did not clear its pending origin/authentication request; DELETE returned409. Cancel pending requests before the turn, then reconcile deletion with bounded backoff and GET404. A timed-out admitted-origin reply can retry once only after rereading the same pending request; task input and credentials are not automatically replayed. [Turn cancellation](https://developers.openai.com/api/docs/guides/agents-api/sessions#cancel-an-active-turn), [session deletion](https://developers.openai.com/api/reference/resources/beta/subresources/agents/subresources/sessions/methods/delete)
5. Final source review found raw calendar rows included soft-deleted events and ignored recurrence exceptions. Reuse `Store.snapshot` so moved, completed, cancelled and deleted occurrences are represented accurately.

After fixes, six real-model research cases passed, including a saved preference versus an unassigned mail preview. A real model followed/stopped the same synthetic thread without an extra approval card or send. The final hosted browser compared two public catalogue books, inspected stock and returned a correctly calculated report, independently checked. All four hosted sessions are confirmed deleted. Failures and cost uncertainty remain in [QA](../output/qa/2026-11-17-proactive-agent-merge/verification.md).

## Scope still open

The subsequent 18 November rollout put `c607759e` on normal Mac Web, the native iOS Simulator and the Pi kiosk. The two servers retained their background inference setting (off). Sustained real-mail follow-up, full-inbox incremental events, Microsoft consent, production spending controls, closed-phone notifications, and merchant transactions remain open. The subsequent [ordinary-text migration](../desk-companion/docs/official-text-sessions.md) has local protocol and browser acceptance. [Deployment evidence](../output/qa/2026-11-18-three-end-rollout/verification.md).