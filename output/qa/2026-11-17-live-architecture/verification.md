# Group 2 · Live and execution-layer clarification

17 November 2026. Owner asks whether FYP is using Live and whether the earlier official-reuse plan should eliminate much of our implementation. This is architecture clarification, not a new paid/deployment authorization.

Read current AGENTS/handoff and recent decisions, research/2026-11-16-official-agent-runtime.md, OpenAILiveProtocol setup, local ComputerUseExecutor, ManagedBrowserExecutor and AgentLoop. Fresh normal Mac 8831 readback: release 2c31f430, voice provider openai_live/model gpt-live-1/configured true/active false; local computer_use enabled/configured true; managed_browser configured true but enabled false. These are configuration/readiness facts, not a fresh provider or voice trial. Only selected nonsecret status fields were emitted.

Current source uses Responses delegation with FYP custom functions. Local browser actions are generated through OpenAI's computer tool, while FYP still owns the local Chrome process and execution loop. Official Agents managed execution has a separate opt-in adapter and is not the default. PR #126 wires business admission/results but does not change that default. The prior official-first direction remains unfinished at the execution layer.

Re-read current official Live delegation, Agents overview and Agents computer-use documentation. Live can manage Responses requests/context and use hosted tools/MCP; custom tools and client delegation still need app-side execution/decisions. Agents supplies the managed Codex session/orchestration/context-compaction/recovery layer. FYP still owns Alice/device UX, business records, account/permission bindings and independently justified outcomes.

Clarify the next step: prefer the existing official Agents origin/authentication/session-continuation protocol before building another general local browser-control stack. Keep existing local adapters for concrete local/Pi functions and compatibility. Official authentication currently supports email/password/verification codes, not passkeys or QR sign-in; unsupported merchant paths require separate evaluation. This does not prove a completed authenticated commerce path.

No runtime/provider setting, source code, account grant or paid session changed. Documentation-only validation: diff/link check. Sources: [Live delegation](https://developers.openai.com/api/docs/guides/live-delegation), [Agents overview](https://developers.openai.com/api/docs/guides/agents-api/overview), [browser sign-in](https://developers.openai.com/api/docs/guides/agents-api/tools/computer-use#handle-sign-in).
