# Group 2 · Personal agent delivery status

Checked 16 November 2026 (Hong Kong). This is a capability and acceptance map, not a completion percentage. The goal remains a personal assistant that follows responsibilities and completes real work across applications. [Research and user journeys](../../research/personal-agent-research-index.md).

## Source, runtime and evidence

GitHub main remains6153b41d, containing the reviewed Grok integration through PR121/122. A fresh fetch and GitHub PR metadata confirmed that PR123 is the only open PR; it contains Alice motion work. The connector issue-search result omitted that open PR, so the actual PR listing was checked with gh. The updated old conversation branch contains merge/documentation receipts already represented in the reviewed stack, not a newly deployed feature.

The ordinary Mac backend is still the retained520ab563 implementation. Later Alice presentation changes were delivered as compatible frontend overlays. Main's newer memory reminders, saved checklists/schedules, shopping preferences, offline trip quotes and local Work conversation extensions have not all been activated in this runtime. Code being merged is therefore insufficient evidence that the owner can use it in the running app.

The local app catalog was read on16November, without fetching private emails or sending mail: Gmail is configured and has a saved connected account; Google Calendar is configured but unconnected; Microsoft365, Teams and SharePoint are unconfigured/unconnected. There are zero configured public/synthetic MCP connectors in this runtime. A saved OAuth account is not a fresh provider-token validity test. No new model call, mail send, merchant login or transaction was performed for this status check.

## Delivery map

| Capability | Implemented / established evidence | Remaining gap |
|---|---|---|
| Conversation, local calendar/tasks, permissions | Shared text/voice tool catalog, Ask first/Full access, versioned proposals, local calendar/task CRUD and recovery; dated provider and application trials exist | Reliable end-to-end human voice use, latency/interruption and long-running cross-device use still need acceptance |
| Persistent goals and memory | Durable Work/tasks, approved memory, artifacts and explicit continuation. Main additionally contains approved memory follow-ups, local checklists and status answers | The normal runtime is behind main; the full task is not autonomously planned, executed and revisited without explicit continuation |
| Gmail read/send | Official browser OAuth and reviewed sending are implemented. FYP itself sent one exact self-test email and independently read it back on8November | Current saved connection was checked locally only; continuous real inbox ingestion, thread-to-task updates and useful ongoing suggestions remain unaccepted |
| Google Calendar / Microsoft apps | Google calendar adapter and Microsoft Graph mail/calendar/directory/To Do/OneNote/Teams/SharePoint adapters with local protocol tests | Google Calendar consent and Microsoft client/account authorization remain incomplete. Word/Excel/PowerPoint cloud support is file metadata, not arbitrary document editing |
| Office application work | Actual Chromium/Calc/Writer/PDF and file readback/change/recovery paths were exercised with scripted planning | Full unseen multi-application tasks under real-model planning and speech are not established by those scripted trials |
| Browser computer use | Native computer-call protocol, real mouse/keyboard observations, durable job/evidence and cancellation.31real model requests on7November covered explicitly fictional shopping/flight tasks and follow-up/calendar handling | Shipped browser uses fresh public state and constrained requests. Private authenticated sessions and general host-desktop control remain outside this accepted scope |
| Shopping | Controlled price/quantity/coupon/shipping cases passed with a real model; real JD reached a verification wall | Real account login, owner-controlled browser takeover, real product/stock/address handling, checkout/payment and independent order receipt are not complete |
| Travel / tickets | Controlled dates, passengers, baggage, total costs, timezones and calendar follow-up passed | Actual live fares, passenger authorization, reservation/payment/ticket issuance and later changes are not verified. Cathay's real page failed to load in the dated trial |
| Background assistance | Existing rules, quiet hours, delayed checks and notifications; offline mail/shopping/calendar fixtures update the same task | Real mailbox incremental sync, reliable unattended goal continuation and verified phone notifications when closed remain open |

## Why complex tasks still stop early

The normal text `AgentLoop` currently allows at most three tool steps and45seconds; writes/proposals end the turn. The computer-use loop has a separate bounded run. Main's explicit Work continuation does not turn either path into a persistent autonomous goal worker.

The reviewed browser correctly pauses at a login/OTP/payment wall. However, its shipped headless worker has no owner-input transport. The positive takeover tests use a synthetic driver; production gates reject unavailable takeover/return rather than displaying a nonfunctional control. This is the immediate missing connection for an actual account journey, not a missing model name or a prompt-only problem. [Browser contract](computer-use.md), [app connections](connected-apps.md).

## Next engineering slice

Build a real owner-controlled browser view on the existing JobService lifecycle: open the same paused browser, suspend model observation/input during owner control, let the owner complete authentication, explicitly return it, and independently verify that the wall is gone before continuing. Keep cancellation, deadlines, session ownership and operation versions effective. Do not create another task queue or copy ordinary browser credentials into model context.

After that slice, close one authorized real mail-to-task-to-suggestion journey and one merchant order-preparation journey. Actual purchase/payment/ticketing needs its concrete transaction details and appropriate authorization. Continue distinguishing software implementation, mock tests, real provider observations and delivered runtime versions. This is an engineering priority proposed from the current gaps, not new permission to send mail or buy anything.
