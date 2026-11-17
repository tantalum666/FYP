# Group 2 · Official capability reuse audit

17 November2026. Owner explicitly asks to keep development on OpenAI's architecture and avoid rebuilding capabilities already available. This audit uses current FYP source plus fresh primary documentation. It is not a new paid-run, account, remote-schedule or deployment authorization.

## Current findings

| Responsibility | Current FYP implementation | Official capability and decision |
|---|---|---|
| Spoken conversation and delegated reasoning | openai_live.py configures GPT Live with delegation.type=responses and shared function tools | Keep official Live/Responses delegation. No new speech orchestration or client-delegation engine. [Live](https://developers.openai.com/api/docs/guides/live-delegation) |
| Browser reasoning/execution/session | managed_browser_client.py uses official Agents hosted environment; default current browser admission is managed | Keep official harness. FYP's client handles authority, required actions and result/cleanup evidence, not browser planning. [Agents](https://developers.openai.com/api/docs/guides/agents-api/overview) |
| Future scheduled agent reasoning | No official automation resource is created by this slice | Agents API already has once/periodic automations, existing/new-session targets and invocation records. Reuse this for future scheduled agent work; do not build a generic cron/planner/session framework. Invocation completed means delivered, not task finished; stop active work separately. [Automations](https://developers.openai.com/api/docs/guides/agents-api/sessions/automations) |
| Primary text planning | text_ai.py still uses the older AgentLoop/TextPlan with a three-step local controller | This is a real legacy migration gap. Do not call the entire app fully migrated. Freeze generic-loop expansion; migrate the OpenAI path to official session/tool execution as the next orchestration slice, retaining explicit non-OpenAI/offline compatibility rather than silently substituting providers. |
| Thread data acquisition | mail_threads.py makes fixed, bounded Gmail/Graph metadata reads; app's existing worker invokes poll_source_once | Retain as a source synchronization adapter. It performs no inference, action planning or self-scheduling agent work. Timed source freshness is not a replacement for Agents Automations. Provider push notifications can later replace polling. |
| Thread→task association, duplicate handling, notification privacy | mail_followups.py stores the owner's chosen scope/expiry, message identity baseline and one linked existing TaskService task | FYP-specific business/permission state. Retain; official session context is not the app's task database, proof of owner consent, or notification-delivery receipt. Function handlers remain application-owned. [Functions](https://developers.openai.com/api/docs/guides/agents-api/tools/functions) |
| Email draft/send/reply | Existing OAuth, proposal UI and outgoing-mail-attempts reused; direct provider APIs preserve exact target/thread and no-resend receipts | Retain the narrow business adapter and explicit review. Do not recreate OAuth, an SMTP stack, generic MCP server or provider-signed-in account system. The model cannot approve or send on its own. |
| Files/search/general code work | Existing bounded local adapters; no new general search/sandbox in this slice | Prefer hosted web/file search, Code Interpreter/shell, programmatic tool calling and MCP when the next task needs them. Their existence does not authorize broad local-file upload or a new fee. |

## Why the email adapter is not a replacement agent framework

The new worker is explicitly named **mail_sources** and invokes **poll_source_once**. It reads only an owner-selected thread, compares opaque message IDs, adds source evidence to the existing task and publishes through Notifier. It cannot select a tool, generate a plan, run a model, infer deadlines from email text or send a message. Existing Runtime scheduling is reused; no cron parser, alternative task queue, language-model runtime or new memory store is added. A regression forbids model/AgentLoop calls during source polling.

Interactive mail requests are exposed through the same function catalog as Live's official Responses delegation. Owner confirmation remains an application action absent from the model's tool list. The older text controller can also call these business functions, but that compatibility is not evidence that text orchestration has already migrated.

A future "review this tomorrow / keep working on this goal" agent feature must use official Automations/Sessions. The current15-minute metadata refresh does not claim autonomous reasoning and incurs no model inference. Replacing a cheap metadata read with an inference turn on every empty check would change cost and data-sharing behavior and needs an explicit product choice.

## Modern MCP and account boundaries

OpenAI's current MCP guide marks connector_id as deprecated for models released after1September2026. New integrations should use remote server_url or supported secure tunnels; do not copy older Gmail/Outlook connector_id snippets into the current model path. OAuth credentials and provider consent remain app responsibilities. [MCP guide](https://developers.openai.com/api/docs/guides/tools-connectors-mcp).

Google's official Gmail MCP service is a developer preview requiring program membership, gmailmcp.googleapis.com enablement and an OAuth client configured for an AI agent. Its guide requests readonly/compose scopes. FYP's existing Gmail readonly/send grant does not prove those new prerequisites or compose consent. Do not silently replace the current grant or claim MCP is connected. The preview supports thread reads/drafts/labels and is a preferred future broader-tool connection once access is established. [Google configuration](https://developers.google.com/workspace/gmail/api/guides/configure-mcp-server).

Microsoft Work IQ MCP exposes a broad resource/tool surface and uses Entra tenant authentication/policy. Its existence does not establish this owner's personal Outlook account eligibility or complete FYP registration; the prior human-verification block remains. Preserve the current Graph adapters and defer claims of live Microsoft operation until authorization and actual reads. [Microsoft overview](https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/work-iq/mcp/overview).

## Engineering gate for subsequent work

Before adding an execution loop, scheduler, sandbox, context store, tool discovery layer or provider integration: identify the matching official capability, inspect current schemas/account prerequisites, and record adopt/retain/replace with a concrete reason. Retain product authority/data/receipt responsibilities; replace generic model orchestration. Existing raw HTTPX transport is an app convention, not a claim that an SDK supplies another feature. The project environment currently has no OpenAI SDK; no SDK installation or live access claim is made here.

The old16/17November research that said managed execution was off describes the pre-mainline checkpoint. App8c67ddbe subsequently activated the default official browser route across endpoints. That historical statement must not be used as current architecture evidence.
