# Companion architecture: hosted models, team-owned agent

> **HISTORICAL — 14–15 October 2026.** Use the [current research entry](../../research/personal-agent-research-index.md) for product identity, current source checks and implementation priorities. Dated provider recommendations, budgets, missing-feature statements and old next steps below are not current instructions.

Date: 14 October 2026. Group 2, Desk Companion. This note is for teammates and coding agents. It does not choose a vendor on the owner’s behalf, and it does not change the school proposal.

**Review update, 15 October 2026.** PRs #7–#14 are merged into `main`. Memory, one owner-named folder, shared persona, quiet follow-ups, recovery copy and text adapters use the existing note-job contract. This PR #6 reconciles the dated research with those implementations and records the [independent review](../../output/qa/2026-10-15-grok-review-merge/verification.md). PRs #4 and #5 remain separate. Provider/model choice and a test-spend cap remain open. No hosted account was opened.

**Chinese summary.** 个人助理的大模型走托管 API，不在 Pi 或学校机器上自托管权重。记忆、工具执行、主动调度、人格提示和语音会话由本组软件负责。产品行为见 [companion-product-teardown.md](companion-product-teardown.md)；PR #5 上的早期接口研究不在这里重写。推荐先开通阿里云通义（Qwen）做第一次有预算的试用，Gemini 3.8 Live 作为同一套脚本的对照；这是工程建议，不是用户已选定的供应商。

## How to read the labels

| Label | Meaning |
|---|---|
| Public record | Written in an official page and already captured in the dated research linked below. Not re-fetched for this note. |
| Inference | A likely system shape drawn from that public record. Not a leak, not a decompilation, not a claim about private source. |
| FYP design | What this repository should build. It is ours. |
| Not decided | The owner has not chosen a provider, a spend cap, or a hardware purchase. |

## Product behavior and the earlier study

The product-facing teardown for this branch is [companion-product-teardown.md](companion-product-teardown.md) (14 October 2026). It identifies Meta Muse, separates ChatGPT “your dot” from New Computer’s Dot, and lists gaps and tasks against `main`. Read that file for features, personality, memory, proactivity, voice, hardware, and privacy. Do not add another survey.

