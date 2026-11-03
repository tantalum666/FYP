# Group 2 · Modules, data and extension points

28 October 2026. This map describes the integrated branch. The [root handoff](../../handoff.md) records its GitHub state separately from the paused Pi. Archived art/kernel PRs are not part of this integration.

## Responsibility map

| Modules | Responsibility |
| --- | --- |
| app, access, cookies, private_file, vault | HTTP identity/origin boundaries, private credentials and service composition |
| calendar, tasks, workspace_data | Shared business data, versions, quiet hours and explicitly saved preferences |
| offline_calendar | Offline schedule fixtures into the existing task, calendar event, proposal, and notice path; no live account |
| memory, memory_review, memory_extract, profile, recall, aliases | Approved facts, deterministic review/profile/recall and owner-only management |
| conversation, turns, context, context_budget | Bounded login/task-scoped RAM context and budgeted model views; no global transcript table |
| assistant, capabilities, tool_policy, tool_dispatch | Typed tools, owner review, shared bounded execution and cancellation; no model approval capability |
| agent_loop, model_provider, text_ai, text_providers | HTTP planning/streaming, per-attempt usage and replaceable providers; fake is offline |
| voice, voice_turns, voice_media, voice_credentials | Realtime protocols, turn deadlines, explicit media and backend-only credentials |
| jobs, computer, linux_desktop, linux_desktop_bridge | One durable intent/approval/verification queue with three bounded executors |
| goals, nudges, moments, digest, notify, web_push | Confirmed goals, quiet/proactivity-aware local summaries and opt-in notification delivery |
| exchange, backups, diagnostics, log | Validated business import/export, private SQLite snapshots and owner diagnostics |
| frontend phone/components/workspace/device | Separate layouts, shared session/editor/data lifecycle; [frontend contract](software-maintenance.md) |

One API worker owns in-memory voice/outputs/posture state. The five scheduled loops are rules1s, public_data10s, task_advice30s, computer_jobs0.5s and local_backup at its configured check interval. API startup is not authorization to enable providers, executors, media or physical output.

## Execution and state

The model proposes typed actions. `execute_tool` validates while preserving omitted fields, applies risk/time limits and records audit. Read calls return current data; effects retain operation-scoped receipts. Preparing persists only a reviewable proposal/job. Approval, exact intent/version, execution, cancellation and independent readback remain separate.

JobInput supports save/verify for application notes, one owner-named folder and the separately enabled Linux Mousepad→Chromium workflow. Models supply no filesystem path or shell. All filenames use the same validated generated artifact helper. New actions extend the existing registry and JobService rather than another queue.

RAM chat is scoped by owner login and selected task, bounded to16 contexts/40 items/32000 characters with30-minute expiry. HTTP context views are limited further. Business operation receipts persist independently so an explicit retry can recover one acknowledged result after login renewal without recovering old chat. Paired clients do not obtain owner memory, goals, audits or replay.

Business JSON includes approved fact/persona data and job history. Import validates complete intents and normal folder/path bindings; incoming nonterminal jobs return to review without approval/run tokens. Backup final apply is owner-only even for a known preview/cached receipt. SQLite snapshots are private whole-database copies, not sanitized JSON exports.

## Extension rules and limits

Add tools to TOOLS/CAPABILITIES/TextPlan together; keep approval outside model schemas. Add provider protocol adapters separately from business operations. Qwen Omni stays the measured baseline, while other candidates remain open. No paid calls without a new budget. `fake` never contacts a provider.

Text conversation attempts default to40 per UTC day (including fallback); optional background advice is separately20. These are call counts, not a currency hard limit. The context character budget excludes tool schemas. Realtime voice retains its own10-second turn/600-second session policies, not the HTTP three-step loop.

General GUI/shell automation, job archival UI, true remote notification delivery, real-device acoustics/energy and physical arm validation remain separate work. The current one next step is in the root handoff.
