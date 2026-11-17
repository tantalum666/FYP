# Group 2 · Personal agent delivery status

Checked 17 November 2026 (Hong Kong). A capability/acceptance map, not a completion percentage. [Research](../../research/personal-agent-research-index.md), [current QA](../../output/qa/2026-11-17-personal-agent-browser/verification.md).

## Current source and runtime

The 17 November official-mainline branch now defaults conversational/current-browser work to the official managed executor and adds registered owner sign-in within the same task. SSE recovery reads the original session/turn; it does not replay input. Full backend2,428/frontend391 and real desktop/phone synthetic-provider sign-in/recovery/result journeys passed. Original conversation browser work and software-tool parity are included. [Current execution contract](managed-browser.md), [QA and delivery evidence](../../output/qa/2026-11-17-official-mainline/verification.md).

Latest16November slice: shared weather_query, voice presentation/buffering, proactive task cues and browser-local posture capture are implemented with actual HKO, local-model, physical Mac input and UI evidence. [Daily-presence contract](daily-presence.md) / [QA](../../output/qa/2026-11-16-alice-daily-presence/verification.md). Complete A3 weather speech and long-running posture accuracy remain unaccepted; activation receipts must be checked before attributing these changes to an endpoint.

PR123 merged as 7d7ab9fa. Mac and native Simulator now run8c67ddbe with verified bundle/index/backend parity, original data/grants/A3 retained. Pi was subsequently activated/read back at8c67ddbe, including a later boot, with data/A3/grants retained. All three have the same application source; Pi availability remains intermittent under the separately tracked wake/power issue.

Mac Gmail and Calendar authorization were renewed by the owner; Pi subsequently received separate consent. All four grants passed real provider GETs. Microsoft personal-account login stopped at human verification, so no FYP app registration or Graph grant is claimed. Codex plugin access is a separate grant.

## Delivery map

| Capability | Established evidence | Remaining gap |
|---|---|---|
| Conversation, calendar/tasks, permissions | Shared text/voice tools, owner approval/Full access, versioned proposals, local CRUD and recovery | Reliable long-running human voice use, latency/interruption and cross-device failure coverage |
| Persistent goals and memory | Durable Work, approved memory/reminders, saved checklists/schedules, artifacts and explicit continuation; full baseline delivered | Autonomous ongoing goal execution and revisiting is not established by explicit continuation |
| Gmail | 8November native self-send/readback;16November Mac/Pi fresh grants/profile reads;17November primary text catalog now exposes the existing email status/draft tools | Continuous real inbox ingestion, thread-to-task updates and useful ongoing suggestions |
| Google Calendar | Mac/Pi consent plus bounded actual primary-calendar reads | A complete incremental external-sync journey |
| Microsoft apps | Graph mail/calendar/OneDrive directory/To Do/OneNote/Teams/SharePoint adapters and offline tests | App registration, account consent and live provider acceptance; file metadata is not Word/Excel/PowerPoint editing |
| Office operations | Real Chromium/Calc/Writer/PDF scripted execution and independent file verification | Unseen complex tasks under real-model/speech planning |
| Local computer use | Native computer protocol and durable jobs;17November real Chromium chat-to-review-to-result/continuation and follow-up-task flows passed with scripted model decisions | Fresh public browser only; real owner-input transport and authenticated continuation are absent |
| Official managed browser | New default route; registered owner sign-in and same-job continuation; bounded stream/turn recovery and cleanup; full protocol/desktop/phone fixture evidence | Fresh integrated live acceptance, actual merchant accounts and unsupported sign-in methods; no checkout/payment/ticket claim |
| Shopping | Real-model controlled price/quantity/coupon/shipping tests; current public catalogue comparison | Real account/product/stock/address checkout, payment and independent order receipt |
| Travel/tickets | Controlled dates/passengers/baggage/cost/timezone/calendar follow-up | Actual fares, authorized passenger/booking/payment/ticket issuance and later changes; prior Cathay load failed |
| Background assistance | Quiet hours, delayed rules/checks, offline fixture updates and local notifications | Real mailbox incremental tracking, unattended task continuation and closed-phone notifications |

## Execution direction

Live already supports Responses delegation. Official Agents supplies a managed Codex harness; App Server/SDK are alternatives for a local custom client. Reuse those capabilities instead of adding another generic agent planner. FYP still owns authorization, task identity, business state, account grants and verified outputs. [Official source review](../../research/2026-11-16-official-agent-runtime.md).

The current browser-job form is owner-admitted. The ordinary `computer_job_draft` text/voice tool still prepares bounded note operations; it does not automatically admit the new managed browser. The text loop's three-step/45-second limit and explicit Work continuation remain. The new browser_research_draft/status pair supplies that missing review/result bridge, with explicit owner cloud consent and same-job retry recovery. Live speech/model behavior still needs separately authorized acceptance.

Next: verify the official primary route with an authorized real session, then a selected merchant's supported owner sign-in and read-only continuation. Hosted origin approval is not a hard payment gate. Keep cancellation, session/version checks and independent order/ticket evidence; no fresh spending, mail send or purchase is authorized by this roadmap.
