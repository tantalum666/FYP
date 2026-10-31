# Group 2 · Personal-agent cross-application acceptance

31 October 2026, Asia/Shanghai. Owner paused Pi and prioritized personal-agent implementation, especially cross-application operation. Branch `codex/personal-agent-cross-app-20261031` starts from verified main `dac527b`; hardware PR73 is separate. [Implementation contract](../../../desk-companion/docs/application-work.md), [research refresh](../../../research/2026-10-31-cross-application-continuation.md), [actual reading/scope record](progress.md).

## Implemented and tested

Connected PR5's durable Work registry to the current Chromium/Calc/Writer/PDF executor. Application use and input selection are explicit at admission; selected hashes are bound even if the planner omits a reference. Reused the existing queue, software permissions, action cards, result verifier and parent-run storage. Added current/immutable-history verification for legitimate file revisions and normalized supported spreadsheet formula syntax at execution.

Local checks: **1,701 backend tests**, **303 frontend tests**, Ruff, TypeScript and Vite production build passed. Fifteen new backend cases cover real service/storage behavior with a fake application bridge: selected sources, file revision/history, once/full permission, no retroactive full grant, revocation, parent pause/cancel/session expiry, changed queued input, foreign references, exact child recovery after an abrupt process loss, tampered history and waiting-effect/shutdown, and cancellation without blocking on office readback. Three new frontend cases validate application scope/task/source/budget/disconnection behavior. The frontend build retains its existing large-3D-chunk warning; it is not a test failure. Existing FastAPI/httpx deprecation and empty-regex pytest warnings remain unrelated to this patch.

## Actual applications, offline decisions

The existing `fyp-apps` Colima profile was stopped, then restarted after checking its sole application-root mount. Reused its labelled `desk-applications` container, internal network, nonprivileged execution and Chromium sandbox. Other profiles, including the running Rillora build profile, were untouched. No home/repository/credential mount was added; one clearly fictional HTML quote file was added inside the already-owned input root.

The coordinator receives **scripted** `AgentDecision` objects through the normal guarded interface; its decisions use only returned Work observations/results. The application operations use the actual registered tools and real programs. Synthetic owner changes/answers are labelled in the runner and evidence. No model request or external purchase occurred.

| Stage | Independent result |
|---|---|
| Read | Actual Chromium read the selected local HTML quotes; source/hash/complete displayed-line coverage recorded |
| Initial calculation | Actual Calc:36 requested copies, HKD900 budget, Wednesday deadline,10% reserve; Aster776.60 feasible, Birch902.00 over budget, Cedar752.40 too late |
| Changed constraints | Synthetic owner changed to48 copies/HKD950; same Work, new plan revision and same task |
| Revised calculation | Aster1020.80 infeasible, Birch902.00 feasible at50-copy minimum, Cedar1003.20 infeasible/late |
| Lost completion | Real revised XLSX saved; runner deliberately lost the completion and exited73 |
| Restart/recovery | Restarted the application container; a new runner process reconciled the original job. File SHA and nanosecond mtime were unchanged |
| Clarification | Work persisted the minimum-order question; synthetic owner accepted two extra copies |
| Document/PDF | Actual Writer saved the decision and exported a two-page A4 PDF; returned content and operation marker verified |
| Final Work | Four real app jobs verified, including the superseded workbook history; report/CSV saved; structural state succeeded, semantic/live-model quality not assessed |

[Machine result](real-02/verification.json). Actual local files: [initial XLSX](real-02/1-comparison.xlsx), [revised XLSX](real-02/2-comparison.xlsx), [Writer ODT](real-02/3-decision.odt), [PDF](real-02/4-decision.pdf). These are fictional acceptance artifacts, not a purchase, teacher submission or private-user data migration. Both PDF pages were rendered with Poppler and visually inspected: table/amounts/text fit without clipping or overlap. The full fixture run response remains local; selected evidence and hashes are published.

Failures were retained: an initial fixture bootstrap omitted three required privacy flags and was corrected before run creation. `real-01` then exposed `APPLICATION_FORMULA_ERROR` because comma-form formulas were passed directly to UNO. The failed job was not replayed or marked successful. Fixed the executor boundary, used fresh `real-02`, and preserved its failed predecessor. Existing framework checks first caught a create-response/idempotency default mismatch; corrected the returned defaults while preserving old request hashes.

## Actual web and phone UI

Flow: Tasks → Work tasks → selected Work → exact workbook card → Allow once → verified workbook → automatically prepared document → Cancel work → confirmed cancellation. Independent SQLite/filesystem readback shows one Work, one succeeded workbook and one cancelled document, with no document published. [UI readback](ui-readback.json).

A393×852 phone browser retains Alice, exposes the same Work flow, shows the verified/cancelled distinction and downloads the workbook. Download SHA matches the server receipt. Page width equals393px with no document-level horizontal overflow. The scope composer disables application use until a task is selected, lists chosen input files and separates application authority from calendar/task drafts. A scope-only test draft was reviewed, then explicitly discarded; no extra Work was started. Temporary viewport override was reset.

Validation uses CUA and the actual app at Vite5191 proxying API8861. The first direct API8861 static-page attempt hit the existing origin allowlist; switched to the supported frontend origin without weakening policy. Final app console has no warn/error. Source hot reload reset an unused test draft during copy edits; the final scope flow was repeated after those edits. Native device/soft-keyboard validation was not performed.

UI fixes made during verification: application cards moved before diagnostic activity; pending actions ordered first; file review remains expandable; calendar/task proposals and office-file permissions have distinct copy; report limits/files no longer imply that office artifacts are absent. Screenshots stay in the ignored `.runtime/qa-ui` directory: `web-cancelled.jpg`, `phone-files.jpg`, `phone-scope-review.jpg`.

## Publication and remaining work

Only source, focused documentation, selected test logs/JSON and fictional artifact files are eligible for this milestone. No credentials, databases, raw private diagnostics, browser profiles or background model budgets are published. No CI was added or run. Git publication is recorded separately from merge or deployment.

Pi is paused, with prior networking/kiosk/power work preserved on PR73. No Pi session was resumed; its old Mac tunnel had already timed out and was left stopped. All live-provider experiment budgets remain closed. The next step is ordinary Alice/Omni-to-Work handoff/recovery with offline variants. This milestone does not deliver unrestricted GUI operation, real-mailbox monitoring, shopping/payment, ticketing, real model autonomy or offline-host cloud availability.

Publication: source commit `b277cef` pushed to [draft PR74](https://github.com/tantalum666/FYP/pull/74); GitHub head readback matches. It remains unmerged. The receipt/handoff-only follow-up does not change the tested application.
