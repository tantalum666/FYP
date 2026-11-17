# Group 2 · Official browser execution

17 November 2026. The owner explicitly requested the official execution path as the mainline. New conversation drafts and the current browser form now select the official managed executor by default. GPT Live remains the voice interface with Responses delegation; the official Agents service runs the browser task. FYP retains account/permission binding, task identity, result readback and the existing JobService. [Conversation contract](conversation-browser.md), [current QA](../../output/qa/2026-11-17-official-mainline/verification.md).

## Admission and compatibility

- `BrowserResearchDraft.engine` and the new `POST /api/computer/browser-tasks` default to `managed`. The current frontend submits an explicit engine; this is included in the immutable request hash. `DESK_MANAGED_BROWSER_ENABLED` defaults to enabled; an explicit `0` still disables it. Credentials, provider readiness, owner session, private-context visibility and sharing consent remain required. Unavailability never silently selects local execution.
- Legacy `POST /api/computer/computer-use/jobs` and `ComputerUseInput` keep their omitted-engine local default. Old requests, operation retries, backups and local source-job continuation preserve their original bytes and executor identity. Local Chromium remains an explicit option for local/rehearsal requirements.
- Models may draft task/sites but cannot provide sharing consent, approve a job, submit credentials or enlarge the activity limit. The owner reviews the task and permits task/screenshots to be processed in the cloud. Existing Full-access policy does not manufacture this new sharing grant.
- No new planner, generic tool loop, job queue, task store or local desktop-control system is introduced. The existing HTTPX/proxy adapter calls the documented official Agents API; the project does not import an unrelated system Python SDK.

## Execution and observation recovery

`managed_browser_client.py` creates one small hosted desktop with restricted admitted domains and the computer-use tool. Multi-agent is disabled. It subscribes before the single owner input. Empty HTTP202 event acknowledgements are accepted; they do not prove login or task completion.

The SSE stream has no replay. Up to two interrupted subscriptions can reopen the same session, then reconcile its canonical root turn and bounded saved items. Item IDs deduplicate activity. The original input and approval events are never replayed. A saved completed root turn and its matching final answer are required; idle alone is not completion. A failed session, another root turn or oversized history stops the task. The report excludes intermediate commentary.

The active-work allowance remains45seconds, with up to90additional seconds only while waiting for owner sign-in, and a separate12seconds for cancellation/deletion. Existing job deadlines still apply. Activities remain bounded by the approved max_steps (conversation drafts use8). These are application limits, not provider-internal model-call or hard dollar ceilings. One session occupies one existing daily attempt slot. Nested token usage is retained when provided; unknown usage is never represented as zero cost.

## Owner sign-in in the same task

`managed_browser_auth.py` handles only registered `browser_authentication` actions from the current official session/turn. The credential origin must exactly match an admitted origin. Forms are bounded to six supported fields/options. Missing/unadmitted origins and unsupported controls stop safely; QR, passkeys, CAPTCHA and arbitrary remote desktop takeover are not implemented.

The job remains in the existing running worker. Its card shows the actual origin and a dedicated form. A later explicit owner checkbox permits this task to read signed-in pages; original public admission alone does not grant account access. No account scope authorizes sending, purchasing, paying or booking. The final verified receipt/status labels an authorized account task accordingly rather than calling its observations public.

Form values are masked and held only in memory. They bypass generic pending-write storage and the operations ledger. Submission goes to the official registered-form response event, outside model messages. The server checks the original owner session, job version, current challenge nonce, privacy/provider/task state, deadline and cancellation. An in-memory keyed digest acknowledges an identical retry without consuming values twice; a changed retry is rejected. No automatic credential retries occur. A replacement/expired form, leaving the page, cancellation or job completion clears the values. Labels/options stay in RAM too; only origin/nonce/progress metadata enters the job ledger and is removed from concealed views.

“Submitted” means the form response was received, not that the website authenticated the owner. The same official turn resumes after the website responds; no second task/session is created. Each task closes its session, so cross-job account-cookie retention and server-restart reattachment are not claimed. After restart, existing unknown-job/cleanup-required handling remains authoritative.

## Cancellation, evidence and limits

Closing SSE does not stop hosted work. FYP cancels unfinished work, deletes the session and checks GET404. A lost deletion reply can be resolved by this readback. Unknown creation/deletion leaves cleanup-required and prevents another managed session until inspected; no automatic create/input retry occurs. API deletion does not prove the precise physical teardown time.

`managed_browser.py` stores a private session receipt before input and separately hashed evidence/report bytes. quality=not_goal_completion remains mandatory. Ready for review means the report and cleanup evidence were read back, not that every page claim is independently true or an order/ticket exists. Exact origins and model instructions are not a programmatic transaction firewall. Merchant checkout and independently verified payments/tickets remain separate acceptance work.

## Evidence and sources

Current offline coverage includes default routing/legacy compatibility, empty202, reconnect without duplicated inputs/approvals, missed terminal events, auth submit/skip/expiry/cancel, owner/privacy/provider fences, no credential persistence, deletion-response loss and evidence tampering. Real installed Chrome desktop1440×1000 and phone393×852 ran the new default, registered-form submission, same-job result, and a deliberately lost phone submission reply using an offline provider. No app page exceptions or horizontal overflow; injected network failure and software-WebGL screenshot warnings are identified in QA. Full regression/deployment/live-trial results are recorded in the current QA rather than inferred here.

Historical16November paid trial: one public Books to Scrape session independently matched two prices and confirmed DELETE/404. Its US$1 budget is closed and is not reused. The current real-service trial requires a fresh owner budget; any final live result belongs in the current QA. Synthetic login is not real merchant/account acceptance.

Official references checked17November: [computer use and registered authentication](https://developers.openai.com/api/docs/guides/agents-api/tools/computer-use), [stream recovery](https://developers.openai.com/api/docs/guides/agents-api/sessions/events#how-to-recover-a-disconnected-stream), [turn retrieval](https://developers.openai.com/api/reference/resources/beta/subresources/agents/subresources/sessions/subresources/turns/methods/retrieve), [session items](https://developers.openai.com/api/reference/resources/beta/subresources/agents/subresources/sessions/subresources/items/methods/list). Historical source review: [16November](../../research/2026-11-16-official-agent-runtime.md).
