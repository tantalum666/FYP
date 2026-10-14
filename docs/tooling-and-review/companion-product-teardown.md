# Product teardown: Muse, Dot, and a personal agent

Date: 14 October 2026. Group 2, Desk Companion. Written for teammates and coding agents (including Codex).

**Merge status, 14 October 2026, later than the roadmap below.** Memory and the folder action now exist as PRs **#7–#14** on the existing note-job contract, aimed at `main`. Do not merge PR #4 or PR #5. Do not extend PR #5. Do not open a hosted provider account until the owner sets a spend cap. Do not add unrestricted app or GUI control.

**Chinese summary.** 和 Desk Companion 最吻合的 “Muse” 是 Meta 在 2026 年 9 月推出的个人代理，不是旧的视频站或冥想应用。名叫 Dot 的公开产品有两个：本组 10 月 3 日已经指定的是 ChatGPT 里的 Your dot；本轮提示里更可能指的是 New Computer 的 iOS 伴侣，该公司主页已宣布停运。下文只根据公开网页，不反编译、不提取提示词。差距和路线图对着 `main` 上的 Desk Companion，大模型仍走托管 API。

This note describes what those products **say they do for a person**. It is not an audit, a benchmark, or a copy of their servers. A likely technical shape, and why a client binary cannot reveal it, is already in [companion-architecture.md](companion-architecture.md). The 12 October studies on unmerged [PR #5](https://github.com/tantalum666/FYP/pull/5) remain the earlier interface notes. Do not write a third survey.

## Identification and uncertainty

| Name in the request | Product used below | Why | What is still uncertain |
|---|---|---|---|
| **Muse** | **Meta Muse**, the personal agent launched with the 8 September 2026 safety article and the September 2026 design article. | Desk Companion is a personal agent that should act in the user’s tools, keep memory, work after the chat closes, and remind the user. That is the product those two Meta pages describe. Older products that also use the name Muse (a former video host, meditation apps) do not match this brief. | Meta’s consumer announcement on `about.fb.com` was not retrieved (an earlier fetch returned HTTP 403). The launch demo video was not watched. No first-party checkout price was opened. “AI glasses, coming soon” and “free for most uses, subscriptions for more” appear in a [WebWire reprint](https://www.webwire.com/ViewPressRel.asp?aId=360321) (10 September 2026), not in the design article fetched here. |
| **Dot** | **Two products, kept separate.** (1) OpenAI **ChatGPT “your dot”**, which the FYP owner named on 3 October 2026. (2) **New Computer’s Dot**, the iOS companion the latest request says is the likely Dot. | (1) Matches “acts in the user’s apps, keeps memory, works in the background, sends reminders,” and is already the baseline in [proactive-task-tracking.md](../../research/2026-10-03-dot/proactive-task-tracking.md). (2) Is a real 2024 companion, but its own site says the company is winding down. It is not the computer-use reference for this FYP. | New Computer’s [homepage](https://new.computer/) says Dot stays up until **October 5** and does not print the year. [TechCrunch, 5 September 2025](https://techcrunch.com/2025/09/05/personalized-ai-companion-app-dot-is-shutting-down/) dates that deadline as 5 October 2025. The [product page](https://new.computer/dot) was still written in the present tense when fetched on 14 October 2026. The App Store listing was not opened. |

No page here was obtained by decompiling an app or extracting a hidden prompt. Meta’s design article voluntarily quotes one line of its system prompt. That line is cited as their published sentence. It is not adopted as Desk Companion’s persona, and the rest of the prompt was not sought.

## Meta Muse

Sources fetched 14 October 2026: [How We Designed Muse](https://introducing.muse.ai/) (Mona Sarantakos with Christine Awad, September 2026) and [How We Built Safety Into Muse](https://research.meta.ai/blog/security-and-safety-for-ai-agents-our-approach-with-muse) (Tarek Sheasha, 8 September 2026). The WebWire reprint is used only where noted, and only as a secondary copy of the announcement.

### Core features

The design article’s claim is that Muse finishes tasks, not only answers. Published examples include reading school email, putting dates on a family calendar, filling a shopping cart, booking dinner, and messaging the user about a sports-tryout deadline. The same article says Muse has its own computer (files and a terminal), a full browser (search, forms, purchases), and can produce documents, PDFs, web pages, trackers, and dashboards. Those outputs are called **artifacts** and can live in the chat or outside it.

The safety article says each person shares a dedicated cloud Linux VM with a browser, and that iOS, Android, and web clients connect to that VM. Connectors cover email and other services, including Instagram and Facebook, plus custom connectors when a service has an API or CLI. WebWire adds WhatsApp as a way to talk to the same agent, and says work continues after the app is closed.

A **Goals** tab tracks long-running plans. An activity log sits under the avatar. Ideas are suggested from goals and from conversation, including during onboarding. Approvals for hard-to-undo actions (the design article names writing an email and paying) are structured cards, not another chat sentence.

### Personality and conversation style

One main chat is meant to feel like an ongoing conversation with a person. The user can interrupt or send several tasks without waiting. Side chats exist for separate projects. Chat bubbles were added because proactive messages and stacked user messages made a flat transcript hard to read.

The published first line of the system prompt is: “Your purpose is to make your user’s life better.” People name the agent and design an avatar (the author’s example is “Veda”). The design article treats that character as a core feature. Desk Companion should not copy the sentence or the character.

### Memory

Memory persists across the main chat and side chats. The safety article says files in the VM, including “Muse’s memory about you,” can be inspected, edited, and downloaded. WebWire says the user can tell Muse to forget specific things. This teardown does not know the private schema, what is stored automatically, or how memories are ranked.

### Proactivity

Muse can message first. The design article sets a high bar: a proactive message should be worth the interruption. The user can turn proactivity up, down, or off. After a goal or task is set, Muse keeps working on a schedule and on relevant events, then notifies only when something is new or needs input. The safety article’s scheduler detail (crons inside the VM) is a published implementation claim, not something this repo should reproduce.

### Multimodal input and voice

Fetched first-party pages describe text chat, interruption, a visual avatar, artifacts, and a browser that can encounter images (the safety article discusses prompt injection in page images). They do not describe a phone-call mode or a wake word. WebWire says talking to Muse is like messaging a person, in the Muse app or WhatsApp. Whether WhatsApp voice notes or a live call exist was not established from these pages.

### Hardware form factor

At launch, the clients named in the safety article are iOS, Android, and the web. WebWire says the US rollout is on iOS, Android, and muse.ai, with **AI glasses coming soon**. No desk terminal, camera, or motor is part of the product described. Glasses were not confirmed on a Meta-owned page in this session.

### Privacy, as published

These are Meta’s claims, not an independent test:

- The person’s files and connected credentials live in that user’s VM. Credentials are stored outside the agent’s runtime, and the model is not supposed to see real tokens or typed passwords.
- Read and write access can be separated. A purchase or an outbound email is supposed to stop for an approval dialog that is not part of the chat. Checkout can use a Stripe Link single-use card; Shop Pay is described as later.
- The user can see an activity log and the permissions already granted.
- Conversations and VM data are not shared with Meta ad systems. Browsing can still affect ads indirectly, because a site visit can look like the user’s visit.
- Conversation and tool trajectories can be sanitized and used to train models unless the user opts out in settings.
- The launch design still allows Meta to access data when operating the service. **Muse Confidential VM**, intended so Meta cannot access the VM, is described as later in 2026, with a small tester group already. It is not the launched default.
- A bug bounty pays up to US$300,000, including prompt-injection reports.

## New Computer’s Dot

This is the companion the latest request points at. It is not ChatGPT’s dot.

Sources: [new.computer](https://new.computer/) (winding-down note, Sam and Jason), [new.computer/dot](https://new.computer/dot), [Your data](https://new.computer/your-data), [TechCrunch, 21 June 2024](https://techcrunch.com/2024/06/21/dots-ai-really-really-wants-to-get-to-know-you/), [TechCrunch, 5 September 2025](https://techcrunch.com/2025/09/05/personalized-ai-companion-app-dot-is-shutting-down/), and Daniel Klein’s [design critique, 27 June 2024](https://diklein.com/writing/on-the-design-of-dot).

### Core features

The product page says Dot is a personal AI that “grows with you” and offers guidance for career, plans, and “a thoughtful ear.” The 2024 TechCrunch profile describes an iOS chat app whose onboarding asks about work, taste, and Sundays, then follows up on motivations. A paid **Chronicles** view summarizes the conversations. TechCrunch reported unlimited chat at US$11.99 per month, with a free tier capped by messages per week. Klein’s critique quotes onboarding copy that asks for notifications (“timely reminder and proactive messages”), calendar (“see what your day is like”), and location.

The 2025 TechCrunch report says the app was iOS only. Appfigures, cited there, counted about 24,500 lifetime iOS downloads, against the company’s “hundreds of thousands” of users. This teardown did not check either number.

What it does **not** claim in these pages: its own computer, a browser that clicks through the user’s accounts, plugins, or background work inside Gmail or a desktop app. Calendar and location are inputs to replies, not a published “operate the user’s apps” feature.

### Personality and conversation style

Co-founder Jason Yuan told TechCrunch it is “a living mirror,” not a replacement for friendship, and Sam Whitmore described it as a tool for self-introspection. The reported style is warm and inquisitive: it sympathizes, asks why a plan matters, and sometimes ends a conversation by suggesting the user do something else. Klein’s onboarding screens say “Living History” and that Dot may “surprise you with a birthday gift.” That is a companion voice. Desk Companion’s job is a desk agent plus a posture loop, not a confidant.

### Memory

Personalization is the product. TechCrunch says it learns from intensive questions and uses that to tailor advice. Chronicles are the subscriber’s longer view of those chats. The privacy page says deleting the account wipes data, and the shutdown note tells users to export via “Request your data.” No public page fetched here shows an editable memory file the way Muse’s safety article does.

### Proactivity

Klein records a notification permission whose purpose is reminders and proactive messages. The product pages fetched here do not describe a scheduler, event watches, or work that continues while the phone is off. Treat reminders as a claimed notification feature from the 2024 onboarding, not as a verified background agent.

### Multimodal input and voice

The privacy page lists messages, photo uploads, and voice memos as data the user provides, plus location and calendar to inform replies. TechCrunch’s 2024 profile reviews a text conversation. A live voice call was not described in the pages fetched this session.

### Hardware form factor

An iPhone app. No desk device, glasses, or always-on screen is described.

### Privacy, as published

The [commitments page](https://new.computer/your-data) says: data is not sold; messages, photos, voice memos, location, and calendar are used to inform replies and can be revoked; cloud storage with encryption at rest and in transit; only the user can read the chat; the company does not train models on user data; deleting the account wipes it. TechCrunch (June 2024) adds that the app called roughly ten models, including OpenAI, Anthropic, Google, and open-source models, and that the company said it would monetize by subscription rather than by selling data. The full legal privacy policy was not opened in this session. The homepage says a data export remains available until the shutdown date.

## ChatGPT “your dot”

This is the Dot the FYP owner asked the project to learn from on 3 October 2026. It is also the public product that matches a general agent which acts in apps. Docs fetched 14 October 2026: [Meet dots](https://learn.chatgpt.com/docs/dots.md) and [Tasks and memory](https://learn.chatgpt.com/docs/dots/tasks-and-memory.md). OpenAI’s privacy policy was not reviewed here.

### Core features

The docs call it an always-on agent, “powered by GPT-6 Astra,” with its own cloud computer and browser. It can research, analyze, prepare documents, and build software while the user’s PC is off. The same dot is reached from the ChatGPT mobile app, desktop app, or desktop browser, and from Slack or Microsoft Teams. Mobile web is not supported.

Plugins (the docs’ examples are Gmail, Google Drive, and GitHub) use the accounts the user has already connected. One personal computer can be connected at a time; it must be online with the ChatGPT app open, and that permission is separate from Codex. The cloud browser has its own sessions. Website login goes through a private form or a user takeover, not through the chat transcript. The user can take over the browser and hand control back.

It can start background agents, cloud threads, and Work or Codex tasks. A finished run is not, by itself, proof the result happened. Pause stops the current main task; scheduled work is cancelled separately. Ending a voice call does not necessarily stop assigned work.

Availability in the docs: gradual rollout; Pro plans for users over 18 outside the EEA, UK, and Switzerland; Business Premium and Enterprise more widely, with Enterprise off until an admin enables it. Conversations with the dot do not count toward ChatGPT usage limits; Work and Codex tasks it starts still count toward those products.

### Personality and conversation style

The user names it and sets shape, color, eyes, glasses, and accessories. It introduces itself and suggests help from available context. The documented tone is a work colleague that reports progress and asks for decisions, not a “living mirror.” Custom instructions can ask for drafts before sending. The docs say those instructions do not override built-in safety checks.

### Memory

Three layers, as the tasks page separates them: the current conversation (a selection, and a call can see a different selection than a background task), relevant ChatGPT memory, and the dot’s own notes on preferences, decisions, and ongoing work. Those notes are not a full transcript and are not the same store as ChatGPT’s saved memory. Changing a ChatGPT memory setting does not necessarily edit notes the dot already wrote. Slack, Teams, and ChatGPT reach the same notes, but a message in one channel is not copied into another, and private details are not shared onward unless the user has allowed it. A connected computer does not expose every chat in every app.

### Proactivity

The user can assign an ongoing responsibility and let the dot choose when to pause and resume. Fixed times need an explicit schedule: what to do, time zone, end date, which changes deserve a message, and where to deliver it. Event monitoring exists only where a connected service supports it, and connecting the service does not by itself start a watch. **Proactive research is read-only.** It can keep private notes and then suggest a next step. It does not itself send messages, change apps, or drive a browser. Any follow-up still needs the permission for that action.

### Multimodal input and voice

The user can message or place a voice call from the phone button in the dot’s ChatGPT conversation, and can type during the call. Work continues after the call ends. Files, plugins, and the browser are the other modalities named. No wake word or always-open microphone is described.

### Hardware form factor

No dedicated device. The clients are ChatGPT’s apps plus Slack and Teams, with an optional connection to one of the user’s computers.

### Privacy, as the product docs describe it

Credentials for a website go to the browser outside the conversation. Using a saved login needs confirmation. Each plugin, the local computer, and each messaging channel are separate grants. Review decides whether an action can proceed, needs approval, or must be handed to the user. This note does not state how long OpenAI keeps transcripts or whether those chats train models; that would require the privacy policy, which was not the source used here.

## A general personal agent, from these public products

The pattern below is what Muse and ChatGPT’s dot both publish. New Computer’s Dot shares only the memory-and-reminder half, and its company has said it is shutting down. Desk Companion should copy the **shape of the promises**, not the vendor UX or the prompt.

1. **One ongoing relationship.** The user returns to the same agent. Side threads are optional. Ending a call does not delete the task.
2. **Memory the user can correct.** Saved notes or files, separate from the full transcript, with a way to edit, forget, or export. Ranking stays the product’s choice; the FYP version should store a source and a time for every fact.
3. **Tools with a grant.** Connecting chat is not connecting email. Read is not write. The model proposes; a separate check allows, asks, or refuses. A model sentence is not a receipt.
4. **Work that survives the conversation.** A clock, and only sometimes an event, wakes the agent. The user can pause the task without pausing the whole product. Research that the user did not authorize to act stays read-only.
5. **A visible character.** Name, face, and tone help the user tell the agent from a generic chat. They do not grant extra permissions.
6. **Speech as a front end.** Voice is how some products listen. The durable job is still the task record.

## Gap against Desk Companion on `main`

Baseline: merged Desk Companion as reviewed in [fyp-repo-review.md](fyp-repo-review.md). Providers default to `none`. The notes job is off until `DESK_COMPUTER_ENABLED` is set. PR #5’s memory, routines, and browser fixtures are not on `main`.

| Capability | Meta Muse (published) | ChatGPT dot (docs) | New Computer Dot (published) | Desk Companion on `main` |
|---|---|---|---|---|
| Acts in the user’s apps | Cloud computer, browser, connectors, purchases with approval | Cloud computer, one local PC, plugins, Codex/Work tasks | Not described; calendar and location inform replies | One bounded notes file under `computer-notes/`, default off. No inbox, browser, or shell. |
| Memory | Editable memory files in the user’s VM | ChatGPT memory plus the dot’s own notes, not a full transcript | Personalization and paid Chronicles; export and account delete | Tasks and evidence. No general fact list the owner can edit. |
| Background work | Continues on a schedule and on events after the app closes; high bar before it messages | Agent chooses when to resume; schedules and event watches are explicit; proactive research does not itself message or act | Notification permission for reminders; no published off-phone worker | 1-second rules loop. Optional text advice is off, at most every 30 seconds, 20 attempts a day, and only when a follow-up is due. |
| Proactive reminder | Yes, and the user can turn it down or off | Yes, by responsibility, schedule, or event; delivery channel is chosen | Claimed in 2024 onboarding copy | Local task reminders and calendar reminders. No model-written nudge unless the capped advice loop is enabled. |
| Voice | Not established as a call in the pages fetched | Call inside ChatGPT; typing during the call; hang-up need not stop the task | Voice memos as uploaded data; live call not established | Qwen Audio and Gemini Live adapters, local wake word, 600-second cap, 45-second idle, audio not stored. Default provider `none`. |
| Persona | User-named avatar; one published purpose line | User-named face; work-colleague instructions | “Living mirror,” sympathetic questions | One hardcoded “You are Desk Companion…” string in the text and voice adapters. A1 art is on unmerged PR #4. |
| Hardware | Phone, web, WhatsApp; glasses claimed as coming soon on WebWire | Phone and desktop apps; optional PC | iPhone app | The product **is** a desk terminal: shared API, separate always-on screen, fixed camera, named light and motion presets. That form factor is ours. None of the three products replace the posture loop. |
| Privacy controls we can actually ship | Their VM, Sentinel, and training opt-out are Meta’s. We do not host a copy. | Their plugin grants are OpenAI’s. | Their cloud chat is New Computer’s, and the service was announced as ending. | Keys stay in server env vars. Drafts expire. The model cannot confirm a write. Camera frames and the SQLite file are not the prompt. |

The useful gaps are memory the owner can correct, one named action beyond a notes file, and a scheduler that stays quiet unless something is due. A cloud VM, a general browser, inbox access, and a companion personality are not the next prototype.

## Implementation roadmap

Constraints, already decided in [companion-architecture.md](companion-architecture.md):

- Hosted LLM and hosted speech only. Do not self-host Glimmer, llama.cpp, vLLM, or Ollama as the assistant.
- The team owns memory, tool checks, the scheduler, the persona text, and the voice session.
- Engineering suggestion, not an owner lock: first paid trial is Qwen text plus short Qwen Audio sessions; Gemini 3.8 Live is the comparison if the account can call Google. Leave `DESK_TEXT_PROVIDER` and `DESK_VOICE_PROVIDER` at `none` until the owner sets a spend cap.
- Do not merge PR #4 or PR #5. PRs #7–#14 already add memory and one folder action on `main`’s note-job contract. Do not move that work onto PR #5, and do not open a second job system.
- Do not decompile Muse, ChatGPT, WhatsApp, or the New Computer app. A client binary cannot show the hosted model; see [companion-architecture.md](companion-architecture.md).

Suggested stack, all already compatible with the repo or available as normal open-source libraries:

| Piece | Use | Do not add |
|---|---|---|
| FastAPI, SQLite, the existing asyncio loops | One process, one database, rules on the 1-second tick | A second scheduler service, Redis, or a queue that calls the model on a timer |
| SQLite FTS5 | Search owner-saved facts and task evidence locally | A local embedding model, or uploading the database to a vendor |
| Existing tool schema in `desk-companion/backend/desk/assistant.py` | Model proposes a typed draft; our code checks owner, version, and expiry | A tool the model can use to confirm its own write |
| `sherpa-onnx` wake word, already integrated | Opens a short hosted audio session | An always-open paid socket |
| MediaPipe posture path, already integrated | Local labels only | Asking the LLM to invent a posture score |
| Playwright, only if the owner names a fixture | A later test page **this team hosts** | A general web agent, or driving Gmail, banks, or Muse |

### Tasks a teammate or Codex can pick up

Each task should name its branch (`main` or PR #5) in the patch. One task at a time.

1. **Persona file (small, `main`).** Move the instruction strings in `desk-companion/backend/desk/text_ai.py` and `voice.py` into one versioned text file. English by default, Simplified Chinese when the user is speaking Chinese, no medical claims, no self-approval. Done when both adapters send that file and a test fails if the API key or a camera frame appears in the outbound body. Do not paste Muse’s purpose line or Dot’s “living mirror” copy.
2. **Context packer test (`main`, no live HTTP).** The recorded Qwen or Gemini request contains the persona and the selected task, and omits deleted task text. Use the fake transport the tests already have.
3. **Quiet scheduler test (`main`).** The 30-second advice loop does not construct a model client when the provider is `none`, the daily cap is spent, or no follow-up is due. The 1-second loop stays rules only.
4. **Editable facts, only if PR #5 is the target.** On that branch, memory already has a reviewed design. A `main` patch should not add a parallel table. If the owner wants it on `main` first, the minimum row is: text, source (user said this), time, corrected-by, deleted-at. Retrieval is a SQL query we write. The model may propose a fact; the owner confirms it. Deletion removes it from the next prompt.
5. **One real action (product’s next step).** The owner names one folder or one test app. Approval binds the full text. Independent read-back (size, hash, or the app’s own receipt). A lost receipt stays `unknown` and is not replayed. A second approval does not write twice. Do not add a shell tool.
6. **Voice session rules, fake provider.** A partial transcript cannot approve a job. Closing the socket does not cancel a job the owner already approved. Real microphones, Cantonese, and invoices wait for a key and a cap.
7. **Reminders the user can turn down.** For an existing task follow-up, add a per-task “quiet” setting that suppresses the optional text advice without deleting the task. This is the FYP-sized version of Muse’s proactivity dial and of ChatGPT dot’s “message me only if a deadline is at risk.” It is not a new model loop.
8. **Hardware, parallel.** A named light or arm preset behind the current output queue, with a local stop that does not ask the LLM. Posture accuracy still needs consented labels before anyone cites the proposal’s target. RIG-Arm stays a researched candidate until it is purchased and driven.
9. **Provider trial, after a cap.** Recheck region, model id, and price. Run the proposal’s style of Mandarin and English commands on Qwen, then Gemini if reachable. Log usage from the provider. Do not treat the September 2026 dollar examples as a bill.

## What not to claim

A public product page is not a measurement of Muse’s or Dot’s success rate. New Computer’s download figures disagree with each other in the TechCrunch report; neither is our result. Desk Companion has not had a paid listening test, a Pi run, or a general computer-use demo. Local notes are not inbox access. This document does not submit the school proposal, choose a vendor, or approve a purchase.

## Sources

Fetched 14 October 2026 unless noted.

- Meta, [How We Designed Muse](https://introducing.muse.ai/), September 2026.
- Meta AI Research, [How We Built Safety Into Muse](https://research.meta.ai/blog/security-and-safety-for-ai-agents-our-approach-with-muse), 8 September 2026.
- WebWire reprint, [Introducing Muse](https://www.webwire.com/ViewPressRel.asp?aId=360321), 10 September 2026. Secondary. Glasses and the free-plus-subscription line are from this reprint only.
- New Computer, [winding-down note](https://new.computer/), [Meet Dot](https://new.computer/dot), [Your data](https://new.computer/your-data).
- Sarah Perez, TechCrunch, [Dot’s AI really, really wants to get to know you](https://techcrunch.com/2024/06/21/dots-ai-really-really-wants-to-get-to-know-you/), 21 June 2024.
- Sarah Perez and Maxwell Zeff, TechCrunch, [Personalized AI companion app Dot is shutting down](https://techcrunch.com/2025/09/05/personalized-ai-companion-app-dot-is-shutting-down/), 5 September 2025.
- Daniel Klein, [On the Design of Dot](https://diklein.com/writing/on-the-design-of-dot), 27 June 2024.
- OpenAI, [Meet dots](https://learn.chatgpt.com/docs/dots.md) and [Tasks and memory](https://learn.chatgpt.com/docs/dots/tasks-and-memory.md).
- Group 2, [Your dot feasibility baseline](../../research/2026-10-03-dot/proactive-task-tracking.md), 3 October 2026.
