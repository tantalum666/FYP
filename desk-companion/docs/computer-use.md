# Group 2 · Public browser computer use

7 November2026. General browser work uses OpenAI Responses native computer calls
and the existing job/permission lifecycle. It does not replace typed office
operations or claim general host-desktop, account or transaction autonomy.
[Research and actual evidence](../../research/2026-11-06-general-browser-and-openai.md).

## Responsibilities

- `computer_use_models.py` validates owner goals, public-only/screenshot consent,
  exact sites, task/version,8default/12maximum model turns and continuation refs.
- `computer_use_protocol.py` owns the Responses wire/history in bounded RAM.
  It accepts ordered typed mouse/keyboard actions, rejects duplicate call IDs,
  does not auto-acknowledge pending safety checks, and never retries uncertain
  provider responses. Screens use original dimensions; no arbitrary code tool.
- `computer_use_observation.py` owns document-generation/origin-bound captures and stored-state filtering. Captures raced by a navigation are discarded before persistence/upload; a same-URL reload is a new document.
- `computer_use_worker.py` owns the fresh browser context, page observations,
  input handling, request filtering and normal closure. It receives no API key.
  Platform-specific key context and focused date/select handling were checked
  against real Chromium, not assumed from protocol mocks.
- `computer_use.py` registers an executor on JobService. Its private evidence
  slots are separate from browser temporary HOME. Existing owner session,
  privacy, provider revision, permission version, timeout and cancellation
  checks fence dispatch. There is no second business-task store or job queue.

## Scope and results

The entry page is a public HTTPS URL or an explicitly labelled local rehearsal.
Additional main-frame sites are exact HTTPS origins, at most8total. Browser
requests are GET/HEAD only, public DNS is checked, service workers/WebSockets are
blocked and extra windows require review. Rejected background POSTs/iframes remain blocked without alone stopping an otherwise readable top-level page. Each input rechecks the observed document after target inspection; navigation discards remaining stale inputs. Known personal/login fields, file
access and final purchase/booking controls stop. This can also stop sites whose
read-only searches use POST; it is not a universal merchant adapter.

Request filtering/DNS preflight is **not a proven host network sandbox**. Use only
public/synthetic tasks and fresh app-owned browser state. No user's ordinary
browser profile, saved passwords, payment details or private account is attached.
Real account/credential support needs a separately enforced integration.

A successful job means its browser observation/state was saved, read back and
closed normally. `outcome` is `review_ready`, `needs_owner` or `step_limit`, and
`quality` is always `not_goal_completion`. The UI shows the observed screen and
review/handoff status. It must never turn this into “bought”, “booked” or “ticketed”.

A login, SMS/OTP, captcha, or payment-confirmation wall pauses that same job in
`owner_takeover`. Alice stops model observation and input, tells the owner what
is needed, and does not type or store a password, code, or card, or submit
payment. Only the owner session that admitted the job can `POST
/api/computer/jobs/{id}/takeover` and `.../return`. Both calls are idempotent
operation ids. Paired devices and other logins receive 403. Handing the job
back queues the same id again and restores its saved browser state; it does not
create another job. The resumed run is successful only when the page is read
back and, after a wall, the driver recorded that the wall is actually gone. A
lost response is not success and retries the same operation id. A job left in
takeover past its deadline expires. Cancelling it stays cancelled.

An explicit continuation copies only a verified same-task/site browser state
into a new job with new authority. It does not replay the old action sequence.
Normal cancellation may retain a verified stopped page; uncertain cleanup leaves
a persistent blocker. JSON backup contains job metadata but no browser cookies
or images, and restored browser jobs are read-only/unknown until reconciled.

## Owner interface and HTTP

From Alice's composer, choose **More actions → Use a browser**. State the goal,
select a website or labelled rehearsal, and choose screenshot sharing. Review
the job card, or use the already-selected Full access policy for a new request.
Final transaction boundaries remain outside both modes. Previous jobs and their
screens appear in the existing computer activity view; Continue uses the saved
public state and a fresh explicit instruction.

