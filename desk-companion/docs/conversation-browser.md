# Group 2 · Browser research from conversation

17 November 2026. Text and voice can prepare public browser work through the shared tool registry. The owner reviews the exact sites and task, explicitly permits cloud processing of task/screenshots, and starts the existing job. Follow-up questions reopen current evidence. [QA](../../output/qa/2026-11-17-personal-agent-browser/verification.md).

## Ownership and lifecycle

- `browser_research.py` owns draft validation, translating an approved proposal into a browser job, and bounded result projection. It reuses `ComputerUseInput`, `assistant_proposals`, JobService and executor verification. It creates no new task store, provider client, queue or planner.
- `browser_research_draft` is a draft-only tool. Arguments cannot supply screenshot consent, approval or a larger step budget. HTTPS scope/task/source validation uses the existing browser model. Explicitly requested `demo:` pages remain visibly fictional; they are never real prices/orders.
- `browser_research_status` takes the returned proposal ID. It reports pending/cancelled/expired/running/needs-owner state and, when a successful record exists, independently verifies receipt, screenshot/state hashes and current session/provider/privacy fences before returning bounded page text or the managed report. Those texts remain untrusted data. `goal_completed` and `transaction_confirmed` stay false.
- AssistantService retains proposal expiry/cancel/confirmation serialization. A reviewed browser request is not in automatic software-proposal permission, including Full access: cloud screenshot sharing still needs the explicit owner action. No model confirmation tool exists.
- The existing authenticated decision endpoint requires `share_screen: true` for the new browser kind. Preparation and approval use durable proposal-derived operation keys. A retry after either phase recovers the same job; a cached original chat response refreshes that job instead of reviving the old approval card. Cancelling an interrupted pre-approval draft also cancels its remaining review job.
- BrowserResearchReview owns the compact review UI. AssistantPanel keeps its existing proposal/job reads and conversation refresh. No per-card polling is introduced. Consent resets for each proposal. A lost approval response uses the existing pending-write record/key; recovery is not shown while the request is still being submitted.

The browser request is capped at eight steps. `managed` is now the default in new drafts/current admission; an operator can explicitly disable it. Local execution/fixtures and verified local source-job continuation remain explicit choices. A managed task can pause for an owner-only registered sign-in form and continue the same turn, with separate per-task account-read consent. It does not attach the owner's ordinary browser profile or retain account sessions across jobs. [Official mainline contract](managed-browser.md).

## Text tool parity

The old separate TextPlan literal omitted ten already registered software/read tools: email status/drafting, connected-app queries, weather, five application tools and device status. Text tool names now derive from the registry's explicit `text` flag. Physical feedback/stop and posture remain outside that text catalog, preserving their prior channel scope. Existing tool-level owner checks, mail review, folder scopes and provider adapters remain authoritative.

This exposes existing software abilities; it does not create Google/Microsoft grants or authorize a new send. The opt-in retained-chat endpoint keeps its existing narrower catalog and gains only the two browser tools with the same business-context consent gate.

## Verification and remaining acceptance

Real installed Chromium, production worker, production HTTP/UI flows and independent file/SQLite checks ran against fictional shopping/flight sites. Model decisions were scripted and transports mocked. Desktop/phone checks covered initial consent, revised-price/quantity continuation, a follow-up task, flight baggage/date/arrival arithmetic, cancellation and lost-approval-response recovery with one unchanged operation key and one job.

The new live model routing, spoken naturalness/latency and real merchant/account/transaction behavior have not been accepted in this round. No paid model call, real mail, order or ticket was generated. Production Mac/native/Pi activation is separate from this checked source/isolated QA environment. Backend and shared frontend must be promoted together; an older client without the explicit sharing field cannot approve the new browser proposal.

Current update: the official registered-form path now supports same-task sign-in and continuation, tested with synthetic forms and transport. Actual merchant sign-in, unsupported QR/passkeys/CAPTCHA, signed-in comparison and transaction receipts still need specific real acceptance; protocol fixtures do not establish those outcomes.
