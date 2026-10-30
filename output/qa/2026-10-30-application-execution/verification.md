# Group 2 · Actual application execution acceptance

30 October 2026, Asia/Hong_Kong. Branch `codex/application-execution-20261030`, based on PR67 head `6bc8f19d6476577f5178e0c74374152646591b4a`. The owner authorized beginning the harder application workflow. This checkpoint adds bounded real execution and recovery to the existing services. It does not score a voice candidate or establish general autonomous computer use.

## Result and evidence

| Check | Actual observation | Evidence |
|---|---|---|
| Source review | Dedicated Chromium navigated the local quote pages; source hashes, rendered text/tables and browser PID captured | [Source observations](main-01/source-observations.json) |
| Initial workbook | Actual Calc formulas select Aster at HKD 809.60; XLSX saved and reopened | [Initial budget](main-01/budget-0-5cab4281.json) |
| Changed constraints | HKD 1,000 / 40 colour copies produce `Clarification needed` / `No valid option` | [Changed budget](main-01/budget-1-81ce75b8.json) |
| Scripted clarification | Black-and-white selects Delta at HKD 669.24, including 50 purchased / 40 needed copies | [Final workbook](main-01/artifacts/demo-budget.xlsx), [result](main-01/acceptance-result.json) |
| Lost result and process restart | Controller exits 73 after publishing, before acknowledgment. Fresh process sees `PROCESS_RESTARTED`, reconciles original job, keeps hash and mtime | [Fault checkpoint](main-01-revise.log), [recovery](main-01-recover-2.log) |
| Application restart | New desktop instance ID after a clean container restart; all five active files reopen and verify | [Before](main-01/instance-before-clean-restart.json), [after](main-01/instance-after-clean-restart.json), [readback](main-01/post-restart-readback.json) |
| Writer/PDF | Real ODT edited through Writer and exported as PDF; independent ordered text/metadata match; both rendered pages inspected | [ODT](main-01/artifacts/demo-brief.odt), [PDF](main-01/artifacts/demo-brief.pdf), [page 1](main-01/rendered/brief-1.png), [page 2](main-01/rendered/brief-2.png) |
| Calendar continuity | Three original events plus two rehearsals; first remains version 1, same second event becomes version 2 on Thursday 5 November at 15:15 | [Acceptance result](main-01/acceptance-result.json) |
| Task continuity | Nine source tasks, seven unfinished, 14.5 hours; package task remains in progress with an explicit next step | [Action plan](main-01/artifacts/action-plan.md), [result](main-01/acceptance-result.json) |
| Permission withdrawal | Full → Ask before queued dispatch yields `PERMISSION_CHANGED`; `must-not-publish.txt` is absent | [Acceptance result](main-01/acceptance-result.json) |
| Email boundary | Exact local draft saved; no transmission | [Unsent draft](main-01/artifacts/email-draft.txt) |

The application acceptance driver reads only the connected fictional inputs and uses typed generic operations. It does not import the reference solver or controller answer files. It deliberately supplies the plan, meeting-note interpretation and clarification; these are scripted test decisions. Calendar calls use the actual existing service. **Model calls: 0. Autonomous agent pass: false.** The old paid OpenAI and Qwen ledgers remain closed.

Final workbook SHA-256 is `2646daed43aef3abbe0e45eea94bf3d5700e526257b58f7c15d9be93429c55c3`. It is the same before acknowledgment loss, after reconciliation and after a later clean application restart. The final PDF SHA-256 is `f46fbb046731aeb22f208ecca37d144bd5870d3e54c22806b6cd57008f8e2bec`. Full artifact sizes/hashes and event IDs are in the result JSON.

## Web and phone journey

The dedicated preview uses API `127.0.0.1:8854` and Vite `127.0.0.1:5191`, the fictional acceptance database and providers `none`. It does not borrow the older 5190 data or reconfigure the native Simulator.

- Web task → Continue with Alice → exact workbook cells/formula shown → Allow once → queued → Verified. The actual downloaded XLSX matched its receipt SHA-256 (`56c5d34ae60dadaaf3124b9c32c52898cd7b7d33a92983916a61169b6c87169d`). Actual Calc value was 285.
- Phone surface → contextual update card → Allow once → actual Calc recomputes 380, preserving `=A2*B2`. This first interaction used the phone surface at a wide viewport; it is not counted as narrow-screen proof.
- Explicit 393 × 852 viewport was verified through DOM dimensions. Read-only checking retained the exact unsent message, then a new proposed update was reviewed and declined with Not now. The active workbook hash stayed unchanged. The fixture draft was cleared afterward.
- Phone Plan → Tasks → complex task shows stage results, unfinished parent task and five download links. Alice remains available on the home screen. No new bottom navigation was added.
- Shared action cards, request handlers and task refresh remain the only UI path. No duplicate queue or per-card polling was introduced. Console inspection during the completed journeys and on the fresh final preview found no warnings/errors. Vite recorded expected connection-refused messages during the intentional API restart; the reconnected final UI and file reads passed. [Log summary](preview-log-summary.json).

