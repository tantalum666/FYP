# Group 2 · Personal agent delivery status

Checked 19 November 2026 (Hong Kong). [Research](../../research/personal-agent-research-index.md) · [integration QA](../../output/qa/2026-11-17-proactive-agent-merge/verification.md) · [three-endpoint deployment](../../output/qa/2026-11-18-three-end-rollout/verification.md).

## Current source and runtime

The normal Web, native Simulator and original Pi release is `85e6aa94`. Ordinary text, managed browsing and Live delegation use GPT‑6.2 Sol. Speech uses GPT‑Live 1 with A3 v9. The Pi’s screen and Google grants were verified on the device. Actual shopping and flight searches have separate provider evidence. [Pi release](../../output/qa/2026-11-19-pi-release/verification.md) · [Web, Simulator and live flight lookup](../../output/qa/2026-11-19-flight-ledger/verification.md).

The source branch now sends ordinary OpenAI text and follow-ups through official Sessions with application Functions. The shared Web composer and the batched, quiet-hours-recovery journey passed with scripted providers. The preceding baseline was `c607759e`. [Contract](official-text-sessions.md) · [QA](../../output/qa/2026-11-18-official-text-sessions/verification.md).

The reviewed integration [PR129](https://github.com/tantalum666/FYP/pull/129) is merged atc51ece41 with all original124–128 PRs confirmed merged. Its tree matches the tested42bc01ec candidate. It includes contextual proactive research: current facts/tasks/calendar and authorized previews, no per-item read approval, changed-source relevance/citations, silence/dedupe, quiet/off controls and fresh request-based mail follow/stop. It directly uses official Responses structured output, not AgentLoop. The existing official browser client now handles actual readiness, setup timing and cancellation/deletion behavior found during live testing. [Proactive contract](proactive-research.md), [browser contract](managed-browser.md).

Six real Responses research cases, two real-model natural-language mail turns over synthetic mail, and one successful multi-page public hosted-browser trial passed. Three earlier browser failures and two response timeouts are retained. All four hosted sessions have404 deletion readback. This slice did not activate a real mailbox subscription, send mail, trade or deploy to normal runtimes. Final GitHub status and test counts are in the QA/handoff; no completion percentage is inferred from test counts.

The 17 November official-mainline branch now defaults conversational/current-browser work to the official managed executor and adds registered owner sign-in within the same task. SSE recovery reads the original session/turn; it does not replay input. Full backend2,428/frontend391 and real desktop/phone synthetic-provider sign-in/recovery/result journeys passed. Original conversation browser work and software-tool parity are included. [Current execution contract](managed-browser.md), [QA and delivery evidence](../../output/qa/2026-11-17-official-mainline/verification.md).

Latest16November slice: shared weather_query, voice presentation/buffering, proactive task cues and browser-local posture capture are implemented with actual HKO, local-model, physical Mac input and UI evidence. [Daily-presence contract](daily-presence.md) / [QA](../../output/qa/2026-11-16-alice-daily-presence/verification.md). Complete A3 weather speech and long-running posture accuracy remain unaccepted; activation receipts must be checked before attributing these changes to an endpoint.

The 18 November rollout replaced `8c67ddbe` with `c607759e` on Mac Web, the iPhone 17 Pro Simulator and the Raspberry Pi. The installed native bundle matches the Web frontend and uses its saved Mac backend. The Pi autostart entry selects this release, and a capture from its own compositor shows Alice connected. A3 version 9 is preserved. The physical iPhone was deferred and the Pi power investigation remains paused. [Release readback](../../output/qa/2026-11-18-three-end-rollout/verification.md).

On 18 November the existing Mac and Pi grants independently returned HTTP 200 for the Gmail profile and primary Calendar. Each Gmail identity matched its own stored account. Microsoft 365, Teams and SharePoint remain unconfigured and disconnected on both servers. The previous Microsoft registration stopped at human verification.

## Delivery map

| Capability | Established evidence | Remaining gap |
|---|---|---|
| Conversation, calendar/tasks, permissions | Shared text/voice tools, owner approval/Full access, versioned proposals, local CRUD and recovery | Reliable long-running human voice use, latency/interruption and cross-device failure coverage |
| Persistent goals and memory | Durable Work, approved memory/reminders, saved checklists/schedules, artifacts and explicit continuation; full baseline delivered | Autonomous ongoing goal execution and revisiting is not established by explicit continuation |
| Gmail | 8November native self-send/readback;16November Mac/Pi fresh grants/profile reads;17November primary text catalog now exposes the existing email status/draft tools | Selected-thread updates/reply now have local protocol/UI evidence; actual continuous thread acceptance and full-inbox ingestion remain open; bounded contextual suggestions have separate real-model/synthetic-mail evidence |
| Google Calendar | Mac/Pi consent plus bounded actual primary-calendar reads | A complete incremental external-sync journey |
| Microsoft apps | Graph mail/calendar/OneDrive directory/To Do/OneNote/Teams/SharePoint adapters and offline tests | App registration, account consent and live provider acceptance; file metadata is not Word/Excel/PowerPoint editing |
| Office operations | Real Chromium/Calc/Writer/PDF scripted execution and independent file verification | Unseen complex tasks under real-model/speech planning |
| Local computer use | Native computer protocol and durable jobs;17November real Chromium chat-to-review-to-result/continuation and follow-up-task flows passed with scripted model decisions | Fresh public browser only; real owner-input transport and authenticated continuation are absent |
| Official managed browser | New default route; registered owner sign-in and same-job continuation; bounded stream/turn recovery and cleanup; full protocol/desktop/phone fixture evidence | Integrated public multi-page live trial passed; actual merchant accounts and unsupported sign-in methods remain open; no checkout/payment/ticket claim |
| Shopping | Real-model controlled price/quantity/coupon/shipping tests; current public catalogue comparison | Real account/product/stock/address checkout, payment and independent order receipt |
| Travel/tickets | Controlled dates/passengers/baggage/cost/timezone/calendar follow-up | Actual fares, authorized passenger/booking/payment/ticket issuance and later changes; prior Cathay load failed |
| Background assistance | Quiet hours, delayed rules/checks, offline fixture updates and local notifications | Changed-source research and standing read-only selected-thread tracking are implemented and locally/real-model tested. Sustained real-mail acceptance, full-inbox events, unattended multi-step goals and closed-phone delivery remain open |

## Execution direction

Live already supports Responses delegation. Official Agents supplies a managed Codex harness; App Server/SDK are alternatives for a local custom client. Reuse those capabilities instead of adding another generic agent planner. FYP still owns authorization, task identity, business state, account grants and verified outputs. [Official source review](../../research/2026-11-16-official-agent-runtime.md).

The current browser-job form is owner-admitted. The ordinary `computer_job_draft` text/voice tool still prepares bounded note operations; it does not automatically admit the new managed browser. The ordinary session responder allows three calls per request under a 45-second work deadline. Explicit Work continuation remains available. The new browser_research_draft/status pair supplies that missing review/result bridge, with explicit owner cloud consent and same-job retry recovery. Live speech/model behavior still needs separately authorized acceptance.

The original read-only clock acceptance and subsequent normal release are tracked separately. Mac and Simulator have the 6.2 Sol configuration. The Pi package awaits the original device. [Current evidence](../../output/qa/2026-11-18-sol62-deployment/verification.md).
