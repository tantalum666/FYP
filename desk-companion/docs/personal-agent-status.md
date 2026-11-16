# Group 2 · Personal agent delivery status

Checked16November2026 (Hong Kong). A capability/acceptance map, not a completion percentage. [Research](../../research/personal-agent-research-index.md), [current QA](../../output/qa/2026-11-16-agent-runtime/verification.md).

## Current source and runtime

PR123 merged as7d7ab9fa. The full baseline, including reviewed Grok Work/memory/checklist/shopping/travel additions and Alice motions, is activated on normal Mac and Pi backends; native Simulator embeds the same frontend. This supersedes the earlier16November claim that ordinary runtime was still behind main. Stores were rehearsed/backed up first and A3 retained. New managed-executor publication/activation receipts are recorded separately in QA.

Mac Gmail and Calendar authorization were renewed by the owner; Pi subsequently received separate consent. All four grants passed real provider GETs. Microsoft personal-account login stopped at human verification, so no FYP app registration or Graph grant is claimed. Codex plugin access is a separate grant.

## Delivery map

| Capability | Established evidence | Remaining gap |
|---|---|---|
| Conversation, calendar/tasks, permissions | Shared text/voice tools, owner approval/Full access, versioned proposals, local CRUD and recovery | Reliable long-running human voice use, latency/interruption and cross-device failure coverage |
| Persistent goals and memory | Durable Work, approved memory/reminders, saved checklists/schedules, artifacts and explicit continuation; full baseline delivered | Autonomous ongoing goal execution and revisiting is not established by explicit continuation |
| Gmail | 8November native self-send/readback;16November Mac/Pi fresh grants/profile reads | Continuous real inbox ingestion, thread-to-task updates and useful ongoing suggestions |
| Google Calendar | Mac/Pi consent plus bounded actual primary-calendar reads | A complete incremental external-sync journey |
| Microsoft apps | Graph mail/calendar/OneDrive directory/To Do/OneNote/Teams/SharePoint adapters and offline tests | App registration, account consent and live provider acceptance; file metadata is not Word/Excel/PowerPoint editing |
| Office operations | Real Chromium/Calc/Writer/PDF scripted execution and independent file verification | Unseen complex tasks under real-model/speech planning |
| Local computer use | Native computer protocol, actual browser actions, durable job/evidence, cancellation;7November real-model fictional shopping/flights | Fresh public browser only; real owner-input transport and authenticated continuation are absent |
| Official managed browser | One actual hosted session compared public book prices; independent readback/deletion passed. New FYP adapter shares existing jobs and passes local protocol/UI tests | Adapter remains opt-in/off; no paid integrated FYP/voice/cancel acceptance. No personal browser, credentials or merchant checkout attached |
| Shopping | Real-model controlled price/quantity/coupon/shipping tests; current public catalogue comparison | Real account/product/stock/address checkout, payment and independent order receipt |
| Travel/tickets | Controlled dates/passengers/baggage/cost/timezone/calendar follow-up | Actual fares, authorized passenger/booking/payment/ticket issuance and later changes; prior Cathay load failed |
| Background assistance | Quiet hours, delayed rules/checks, offline fixture updates and local notifications | Real mailbox incremental tracking, unattended task continuation and closed-phone notifications |

## Execution direction

Live already supports Responses delegation. Official Agents supplies a managed Codex harness; App Server/SDK are alternatives for a local custom client. Reuse those capabilities instead of adding another generic agent planner. FYP still owns authorization, task identity, business state, account grants and verified outputs. [Official source review](../../research/2026-11-16-official-agent-runtime.md).

The current browser-job form is owner-admitted. The ordinary `computer_job_draft` text/voice tool still prepares bounded note operations; it does not automatically admit the new managed browser. The text loop's three-step/45-second limit and explicit Work continuation remain. Trusted speech/conversation-to-browser admission needs wiring and testing, not just a new model name.

Next: connect that admission to the existing review flow, then add real same-browser owner control/explicit return before authenticated merchant work. Hosted origin approval is not a hard payment gate. Keep cancellation, session/version checks and independent order/ticket evidence; no fresh spending, mail send or purchase is authorized by this roadmap.
