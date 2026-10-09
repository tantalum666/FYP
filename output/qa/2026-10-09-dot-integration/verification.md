# Group 2 Dot integration verification — 2026-10-09

Status: local review and validation complete; GitHub merge and local-main application pending. Final readback is recorded below after completion.

## Scope and provenance

User explicitly requested reviewing Dot's GitHub work, merging/applying it and fixing problems directly. Remote main started at `5b8ce5b81dd075cae3cef6787c964bf0406591e2`. Dot plan `597cfe7e90aec8d12a2f68963d2b8f4e1ff54220` is the parent of code `ba2b164664c33db0427e05fa39eb23752430103e`. Neither had a PR or was merged. Integration starts from local RIG research `085dc01e3ea360d4d1555189f542c435cd5e40e3` / draft PR #1, preserving that work.

[Full-reading ledger](reading-record.json): 123 local project Markdown bodies to EOF; 19 remote changed versions additionally covered. Exact equal line text already read in this same round is inherited only after source coverage and equality are checked; all new/replaced remote lines emitted and read. 142 file versions / 15,358 version-lines, 127 unique paths. No fingerprint substitutes for reading. Chunks 0–43 and the recorded truncated-range supplement are complete. The four conflicted root documents preserve both histories; current handoff is rewritten to current status.

## Review findings and fixes

1. **Voice disconnect cleanup:** a conflicting or invalid request reusing an in-flight tool ID enqueues a rejection. The result loop marked the original invocation delivered solely by that ID. Disconnect then skipped cancellation, allowing a late unapproved calendar draft to remain. `ToolDispatcher.delivered` now requires that exact invocation's stored result object. Both regression cases failed before the patch and pass after it. The committed red log only normalizes trailing whitespace; its raw output remains in the ignored private runtime backup. See [red log](delivery-regression-red.log), [green log](delivery-regression-green.log).
2. **Capacity UX:** the history-limit error referred to an archive action that does not exist. Copy now explains that new jobs are unavailable while existing jobs/results remain accessible. No archive feature is claimed.
3. **Installation/docs:** the note demo avoids an unnecessary dependency sync that could remove installed optional audio/vision packages. Product/current entry points now describe the implemented bounded executor; historical cloud reports retain their dated browser limitation with a link to this local verification.

Computer operations remain opt-in and limited to generated new UTF-8 files in the service host's dedicated notes directory. Owner approval, full-intent/version binding, independent readback, cancellation and unknown-result reconciliation remain intact. General GUI / LCU control is unfinished.

## Automated checks

| Check | Result | Evidence |
|---|---|---|
| Remote code baseline backend | 147 passed, one upstream deprecation warning | [baseline](backend-baseline.log) |
| Added delivery regressions before fix | 2 expected failures | [red](delivery-regression-red.log) |
| Full voice dispatch after fix | 14 passed | [green](delivery-regression-green.log) |
| Complete backend after fix | 149 passed, one upstream Starlette/httpx deprecation warning | [backend](backend-final.log) |
| Ruff backend / scripts / tests | Passed | [Ruff](ruff.log) |
| Frontend pure logic | 15 passed | [frontend](frontend-final.log) |
| TypeScript and Vite production build | Passed | [frontend](frontend-final.log) |

Commands from desk-companion: `uv run --no-sync pytest -q`, `uv run --no-sync ruff check backend scripts tests`; frontend: `npm test`, `npm run build`. No dependency upgrade or CI workflow was introduced. These are actual local runs, not GitHub CI results.

## Real browser interaction

Flow under test: Assistant → prepare a note → review exact text/target → approve → independent verified result; then cancel, reconcile a changed file, recover an unknown request and preserve drafts.

Used the available CUA in-app Browser APIs (`tab.playwright`, documented CDP fault injection and viewport capability); no standalone Browser plugin skill was listed, and no external Playwright or alternative UI automation was used. Isolated API `127.0.0.1:8833`, UI `127.0.0.1:5191`, runtime `desk-companion/.runtime/dot-integration-qa/`. All contents are fictional. Original credentials/database are separate.

| Browser check | Result |
|---|---|
| URL / title identify Desk Companion | Pass |
| Meaningful page; no blank shell or framework error overlay | Pass |
| Relevant console warnings/errors on normal app and device page | None observed |
| Real note preparation before approval | No file existed |
| Owner approval → actual file | UTF-8 contents match; 63 bytes and SHA256 independently match disk |
| Read-only verification after tampering | unknown, content_mismatch; tampered file unchanged |
| Restore fixture → Check existing result | Verified, no repeat write |
| Cancel before approval | Cancelled; no artifact |
| HTTP 200 response withheld until client timeout | Unknown request retained; same operation recovered to one job |
| Recover old request while a new draft is entered | New title/text retained; old job not duplicated |
| Close with unsaved note → Continue editing | Draft retained; later explicitly cleared |
| Reopen and English / Simplified Chinese | Persisted statuses and both interface languages observed |
| 1280×800 desktop / 320×740 phone | Readable controls and scroll; no horizontal document overflow |
| 1024×600 independent always-on display | Clock/month/up-next layout retained; touch → Assistant → same job panel |

A text-label selector for a populated controlled textarea did not match exact label text; the DOM/AX showed the retained value and a semantic textbox selector succeeded. Initial raw Fetch setup without resource type was refused by the browser tool; explicit non-Document patterns were used. The held response eventually reached the existing client timeout; its interception ID was already expired when failRequest was attempted. This was an actual timeout-after-server-commit test, not a successful failRequest. Interception was cleared using supported Fetch.enable with empty patterns. Viewport overrides and draft inputs were reset.

UI evidence: [desktop](fyp-dot-jobs-desktop.png), [phone](fyp-dot-jobs-mobile.png), [actual file receipt](ui-file-result.json), [validation and preservation](validation.json). Four isolated jobs, two cancelled, two verified, one physical file; the response-loss fixture exists only once. No QA content was inserted into the main workspace.

## Preservation and limits

107 school / identity / retired Senplate protected files are byte-identical. Main SQLite was backed up into its ignored private runtime before migration; its seven original event rows were hashed for comparison. School DOCX/PDF were not edited, so no render was required. No model credentials, private runtime data or installed dependencies are committed.

Not validated this round: paid voice quality or latency, real microphone / AEC / Cantonese, school DGX, physical camera accuracy, Pi load/touch longevity, RIG / cleaner / physical stop, native iPhone build or true-device behavior, third-party GUI / LCU / remote-PC execution. No purchase, system permission change, member invitation or school submission was performed. No CI workflow exists.

## GitHub merge and local application

Pending at this checkpoint. The integration PR must be attached, merged at its reviewed head, then origin/main fetched and local main fast-forwarded. Record actual resulting refs, original-data comparison and running-preview verification after these steps; do not infer completion from a pushed branch alone.