Evidence: [web review](02-web-review.jpg), [web result](03-web-verified.jpg), [393px review](06-phone-393-review.jpg), [393px cancellation](07-phone-393-cancelled.jpg), [Alice home](08-phone-alice.jpg), and [UI identifiers](ui-ids.json), [independent UI readback](ui-result.json), [final web files](12-web-files.jpg) and [actual final Calc window](13-live-calc-final.png). Native iOS taps, keyboard, downloads and voice capture were not exercised in this round.

## Failures retained and repairs

1. Mac LibreOffice's bundled Python was killed, and an external compatible Python importing pyuno crashed. The installed Mac application/security settings were preserved. Actual execution moved to an owned ARM64 Linux environment.
2. First Writer smoke attempts failed before publication because the installed UNO style is `Text body`, not `Text Body`. Corrected the mapping; actual ODT and two-page PDF then passed. [Failed smoke](writer-pilot.json), [successful smoke](smoke-office-results.json).
3. Main initial attempt 1 failed with Calc error 525: formulas referenced a sheet that had not yet been created. All sheets are now created before assigning formulas. XLSX reload also canonicalizes absolute sheet names; normalization preserves cell anchors and quoted strings. [First failure](main-01-initial.log), [successful initial workbook](main-01-initial-2.log).
4. The first complex PDF failed the content gate because layout-order text interleaved wrapped table cells. Raw content order plus exact complete-text/operation comparison fixes this without weakening missing/changed-content checks. The rejected PDF was never published. [Attempt 2](main-01-initial-2.log), [reused successful steps and repaired export](main-01-initial-3.log).
5. First application restart left an Xvfb lock in the container's writable `/tmp`, so read-only reconciliation remained unknown. The startup script now removes only its owned display lock. Rebuilt/recreated the isolated container, reconciled the original file, then separately verified another clean restart. [Unavailable recovery](main-01-recover.log), [successful recovery](main-01-recover-2.log).

Failed jobs, staged diagnostics and immutable versions were retained; successful steps were read back and reused rather than rewritten. Private core databases, credentials and raw runtime directories are not publication artifacts.

## Local checks and scope

- [Full backend suite](backend-tests.txt): **524 passed**, one existing Starlette/httpx deprecation warning. Fourteen new application boundary checks include approval, stale source/artifact/task, revocation, cancellation, lost acknowledgment/restart, immutable download, owner-only access, backup authority and strict PDF/formula comparison.
- [Frontend suite](frontend-tests.txt): **89 passed**. [TypeScript/Vite build](frontend-build.txt) passed; existing asset chunk-size advisory retained.
- [Final focused application/job/permission checks](final-targeted-tests.txt): **73 passed** after the final stage-error projection. Ruff, changed-source formatting, internal links and staged secret scan are recorded in this folder. An initially mistyped test filename ran no tests and was corrected before this passing run. Tests use fake bridges only for service boundaries; the application records above are separate actual-process evidence.
- A pinned-profile prepare helper was run successfully. [Execution contract and reproducible setup](../../../desk-companion/docs/application-execution.md) document the single mount, internal network, non-root process, unchanged Chromium sandbox, DNS workaround and owned process cleanup.

Published text logs normalize terminal carriage returns/trailing whitespace; failure codes/results are retained. Live preview logs stay local and ignored.

No CI workflow was added or run. No API spending, external message, purchase, school submission, microphone/camera capture, Pi or Luwu action occurred. The actual controlled desktop is Linux X11; this does not establish Pi Wayland or native macOS execution.

## Next gate

Integrate a resumable model-driven task turn over the existing stages/tools and test it offline, including held-out source/layout variants and interruption. The HTTP assistant still stops after one effect-producing tool; stage persistence alone is not autonomous planning. Production OpenAI provider wiring and a separately authorized small paid voice comparison remain open. Do not report a new Qwen/Realtime/Live application-task score from this execution-layer milestone.


## Publication

Draft [PR68](https://github.com/tantalum666/FYP/pull/68) is open and unmerged, stacked on PR67. Implementation `20581f387a99d0ecd19f2c194683ad114275aea8` matched the remote branch and GitHub PR head. [Receipt](publication.json). A documentation-only closeout follows; the final remote HEAD is checked after its push. No CI workflow or credentials/runtime data were published.
