# Senplate P0 verification — 19 September 2026

Local development began on 18 September and continued past midnight. Full original Markdown reading is recorded in [reading-record.json](reading-record.json): 79 files, 6,834 lines, all ranges covered. Source history and protected assets remain separate from generated QA evidence.

## Result and environment

The local software replenishment loop passed. This does not validate physical sensing, recognition, Pi performance, nutrition or waste reduction.

- API: Python3.12 / FastAPI / PostgreSQL16.14, `127.0.0.1:8799`; private PostgreSQL port55437.
- Web: React19.3 / Vite8.3, `127.0.0.1:5177`; Codex in-app browser through CUA, no external Playwright fallback.
- iPhone: Xcode26.6 / iOS26.5; iPhone17Pro 402×874 and a project-created SE3 `Senplate Small QA` 375×667. Maximum AccessibilityXXXL was exercised. Other projects' simulators/databases were not reset.
- Latest code build: Web TypeScript + Vite production build passed; Xcode build and selected UI test passed. Backend `pytest`: 15 passed in8.43s; Ruff passed. Upstream Starlette/httpx and anyio emitted two deprecation notices, with no failed backend tests.

## Functional evidence

| Check | Result | Evidence |
|---|---|---|
| Identity / page / nonblank | Pass | [Kitchen DOM](kitchen-en.txt), visible heading, data, controls and chart; no framework overlay |
| Console after fresh final navigation | Pass | No error or warning after final reload; earlier HMR restart and intentional dropped-response network errors are explained below |
| English / Simplified Chinese | Pass | Web reload preserved zh-Hans; iPhone terminate/relaunch preserved Chinese and session; final review defaults restored to English |
| Shared replenishment | Pass | iPhone accepted and progressed task at700g; CLI added1000g; browser linked event, completed once at1700g; iPhone read1700g and completed batch. [DOM](cross-client-completed.txt), [screen](cross-client-completed.png) |
| Reply lost after commit | Pass on Web | CDP paused only the local Fetch decision response atHTTP200 and failed it with ConnectionClosed. Pending operation remained; Check and retry queried same operation; one task remained. [Pending](lost-response-pending.txt), [recovered](lost-response-recovered.txt). Interception cleared with empty patterns; no fault rule left active |
| Removed pan | Pass | [DOM](pan-removed.txt): current `— g`, last valid700g at12:10, Pan removed, no new suggestion; not zero or consumed700g |
| Roles / personal context | Pass | Backend negative tests; Web workspace switching and sign-out; [viewer](viewer-permissions.txt) has no suggestion actions; CSV button absent. Personal workspace has explicit next-milestone empty state |
| Export | Pass atAPI | Manager200, viewer403; [CSV](events-export.csv) explicitly contains simulated data_origin |
| Source filter | Pass | Switching Event log to Device returned no matching events for a simulated run |
| Narrow screens | Pass | Web390×844 has scrollWidth390; iPhoneSE3 375×667 scrolls through content and reaches task controls |
| Large type | Pass after fix | Chart replaces dense labels with [recent readings](iphone-small-large-text.png); normal labels no longer truncate |

Backend scenarios are in [test_api.py](../../../tests/test_api.py). They include concurrency, version/ownership rejection, repeated and out-of-order observations, stale/heartbeat separation, binding changes, end-of-service, future supply, session recreation/persistence, scope and machine identity, revoked roles/WS, old refill event rejection, actual quantity differing from plan, and stable event sequence under a frozen demo clock.

### iPhone test runs

The UI tests are staged against a running demo API, not independent fixtures. Prepare700g for the first test; it leaves an awaiting-reconciliation task. Add/confirm1000g before the second test. Supply generated credentials to the test runner through TEST_RUNNER environment variables, never source control.

| Selected test / target | Final observed result | Artifact |
|---|---|---|
| EnglishChinesePersistenceAndKitchenFlow /17Pro | Pass, latest auth-refresh code;52.364s test /62.483s overall | `.runtime/ui-tests-final-auth.xcresult`; [attachments](ios-ui-final-auth/manifest.json) |
| VerifiedBatchAndLargeText /17Pro | Pass;31.616s test | `.runtime/ui-tests-04.xcresult`; [attachments](ios-ui-04/manifest.json) |
| VerifiedBatchAndLargeText /SE3 | Pass after adaptive chart and filter changes;33.720s test | `.runtime/ui-tests-small-02.xcresult`; [attachments](ios-ui-small-02/manifest.json) |

