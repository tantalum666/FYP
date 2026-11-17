# Group 2 · Personal-agent conversation/browser QA

17 November 2026. The owner asks to continue toward a personal agent after Pi diagnosis. [Reading/scope](reading-record.md), [contract](../../../desk-companion/docs/conversation-browser.md), [sanitized results](results.json). Work is on codex/personal-agent-browser-20261117, based on 50ce8066 / the open PR #124 branch. No CI or paid model call. Ordinary Mac/native/Pi runtimes were not replaced by this QA setup.

## What changed

Text and voice now prepare an immutable public-browser proposal, with exact sites/task details and separate owner cloud-screen consent. Approval starts the existing JobService at most once. Later questions reopen current receipts/screens/state, preserve untrusted source wording as data, and keep goal/transaction completion false. Local saved-state continuation and explicitly enabled managed research reuse the existing executors.

Fixed a separate real reachability gap: TextPlan's independent literal omitted ten registered software/read tools. Text names now derive from the canonical capability registry's text flag. Email status/drafting, connected apps, weather, application sources/operations/results and device status are reachable in primary text chat with their existing authority checks. No new sender/account grant was added.

BrowserResearchReview is a separate compact component using the existing shared action surface. Cloud consent starts unchecked. Conversation/job refresh and the original write-operation key are reused. A lost approval response exposes recovery after submission ends, clears the pending write after readback, and leaves subsequent chat usable. Cached original messages return current browser state instead of a stale review request. Pending-operation copy now says action rather than save across the three layouts.

## Local regression evidence

Final complete backend suite: **2,410 passed**, two pre-existing warnings (Starlette/httpx deprecation and an empty regex assertion in an unrelated connector test). The first full run had 2,405 passes and three failures from an obsolete fixed 31-tool assertion. Replaced it with a complete registry/name/count comparison; the later final full run above passed. Browser/voice focused checks and the new cached-response/permission/scope tests also passed.

Frontend: **391 passed**, TypeScript and production build passed. Final copy-only adjustments were compiled after the interaction checks. Ruff and diff checks passed. Existing 3D bundle-size warnings remain; this is not a new bundle-performance claim.

Meaningful cases include forged consent rejection, Full access without invented sharing, paired/hidden/expired-session refusal, task-version changes, draft expiry, cancellation after partial preparation, crashes before/after durable approval, same-job recovery, evidence tampering, privacy changes during readback, voice interruption, explicit managed-engine lifecycle and independent browser-data-to-task propagation.

## Actual browser journeys — scripted model decisions

Used installed Chrome 157 through production worker/API/UI paths. The model/controller decisions were scripted through mock transports; no inference, real-account, purchase or ticket acceptance is implied.

| Journey | Independent result |
|---|---|
| Chat request → review → consent → real browser | Fictional three-pack cart, total HK$43.50 including shipping |
| Follow-up correction using saved browser state | Four packs, refreshed price and SAVE10, total HK$55.80; parent state hash retained |
| Browser result → reviewed task | Exactly one task stored with the observed HK$55.80 total in its next step |
| Phone flight comparison | Two adults, 20 kg baggage, HK$2,080 fictional total; arrival 23 November 00:15 Asia/Tokyo |
| Approval accepted server-side but response dropped | One unchanged operation ID on retry, one new job, pending write cleared, later chat worked |
| New phone scope and cancel | Sharing initially unchecked, start disabled until opt-in; cancel created no browser job |

Receipt bytes, screenshot and stored browser-state hashes were checked outside the response UI. Every exercised browser comparison closed normally and submitted zero orders/bookings. The task was independently read from SQLite's data JSON column. Two initial QA-harness mistakes (treating calls as a list and task JSON fields as physical columns) were corrected; failed harness logs remain private. Passed desktop phases were retained while resuming the remaining phone check.

## Rendered flow and console

Browser plugin/skill is not listed; regular existing Playwright was used, with no dependency installation. Development review used 127.0.0.1:5191, followed by the built production bundle on 127.0.0.1:8832. English desktop 1440×1000 and English/Chinese phone 393×852: intended title/URL, meaningful content, no framework overlay, no page exceptions, no horizontal overflow, visible readable consent and actions. Expanded details can scroll inside the conversation; default phone review keeps both buttons visible. Screenshots were visually inspected.

The development server's font 403 was traced to a symlinked dependency path outside Vite's allowlist. The production build served the bundled font successfully; production-origin checks were not relaxed. Before a job's first capture, its screenshot endpoint returned expected 404s and the UI retained pending status; after capture it returned the verified image. The approval response failure was deliberate. Headless WebGL readback warnings are recorded and are not a measurement of normal-device rendering performance.

The recovery button originally appeared while the approval request was still in flight; the real flow exposed that issue. It now waits for the submission to finish/fail, and the production-bundle interrupted-response scenario passed after that correction.

Private evidence: `~/.config/desk-companion/personal-agent-browser-20261117/` contains backend-final.log, frontend-final.log, build logs, browser-acceptance.json, production-recovery-acceptance.json, UI captures and isolated fixture runtime. No live credentials, database, browser session or raw logs are published.

## Limits and next step

No new paid text/voice/browser model run; no microphone recording, real merchant account, live fare/order, payment or ticket. Voice dispatcher and full-catalog setup are protocol-tested, not a fresh spoken end-to-end test. Native Simulator and Pi were not redeployed by this slice. The everyday release remains the last independently delivered 2c31f430 unless a later activation receipt says otherwise.

Next integrated product step: real same-browser owner control and explicit return for login/account walls, followed by supported merchant-specific transaction evidence. Existing continuous inbox ingestion and Microsoft consent gaps remain separately documented in the capability map.

Fresh ordinary Mac readback: health OK and build-info source 2c31f430; this confirms that the isolated QA did not replace the daily application. Chinese phone review/cancel and unchecked sharing were separately checked on the final production build.

Closeout scope check: 37 selected source/test/document/result files; 30 added local links resolved; no credential-pattern matches; git diff whitespace check passed. Current requirements, maintenance/copy/browser contracts, capability/research map, decisions, work log and compact handoff/entry were updated. No workflow file is added.

Publication: [PR #126](https://github.com/tantalum666/FYP/pull/126), open/draft against PR #124's branch. Source commit d7d2e04bdf837c9142502c3c39a1be978bcbed51 was pushed and matched the remote head at creation. [Receipt](publication.json). This does not mean merged or deployed.

Environment closeout: completed QA API/dev servers were stopped after checking that no browser job remained active. The linked JavaScript dependency directory was replaced with an independent APFS clone of the same packages; package-manifest hashes matched, no install/lockfile change occurred. A short isolated Vite check then served the previously blocked WOFF2 font with HTTP 200, and that check server was also stopped. Python dependency packages remain reused without installation. Ordinary Mac service is separate.