`POST /api/computer/computer-use/jobs` admits the strict intent. Existing
`/api/computer/jobs/{id}/approve|cancel|reconcile` control the job. Owner/private
read access protects `/api/computer/computer-use/jobs/{id}/screen`; ETags avoid
retransmitting unchanged screens. Client identity/visibility fences discard
late image responses and release object URLs.

## Runtime

Install the locked `browser` extra and choose an installed Chromium executable.
The application never downloads or chooses a personal browser profile.

```ini
DESK_TEXT_PROVIDER=openai
DESK_TEXT_MODEL=gpt-6.1-sol
DESK_TEXT_ENDPOINT=https://api.openai.com/v1/responses
DESK_OPENAI_CREDENTIAL_FILE=/absolute/private/project.env
DESK_COMPUTER_USE_ENABLED=1
DESK_BROWSER_EXECUTABLE=/absolute/installed/chromium
```

Optional `DESK_BROWSER_PROXY_URL` accepts an explicitly configured local HTTP
proxy only. It is scoped to browser traffic and public-DNS preflight; ambient
proxy variables are not inherited and no global proxy/DNS configuration changes.
It is not an OpenAI provider proxy or a workaround for provider region policy.

Normal text/computer requests share the existing daily call count, and each
computer job has a180-second limit and at most12model turns. These are request
bounds, not an account-wide monetary cap. Background suggestions remain off.
Provider usage counters retain numeric values only, including a received response discarded after cancellation/invalid actions. Unknown later attempts cannot reuse an earlier receipt. Keys stay in the host.

Optional operator setting `DESK_BROWSER_HTTP1_ONLY=1` disables Chromium HTTP2 only; it changes the scope binding and defaults off. It does not disable TLS or sandboxing. Confirmed-cleanup initial DNS/load failures produce `COMPUTER_SITE_UNAVAILABLE` and a bounded private navigation diagnostic; uncertain cleanup still blocks later work.

## Reproduce without model spending

`scripts/computer_use_acceptance.py` runs real browser input with scripted native
computer responses through MockTransport. Use a fresh runtime per case and an
existing authorized browser. Cases are `shopping`, `flights`, `stop`, and
`public`; the public case visits the live Books to Scrape test catalogue.

```sh
.venv/bin/python scripts/computer_use_acceptance.py --run-real-browser \
  --case shopping --chromium /absolute/chromium \
  --runtime .runtime/new-computer-case --report /private/qa-output
```

No success here establishes live model planning quality. Paid inference,
authenticated account workflows and real order/ticket receipts are separate
acceptance gates. See the QA for failures retained during development, current
platform access results and exact local/deployed source versions.


## 7 November provider transport

The owner requested a fixed Pi OpenAI route through the existing VPS. The model
client now supports an explicit OpenAI-only loopback CONNECT URL; browser web
traffic still uses its own separate policy. [Transport contract](openai-vps.md).
Actual model authentication/Realtime handshake passed; real computer planning is
still distinct from the earlier scripted browser acceptance.


## 7 November live-model acceptance

The fresh USD1 round ran31real GPT6.1Sol requests on Pi: conservative usage USD0.37970163, all receipts reconciled and ledger closed. Shopping quantity/price/coupon/shipping changes and stored-state continuation, flight comparison/timezones, ordinary calendar-tool followup, and cancellation during a model response passed. Inputs/merchant/flight inventory were fictional; the controller handed the observed flight into a separate calendar subtask. This is not autonomous end-to-end voice orchestration.

Actual JD navigation/search stopped at verification; Cathay initial navigation failed. No real products/fares, private account or transaction was verified. [Full results and retained failures](../../output/qa/2026-11-07-live-agent-eval/verification.md).

`scripts/live_agent_eval.py` is explicit test infrastructure. `scripts/live_eval_budget.py` counts input before generation, durably reserves a conservative amount in one shared USD1 ledger, fixes Standard tier/output limits, retains unknown holds and blocks later calls until resolved. `--initialize-budget` is for a newly authorized round only; subsequent cases require that same existing ledger. Closed budgets must not be reopened. This ledger is not a production account-wide billing limit.

`scripts/computer_scope_acceptance.py` exercises document changes with real Chromium and two owned local fixtures, without a model. It verifies stale-input blocking, positive control, no saved outside-origin screenshot, same-URL reload detection and filtered storage.