An earlier public-source study of Meta’s Muse, ChatGPT’s dot, and Grok Bot already exists on the unmerged branch `codex/personal-agent-kernel-20261012` (draft [PR #5](https://github.com/tantalum666/FYP/pull/5)). Those notes were absent from this checkout until the 30 October research recovery. The six reports are now available below with historical labels; PR #5 application code remains unmerged:

- [Muse architecture and reusable interfaces](../../research/2026-10-12-personal-agents/muse.md) (12 October 2026)
- [Muse capability gap](../../research/2026-10-12-personal-agents/muse-capability-gap.md)
- [Dot and reusable agent primitives](../../research/2026-10-12-personal-agents/dot.md)
- [Dot capability gap](../../research/2026-10-12-personal-agents/dot-capability-gap.md)
- [Grok Bot mechanisms and interfaces](../../research/2026-10-12-personal-agents/grok.md)
- [Grok Bot capability gap](../../research/2026-10-12-personal-agents/grok-capability-gap.md)

On `main`, the earlier baseline is [Your dot feasibility](../../research/2026-10-03-dot/proactive-task-tracking.md). The 6 October product discussion is [personal-agent-discussion-and-next-steps.md](../../planning/2026-10-06/personal-agent-discussion-and-next-steps.md). Those files separate vendor claims from FYP design. This note only adds the inference, the reason binary reversing cannot see the server, the hosted-API shape, and a provider recommendation.

PR #5 also contains a large unmerged agent kernel (memory, durable runs, routines, bounded MCP, browser fixtures). Do not merge that kernel. The owner’s later `main` stack is PRs #7–#14, which add owner-reviewed memory and one folder action on the existing note-job contract. Do not start a second job system and do not move #7–#14 onto PR #5. Repo layout at the time of this note is in [fyp-repo-review.md](fyp-repo-review.md).

## Inferred shape of Muse, Dot, and a personal agent

**Inference, from the public record above.** Both products are cloud assistants with a client that shows conversation, approvals, and results. The behavior that matters lives on the vendor’s servers.

```text
Phone / desktop / chat client
        |  session, audio, approvals UI
        v
Vendor gateway
        |
        +-- Hosted LLM (weights, system prompt, tool schema)
        +-- Memory service (saved facts and retrieval, not a full transcript)
        +-- Tool broker (connectors, browser, computer) with a separate approval check
        +-- Scheduler (clock and a few event sources) that wakes the orchestrator
        +-- Artifact store
Persona is mostly the server prompt plus editable memory plus the client character.
Voice is a speech front end. Ending the call does not have to end the task.
```

**Muse, public record, then inference.** Meta’s 8 September 2026 announcement describes a personal agent with a cloud computer that keeps working after the app closes. The security article describes a per-user Linux VM, the agent inside a restricted cell, and separate host services for credentials, connectors, and permission decisions. The design article describes one ongoing conversation, editable memory, goals, and approvals that are not just another chat sentence. **Inference:** the client is a remote control for that VM and those host services. The model weights, the production prompt, the memory ranker, and the connector credentials are not in the app package. Muse Code, the Model API, and consumer Muse are three different surfaces; a Model API key is not consumer Muse.

**Dot, public record, then inference.** OpenAI’s dot docs describe an ongoing cloud agent with its own computer, work that continues while the user’s PC is off, and memory made of current context, relevant ChatGPT memory, and saved notes rather than a full transcript. A finished model turn is not proof the task succeeded. Connections, schedules, and pause scopes are separate. **Inference:** the same split holds. The ChatGPT or desktop app can show state and collect audio, but the durable task, the memory index, and the computer session are server-side. The 12 October research also separated this product from the public Agents API. An API key does not embed dot.

**A general personal agent, inference.** Any product in this class needs the six blocks below. Vendors can merge boxes. The split is still the right one for FYP, because we do not own their servers.

| Block | What it usually is | What stays off the device |
|---|---|---|
| LLM | A hosted model that reads a packed prompt and may emit tool calls | Weights, hidden prompt, provider logs |
| Long-term memory / retrieval | A store of facts, tasks, and source snippets, searched before the call | Ranking code and the full private corpus, if they live in the vendor cloud |
| Tool calling | Model proposes a typed call; a broker executes it and returns a result | Sandboxes, connector tokens, computer VMs |
| Proactive scheduling | A clock or event cursor that wakes the orchestrator only when something is due | Vendor cron and event subscriptions |
| Voice / multimodal | Speech in and out, or images, attached to the same task identity | Speech-model weights; raw audio retention unless the product says so |
| Persona | Stable instructions, voice, and a visible character | The vendor’s hidden personality prompt |

## Why a client binary cannot reveal the server

**FYP design constraint.** Muse and Dot keep the model weights, the system prompt, the memory store, the scheduler, and the tool sandbox on the vendor’s network. A phone or desktop client typically contains UI, a login flow, caches, and a protocol stub that opens a session. Strings in that binary might name a host. They do not contain the production prompt, another user’s memory, or the code that decides when to speak first. Decompiling or emulating the client still leaves those pieces on the server.

This repository’s research was done from public pages. Do not try to fill the gaps with a commercial app binary, a prompt-extraction attack, or a stolen session. The gaps the October reports already mark as unknown — private memory schemas, ranking, and unlogged connector contracts — stay unknown.

## FYP implementation: hosted LLM, team-owned state and tools

The 14 October design proposes hosted text and speech APIs with local state, tools and scheduling. A provider remains unselected. This is a design plan; it does not claim live-provider or hardware validation.

```text
Web / iPhone / independent Linux screen
                 |
         FastAPI + SQLite
 calendar, tasks, owner facts, persona, approval records
 quiet-hour holds and capped optional advice
                 |
  configured text / short speech API -> model proposes tools
                 |
  existing JobService -> bounded notes or one named folder
                 |
        independent read-back and durable result
```

The following are implemented after PRs #7–#14:

1. `desk/context.py` selects active facts, saved tasks and a bounded calendar window. Paired text requests omit owner facts; response caches distinguish the access scope. Camera frames, credentials, full databases and folder paths are not context fields.
2. `desk/memory.py` stores up to 200 owner-reviewed active facts with source, version and timestamps; at most 40 enter model context. Correction and deletion require the owner. Deleted facts are omitted from later context. This is not a complete chat transcript or a guarantee of removal from old provider sessions.
3. Models prepare typed drafts; owner approval remains separate. Notes and one owner-named directory use the same job ledger. Directory components are opened without following links; generated files are never overwritten. Unknown writes are reconciled by read-back.
4. Quiet-hour holds persist across restart and saved-preference edits. At most three new reminders appear per scheduler pass; optional model advice is disabled by default and capped at 20 attempts a day.
5. A versioned owner persona is shared by text, voice and advice. Reset keeps versions increasing; immutable tool/data rules remain appended in code. Editing failures retain the local draft until the user explicitly loads the current text.
6. Voice retains short sessions, interruption and bounded dispatch. Paired terminals cannot call memory tools; owner sessions and explicitly enabled local voice can. Protocol tests do not establish naturalness, echo cancellation or target-device latency.

The fixed-camera posture loop, local calendar and named hardware presets remain independent of model availability. RIG, the cleaner and Pi performance still require real devices.

## Provider comparison and recommendation

**Not decided by the owner.** The school proposal of 28 September names Qwen realtime as the first voice candidate, then Gemini, OpenAI Realtime, and GPT-Live, and says not all four will be integrated. [product.md](../../product.md) records that this order was later superseded as a quality ranking, that the final service is not locked, and that the Qwen and Gemini adapters in the tree are not a purchase or a listening test. The 29 September studies are the latest full comparison in the repo. Prices and region lists below are those dated snapshots. Recheck the vendor console before any key or invoice.

Goals that the choice has to serve: one desk prototype; English UI with Simplified Chinese; hands-free short voice sessions after a local wake word; Mandarin and English commands (proposal target: 40 commands, at least 90% correctly executed, every calendar-write confirmation passing); later agent tests also want Cantonese and mixed speech, which are not yet measured; reliable tool drafts rather than the model announcing success; posture and motion staying local; a student budget with no spend approved; Hong Kong as the team’s location.

| Hosted option | Why it fits | Why it is not an automatic winner |
|---|---|---|
| **Qwen text + Qwen Audio** (Alibaba Model Studio). Adapters and endpoint allowlists already exist. | School proposal’s first candidate. 25 September region note: a Hong Kong workspace is documented, unlike the direct OpenAI and Gemini developer-API country lists checked that day. 29 September and 6 October notes: Audio 3.1 documents Mandarin, English, and Chinese dialects including Cantonese. Built-in web search cannot be combined with function calling, which matches our rule that tools are ours. September arithmetic put the Flash tiers at well under one US dollar for 10 minutes of audio a day, and Plus near Gemini’s few-dollar example. | Independent public scores for 3.1 tools and naturalness were thin. 3.0 scores must not be copied onto 3.1. Hong Kong voice SKU prices were not confirmed line by line. Dialect support on a model card is not a passing FYP test. |
| **Gemini text + Gemini 3.8 Live.** Adapters exist. | 29 September recommendation if a single integration start is chosen for evidence: stronger third-party English conversation and tool-task snapshots, async function calls, and a low published per-minute audio price (about US$4 for the 10-minute-a-day example, before context replay). | The 25 September developer-API region list did not include Hong Kong. The benchmark excerpts were English-heavy. Active listening bills the whole session, so an always-open mic would fight the wake-word design. No Cantonese result is recorded in our files. |
| **OpenAI Realtime 2.1 or GPT-Live.** | Useful later as a quality ceiling. GPT-Live can keep talking while another worker plans. Realtime has direct function calls. | No adapter in the current tree. The same Hong Kong direct-API gap was recorded. GPT-Live bills the open session, including silence; the September example was about US$15 for 10 minutes a day before the backend. That fights a short student session. |
| **Meta Model API (Muse Spark) or consumer Muse.** | The October teardown shows a real inference API and a separate consumer product. Spark is a possible later adapter. | No code, no account, and consumer Muse is not an embeddable agent. Adding it now duplicates the teardown and skips the adapters we have. |
| **StepAudio, Doubao, Grok Voice, ElevenAgents.** | September notes kept them as second-round or cost experiments. StepAudio’s preview was listed as temporarily free, with no end date. | No adapter, no listening test, and a free preview is not a six-month plan. |

**Recommendation (engineering, not an owner decision).** Ask for one hosted account first: **Alibaba Cloud Model Studio, Qwen**. Use a cheap Qwen **text** model for drafts and the optional background follow-up. Use **Qwen Audio** realtime only for the wake-word session, and close it on the existing idle and total limits. Keep Gemini 3.8 Live as the single comparison: same tools, same Mandarin/English script, run only if the actual account can call Google. Switch the environment variables if Gemini wins that script or if the Qwen account cannot be opened. Do not add OpenAI, Meta, or a local LLM until that pair has a result. Do not create a key, accept terms, or spend until the owner sets a cap. A failed region check is a blocked account, not a reason to bypass it.

Until that trial exists, leave `DESK_TEXT_PROVIDER` and `DESK_VOICE_PROVIDER` at `none`. Local rules and the calendar still run.

## Remaining tasks

1. Name one real target computer/application task and data scope, then prove approval, actual execution, independent read-back, refusal outside scope, cancellation and unknown-result recovery. The folder executor is a bounded file capability, not general GUI control.
2. Define job-history retention/archive and business backup for facts, persona and jobs. Current calendar/task backup does not include all of these stores.
3. Only after the owner chooses a provider/model and spend cap, refresh region, model IDs and pricing and run the same Mandarin/English command script. September prices remain dated examples.
4. Validate real voice/wake/AEC, consented posture labels, Pi/iPhone operation, optical output and commissioned RIG presets separately. Software tests do not fill those evidence gaps.

## What not to claim

A passing unit test is not a natural voice, a Cantonese result, a Pi thermal result, or a smaller cloud bill. Local notes are not general computer control. PR #5’s tests are not on `main`. Nothing here submits the school proposal or approves a purchase.
