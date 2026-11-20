# Group 2 · Browser research from conversation

## Public shopping and flight prices

For a flight search open to multiple sellers, Alice can select the Kiwi.com provider in the existing draft. The review identifies the supplier, party, itinerary, checked weight and any requested nonstop filter. Its decision is `share_itinerary`. The official OpenAI session has no browser or screenshot tool and admits only `search-flight` on the supplier's MCP server. Explicit airline-only requests retain the existing browser path. A completed supplier tool result must match the approved arguments, airports, dates, party and currency. Alice displays the observed price, included bag count, seller handoff and terms. A quoted subtotal already above the budget is sufficient to report that outcome. The operator must preserve an unknown weight or fee until the actual offer supplies it. [Live evidence](../../output/qa/2026-11-19-flight-ledger/verification.md).

A managed browser draft can carry an optional `quote_request`. Shopping specifies the product, selling-unit count and delivery or pickup. Flight research specifies exact airports, outbound and optional return dates, adults and checked kilograms per adult. A currency and spending limit can be supplied together. The ordinary text and Live registry share this draft. The owner sees those values before consenting to cloud screenshot processing. An omitted quote retains the previous generic research contract.

For a quote, the official session returns a typed observation with the admitted source page, displayed price and price basis. Unknown mandatory charges remain unset. The desk checks the currency before comparing a landed total to the owner's budget. It requires matching retail units or a matching trip, sufficient baggage, availability and documented full mandatory charges for that total. Advertised minima and unrelated itineraries retain their displayed basis. When the site supplies no fare, the owner can reopen the admitted website. The observation time belongs to the recorded lookup.

The result card and status Function use the existing job receipt. On an ordinary follow-up the desk resolves the recent proposal in that owner's temporary conversation and verifies the original evidence before supplying amounts. A different conversation, changed evidence or hidden private context cannot supply those amounts. Buying or reserving still requires a separate, explicitly supported transaction and independent receipt. [Implementation and acceptance](../../output/qa/2026-11-19-shopping-flight/verification.md).

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
