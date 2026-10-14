# Companion architecture: hosted models, team-owned agent

Date: 14 October 2026. Group 2, Desk Companion. This note is for teammates and coding agents. It does not choose a vendor on the owner’s behalf, and it does not change the school proposal.

**Chinese summary.** 个人助理的大模型走托管 API，不在 Pi 或学校机器上自托管权重。记忆、工具执行、主动调度、人格提示和语音会话由本组软件负责。Meta Muse 与 ChatGPT Dot 的公开拆解已经写在未合并的研究分支里，本文不重写。推荐先开通阿里云通义（Qwen）做第一次有预算的试用，Gemini 3.8 Live 作为同一套脚本的对照；这是工程建议，不是用户已选定的供应商。

## How to read the labels

| Label | Meaning |
|---|---|
| Public record | Written in an official page and already captured in the dated research linked below. Not re-fetched for this note. |
| Inference | A likely system shape drawn from that public record. Not a leak, not a decompilation, not a claim about private source. |
| FYP design | What this repository should build. It is ours. |
| Not decided | The owner has not chosen a provider, a spend cap, or a hardware purchase. |

## Do not duplicate the existing teardown

A public-source teardown of Meta’s Muse, and the matching Dot and Grok Bot studies, already exist on the unmerged branch `codex/personal-agent-kernel-20261012` (draft [PR #5](https://github.com/tantalum666/FYP/pull/5)). They are not on `main`. Read them instead of writing another product survey:

- [Muse architecture and reusable interfaces](https://github.com/tantalum666/FYP/blob/codex/personal-agent-kernel-20261012/research/2026-10-12-personal-agents/muse.md) (12 October 2026)
- [Muse capability gap](https://github.com/tantalum666/FYP/blob/codex/personal-agent-kernel-20261012/research/2026-10-12-personal-agents/muse-capability-gap.md)
- [Dot and reusable agent primitives](https://github.com/tantalum666/FYP/blob/codex/personal-agent-kernel-20261012/research/2026-10-12-personal-agents/dot.md)
- [Dot capability gap](https://github.com/tantalum666/FYP/blob/codex/personal-agent-kernel-20261012/research/2026-10-12-personal-agents/dot-capability-gap.md)

On `main`, the earlier baseline is [Your dot feasibility](../../research/2026-10-03-dot/proactive-task-tracking.md). The 6 October product discussion is [personal-agent-discussion-and-next-steps.md](../../planning/2026-10-06/personal-agent-discussion-and-next-steps.md). Those files separate vendor claims from FYP design. This note only adds the inference, the reason binary reversing cannot see the server, the hosted-API shape, and a provider recommendation.

PR #5 also contains a large unmerged agent kernel (memory, durable runs, routines, bounded MCP, browser fixtures). Do not rebuild that kernel on `main` from this document. If the task is agent behavior, continue that branch or wait until the owner merges it. Repo layout and the merged baseline are in [fyp-repo-review.md](fyp-repo-review.md).

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

## Why REA on a client app cannot reveal this

**FYP design constraint.** [REA](rea-setup.md) reads a file on disk: headers, strings, disassembly, a decompiled view, rules. That is useful for an ELF or firmware image this team built. It is the wrong tool for Muse or Dot, and it must not be aimed at those clients.

The model weights, the system prompt, the memory database, the scheduler, and the tool sandbox are on the vendor’s network. A phone or desktop client typically contains UI, a login flow, caches, and a protocol stub that opens a session. Strings in that binary might name a host. They do not contain the production prompt, another user’s memory, or the code that decides when to speak first. Decompiling the client would still leave those pieces on the server. Emulating the client would not create a legitimate copy of the service.

This repository’s research was done from public pages. Do not try to fill the gaps with a commercial app binary, a prompt-extraction attack, or a stolen session. The gaps the October reports already mark as unknown — private memory schemas, ranking, and unlogged connector contracts — stay unknown.

## FYP implementation: hosted LLM, everything else ours

**FYP design.** The owner’s constraint for this note is: call a hosted LLM API, and do not self-host the assistant model. Memory, tool calling, proactive scheduling, persona, and the voice session are built in Desk Companion. Raspberry Pi 5 (8 GB) remains the desk candidate for camera, calendar, wake word, speaker, and named motion presets. It is not the machine that loads a 30B model. School DGX / V100 capacity is still unknown and is not the plan.

```text
Web, iPhone, Linux desk screen
        |
        v
One FastAPI process + SQLite          <- team
  calendar, tasks, pairing, posture
  context packer (what may be sent)
  approval records and job ledger
  scheduler loops (no model in the 1s tick)
        |
        +-- HTTPS text API ------------> hosted LLM, drafts only
        +-- WSS audio API -------------> hosted speech model, short session
        |
        v
Team executors: notes today; later one named app or device preset
Independent read-back. Unknown writes are not retried.
Local wake word (already sherpa-onnx) only opens the session.
Persona text is our instruction string, not a second model.
```

What `main` already does, and should keep:

- Text tools in `desk-companion/backend/desk/assistant.py` can read tasks, calendar, posture, and device state, and can prepare drafts. The model has no confirm tool. Drafts expire. Calendar writes check a version.
- Voice in `voice.py` speaks as Desk Companion, forwards the same tools, and cancels unconfirmed drafts on barge-in. Audio is not stored. Sessions are capped (600 seconds total, 45 seconds idle).
- Optional background text runs at most once each 30 seconds, only if `DESK_TEXT_BACKGROUND=1`, a provider is configured, and a follow-up is actually due, with a daily cap of 20 attempts. The 1-second loop is rules, not an LLM poll.
- Keys stay in server environment variables (`DESK_TEXT_*`, `DESK_VOICE_*`). Endpoints are allowlisted. The browser, the ESP32, and prompts must not see the key.
- Posture is MediaPipe plus team rules. The language model must not invent a posture label.

What the team still builds around the API:

1. **Context packer.** Before each hosted call, select the current task, a short calendar window, and any facts the owner has explicitly saved. Send that text as untrusted data plus our persona instructions. Do not upload the SQLite file, raw camera frames, or the microphone stream outside an active voice session.
2. **Memory.** On `main`, durable memory is tasks and their evidence, not a general fact store. A reviewed fact list exists only on PR #5. Prefer that design: source, time, correction, and deletion. Retrieval is a query we write. A hosted embedding API is optional later, and only for text we already decided may leave the machine. Do not run a local LLM to “remember.”
3. **Tool calling.** The hosted model returns a tool name and arguments. Our process checks the schema, the owner, the task version, and whether the call is a draft or a read. Writes wait for an on-screen approval bound to the exact text. The provider’s “tool succeeded” flag is not success. Read the file, event, or device receipt.
4. **Scheduling.** Keep due times in SQLite. Wake the text API only for a due follow-up that passed the caps above. A source watch, if added, should create a review for the owner. It should not start a paid call by itself.
5. **Persona.** One versioned instruction the team writes: concise, English by default, Simplified Chinese when the user is speaking Chinese, no medical claims, no self-approval. The desk character (and the unmerged A1 art on [PR #4](https://github.com/tantalum666/FYP/pull/4)) shows listening, thinking, needs-approval, and working. Those are UI states. They are not a cloned Muse or Dot personality.
6. **Voice.** The team owns wake, turn IDs, barge-in, playback stop, and the rule that a partial transcript cannot approve a write. The hosted speech API owns the audio model. Closing the socket does not cancel a job the owner already approved. Basic calendar and posture prompts must still work with the providers set to `none`.

Self-hosting Muse Glimmer, llama.cpp, vLLM, or Ollama as the assistant is out of this design. The September research already said a from-scratch speech model does not fit a three-person prototype. The local wake-word model stays; it is a gate, not the assistant.

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

## Prioritized tasks

Do these without a new provider and without reversing commercial apps. One task at a time. Say whether the result is on `main` or on PR #5.

1. **Context packer on the current text adapter.** Add a test that the outbound Qwen or Gemini body contains the persona instructions and the selected task, and does not contain the API key, deleted task text, or posture frames. No live call. The fake transport already used in tests is enough.
2. **Keep scheduling deterministic.** Add or extend a test that the 30-second advice loop does not call the hosted client when the provider is `none`, the daily cap is spent, or no follow-up is due. Do not put a model inside the 1-second rules tick.
3. **One real executor beyond notes, still on our tools.** Pick one Mac or Linux action the owner names (a file in a test folder, or one test app). Approval binds the full text. Independent read-back. A lost receipt stays `unknown` and is not replayed. This is the product handoff’s next step. PR #5 may already have fixtures; do not fork a second job system.
4. **Persona file.** Move the instruction strings now embedded in `voice.py` and `text_ai.py` into one versioned text file the team can edit, still sent only as the hosted system instruction. Do not import a Muse or Dot prompt.
5. **Voice handoff, fake provider.** A partial transcript must not approve a job. Ending the socket must not cancel an already approved job. Real microphones, Cantonese, echo, and invoices stay gated on the owner’s key and a quiet room.
6. **Hardware, parallel and not blocked on the API.** Named RIG or cleaner preset behind the existing output queue, with a local stop that does not ask the LLM. Posture still needs consented labels before anyone cites the proposal’s F1 target. REA only if the image was built by this team; see [rea-setup.md](rea-setup.md).
7. **Provider trial, only after a cap.** Recheck Hong Kong (or the account’s real region), model ids, and prices. Run the proposal’s style of Mandarin/English commands against Qwen, then Gemini if reachable. Record usage from the provider’s usage fields. Do not treat the September dollar examples as a bill.

## What not to claim

A passing unit test is not a natural voice, a Cantonese result, a Pi thermal result, or a smaller cloud bill. Local notes are not general computer control. PR #5’s tests are not on `main`. Nothing here submits the school proposal or approves a purchase.
