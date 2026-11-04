# Group 2 · Cross-application personal-agent continuation

31 October 2026. The owner paused Pi work and prioritized personal-agent software, especially cross-application operation. This note supplements the [research index](personal-agent-research-index.md) after PR5 merged; it does not repeat the six historical reports or claim access to competitors' private code.

## Refreshed primary evidence and its engineering consequence

| Product | Publicly described mechanism, re-read today | Consequence for FYP |
|---|---|---|
| Grok Bot | A persistent computer retains files and application sessions. Connectors provide structured access; a browser covers unsupported service flows. Shared screens are not separate security boundaries. [Computer and apps](https://docs.x.ai/grok-bot/computer-and-apps) | Keep one owned application workspace and resumable result references. Prefer typed app operations when available; browser visibility alone does not prove completion. |
| Grok Bot | Skills record a successful method, decision rules, result checks and approval boundaries. Routines decide when to run it; a method should be tested before recurring automation. [Skills and routines](https://docs.x.ai/grok-bot/skills-routines-and-automations) | Finish and test a one-time multi-application journey before adding schedules. Do not turn one passing example into a universal workflow or silently create monitoring. |
| Meta Muse | Its published architecture separates the agent runtime, connector/credential services, independent action review and a browser broker. Browser observations use an accessibility surface; user takeover suspends agent actions. [Architecture and browser mechanism](https://research.meta.ai/blog/security-and-safety-for-ai-agents-our-approach-with-muse) | The planner chooses a next action; existing executors and owner authority decide what can run. Files/pages are evidence, not instructions. A model should not receive host paths, credentials or an approval primitive. |
| OpenAI Your dot | Assigned work can persist between conversations and pause until a useful time or missing input. Delegated work receives selected context. Finished execution still requires checking the requested outcome. [Tasks and memory](https://learn.chatgpt.com/docs/dots/tasks-and-memory) | Persist the same goal, answers, action references and verified observations. Resume from actual results; distinguish a process finishing from a completed user task. |

These are vendor descriptions, not independently measured reliability or available SDK parity. The useful common pattern is a durable coordinator, scoped access to real applications, retained evidence, an independent permission boundary and an explicit recovery path. A model API alone supplies none of the account, desktop, notification or transaction infrastructure.

## The post-PR5 gap selected for implementation

PR5's Work can already plan, acquire selected evidence, ask questions, retain decisions, link reviewed effects and independently verify outputs. The current application executor can already operate real Chromium/Calc/Writer/PDF with a single queue, versioned files and read-only reconciliation. The missing bridge kept those two systems apart: Work's registry exposed public browser/MCP adapters but not the current office executor. Ordinary short chat still stops after one effect.

The new bridge belongs in `application_work.py`. It reuses `AgentToolAdapter`, `AgentRunService`, `JobService`, `PermissionService` and the existing office adapter. It adds an explicit per-Work application choice, selected input hashes, task/version binding, the existing job review cards and returned application evidence. It does not create another queue or copy business tasks into a parallel store.

File changes follow Ask first or the Full access version captured when this new Work starts. Enabling Full later cannot retroactively authorize an older pending Work. Parent cancellation, expiry/privacy changes and policy revocation still fence queued execution. A lost preparation response resolves the exact original child; a lost file-save response triggers independent readback rather than another write. Superseded versions are checked from immutable history while the latest version is checked against current published bytes.

## Acceptance and remaining product work

The selected local case uses fictional supplier quotes read by Chromium, a formula-driven Calc comparison, an owner-test change of quantity/budget, a minimum-order question, Writer decision content and PDF export. A deliberate lost completion after saving and a restarted application environment test recovery. The planner in this case is scripted, receives only Work observations, and calls the normal tool registry; it is not a live-model success. Actual results and negative cases belong in [the current QA](../output/qa/2026-10-31-personal-agent-cross-app/verification.md).

This step does not deliver unrestricted computer use, authenticated shopping or airline accounts, real-mailbox monitoring, payment, outbound messages or cloud availability while the host sleeps. Next product evidence must include model-driven unseen variations using an explicitly scoped budget, and selected authenticated connectors/browser workflows when authorized. Keep the typed adapters where they are reliable; introduce general browser interaction through a separately scoped execution boundary instead of granting arbitrary page scripts or shell commands.