XcodeBuildMCP snapshot_ui repeatedly returned “No translation object returned for simulator.” UI validation therefore used XCTest through the same XcodeBuildMCP tool and full-resolution XCResult attachments. XcodeBuildMCP screenshots independently confirmed the review app running. No claim is based solely on a successful compile.

## Visual comparison

References: [kitchen concept](../../../design/p0/kitchen-en.png), [iPhone concept](../../../design/p0/iphone-en.png). These are assistant-selected implementation references under the user's development authorization, not individually user-approved screen designs. Final English image prompts are in design/p0. Initial Traditional Chinese concepts are retained as historical versions.

The kitchen reference and final screenshot were inspected directly with `view_image` at1536×1024. The phone reference and actual full-resolution screenshots were also inspected. The phone reference is853×1844; actual iPhone17Pro is1206×2622 pixels /402×874 points, with real OS chrome. Exact raster dimensions were not forced onto a real simulator. Web viewport was reset after QA.

| Comparison | Reference / implemented evidence | Resolution |
|---|---|---|
| Structure |215px sidebar, three open metrics, station/suggestion columns, task panel below | Preserved; reduced chart and desktop gaps so task queue and demo footer remain visible |
| Main copy / CTAs |Kitchen board, Station01, Replenishment suggestion, Accept suggestion, Adjust amount, Not now | Preserved in English; Chinese is localized resource text, not a separate flow |
| Palette |VI green#163F35, ivory#F3F1E7, white panels, restrained amber status | Exact code tokens; generated texture/gradient residue replaced by the approved flat VI colours |
| Typography |Manrope character and hierarchy; Noto Sans SC for Chinese | Actual bundled licensed fonts;44px desktop heading; readable native controls. iOS font internal names verified before use |
| Logo |Reference generator approximates a bowl | Actual user-selected V7 asset used; source artwork was not redrawn |
| Containers / spacing |Functional panels with light dividers and limited corner rounding | Preserved; no marketing hero or extra metrics. Original overlong chart/card fixed |
| Icons |Bar chart, event document, station monitor, profile/language | Lucide outline icons and native SF Symbols; weight/style consistent. Native iOS26.5 tab bar intentionally differs from the concept's older flat bar |
| Responsive / type |Phone vertical sequence; desktop two columns | Narrow Web stacks in order, no horizontal overflow. Native small phones scroll; accessibility text replaces a cramped chart with equivalent recent readings |

Above-the-fold copy diff: main page/navigation/CTAs retained. Intentional additions are the authenticated user/workspace, Sign out, Verify refill task filter, and read-only/error/uncertain states required by the business specification. Actual weights/counts/statuses follow the server. “Weight stable” and “Food confirmed” refer to explicit demo/manual state, not model accuracy.

This was verified for fidelity to the reference layout and the existing VI, with the explicit native-navigation, font and responsive differences above. It is not a claim of pixel-identical reproduction of generated raster text.

## Repairs, retained evidence and limitations

Fixed: missing Xcode resource inclusion; unsigned simulator session failing to persist; keyboard focus/Next/Go; chart time truncation; accessibility chart labels; small-screen task filter; StrictMode socket cleanup; and UUID-sorted equal-time events (now explicit sequence). Early failed XCResults are retained with final passing runs. A Vite configuration formatting change briefly restarted HMR; a fresh reload restored the UI and final console was clean.

The browser full-page capture at390px produced a scaled half-width rendering despite correct DOM widths. It is not used as final visual proof; the final viewport capture is [web-mobile-zh-viewport.png](web-mobile-zh-viewport.png). No outside-browser fallback was needed.

Remaining: physical iPhone/iOS17 runtime, comprehensive VoiceOver and arbitrary long user-entered menu names, iPhone-specific lost-response injection, prolonged suspend/network stress, real hardware/model/Pi and all P1 features. There is no external deployment or course submission.

## Screenshots

[Kitchen English](kitchen-en.png) · [iPhone English](iphone-en.png) · [iPhone Chinese](iphone-zh.png) · [running Simulator](iphone-running.jpg) · [narrow Web Chinese](web-mobile-zh-viewport.png) · [SE3 large text](iphone-small-large-text.png).

Closeout records updated authorities, protected hashes, links and group identity in [closeout-validation.json](closeout-validation.json).

Final closeout: 80 source Markdown files and 760 local links checked; no broken links. 332 protected original assets/documents/identity files matched their initial hashes. All required deliverable paths exist.
