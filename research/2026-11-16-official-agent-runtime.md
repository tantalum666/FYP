# Group 2 · Reuse the official execution layer

16 November2026. Owner asked whether GPT Live makes it unnecessary to construct computer-use infrastructure ourselves, and whether the app can use Codex-like execution directly.

## Verified distinction

Current FYP Live uses Responses delegation but advertises custom FYP functions. Live itself manages the speech interaction; delegated reasoning/tool work can use hosted tools, MCP and computer use. The application's authorization, business state and user confirmations still belong to FYP. [Official Live delegation](https://developers.openai.com/api/docs/guides/live-delegation).

The official Agents API exposes a managed Codex harness with sessions and environment/tool orchestration. It can run a hosted desktop/browser, or connect to a self-hosted execution environment. This is a practical replacement for writing another generic browser planner/recovery loop. It is not automatically enabled by selecting the Live voice model. [Agents overview](https://developers.openai.com/api/docs/guides/agents-api/overview), [hosted computer use](https://developers.openai.com/api/docs/guides/agents-api/tools/computer-use), [self-hosted environments](https://developers.openai.com/api/docs/guides/agents-api/environments/self-hosted).

For local client integration, Codex App Server provides a richer client-facing protocol for authentication, history, approvals and events; the SDK offers programmatic thread operations. The installed Mac CLI was inspected offline and its JSON schema generated, without starting an inference session. These are alternatives for future local execution, not evidence that FYP currently inherits Codex's signed-in plugins or private browser. [App Server](https://learn.chatgpt.com/docs/app-server), [Codex SDK](https://learn.chatgpt.com/docs/codex-sdk).

## Current engineering choice

Reuse managed browser reasoning behind the existing JobService, leaving typed application operations and owner authorization intact. Keep public research separate from authenticated merchant actions. Exact-domain network/origin approval does not amount to a hard per-purchase confirmation gate. Hosted browser authentication has its own request/result protocol; entering credentials is not an ordinary model tool argument. [Computer-use approvals](https://developers.openai.com/api/docs/guides/agents-api/tools/computer-use).

A managed turn needs terminal-event evidence. Idle alone is insufficient. Closing the event stream does not cancel server work; explicit cancellation/deletion and deletion readback are necessary. Provider-managed physical cleanup may outlive API deletion. [Session lifecycle](https://developers.openai.com/api/docs/guides/agents-api/sessions), [hosted environments](https://developers.openai.com/api/docs/guides/agents-api/environments/openai-hosted).

## Actual trial and limits

FYP's own API key could list the Agents endpoint (HTTP200). The owner then authorized one session, at most60seconds and US$1 total. A small hosted environment, exact public test domain and one explicit browser task were used. The first two displayed books were A Light in the Attic (GBP51.77) and Tipping the Velvet (GBP53.74); the reported cheaper book and prices matched independent HTML readback. Four browser activities were observed, not inferred from the final answer.

Elapsed51.731seconds. The session was deleted and GET returned404. No second cancellation experiment fit the cap. Usage snapshots were null; no precise spend or zero-cost claim is justified. The complete USD1 reservation stays held and the round is closed. Container and model charges are separate dimensions in the official pricing; wall time alone is not a billing receipt. [Pricing](https://developers.openai.com/api/docs/pricing).

The subsequent FYP integration reuses this actual wire shape but has offline lifecycle/UI acceptance only. It remains opt-in and disabled on ordinary runtimes. This does not establish voice-to-shopping autonomy, owner account takeover, paid order execution, ticket issuance or long-running inbox tracking. [Implementation](../desk-companion/docs/managed-browser.md), [QA](../output/qa/2026-11-16-agent-runtime/verification.md).
