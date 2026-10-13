# Mac bounded layout acceptance: ba8cf2a9

The Mac build and actual English/Chinese work-card regression passed at source `ba8cf2a9516525b9778ab00214cf3bebc6a0ac60`, tree `e04b2b5409c287ad55cc734ab328ce9623bc68b9`. This closes the reproduced Mac module-resolution blocker and the zero-height narrow-title defect within the tested scope. It does not promote earlier memory, routine, demo-application or protocol results to this newer source.

## Source, build and served evidence

The separate `fyp-narrow-ba8c` checkout verifies exact HEAD/tree, ten newly fetched UTF-8 blobs and 544 trees against Git object fingerprints. The old `publicCapture.ts` path is absent; `capturePolicy.ts` retains helper blob `67630e12e97f8ebdd1407bf684ff78259b8a78ac`. No production edits, commits, pushes, merges or deployments occurred. Existing dependencies were reused without installation.

Actual Mac `npm run build` exited0; TypeScript and Vite completed. Existing large-chunk warnings remain warnings. No broad test suite was rerun. After an intentional browser reload, actual HTTP200 response bodies matched the built files:

- JavaScript `assets/index-CsxFLqKL.js`: 804454 bytes, SHA256 `34c33a20bbac80dc1f58f0bf7d3d5c0594cb0409fa0d4a3ce291edd2c5a953bd`.
- CSS `assets/index-Dhx4WPYb.css`: 65027 bytes, SHA256 `b4d6985e1a27b36803c61f2d6e5ff32937761a408305f73ec5d3e0d71f2c1e19`.

HTML's built hash is recorded separately; a served HTML-body hash was not captured. Source/build A1 PNG remains byte-identical to the preserved full image: SHA256 `a7b428a2437da70880fea628dca23c0ded7a24294595b13437b4ae99fe5a09f9`, Git blob `383bf1af9b8e879dfe512840388f09583ddf3bc6`. No served PNG-body hash is claimed.

## Actual rendered results

All four cases rendered twelve distinct cards. Every title was21px or42px high; every card computed flex-shrink0; title clamp2 and overflow-wrap:anywhere remained. Card heights vary naturally with title and localized metadata. No document or list horizontal overflow was measured. Device scale and visual scale were1.

| Case | Actual viewport/document width | List client/scroll height | List client/scroll width | Natural card heights |
|---|---|---|---|---|
| English narrow | 390×844 /390 | 288/1630px | 314/314px | 110.96875,131.96875px |
| Chinese narrow | 390×844 /390 | 288/1420px | 314/314px | 93.4765625,114.4765625px |
| English desktop | 1280×800 /1280 | 512/1861px | 176/176px | 128.4609375,149.4609375px |
| Chinese desktop | 1280×800 /1280 | 512/1651px | 176/176px | 110.96875,131.96875px |

Normal wheel scrolling reached the final displayed card, goal01 (the list sorts newest first, so seed goal12 appears first). Selecting goal01 opened its matching cancelled v3 detail. Both narrow locales and both desktop locales have captures with that selected card fully visible. Repeated selection retained aria-current=true and its visible selection border. The bounded list and outer dialog both remain scrollable. Selecting a different card resets list scrollTop to0; subsequent scrolling and repeated selection work. This observed navigation behavior is reported separately from the fixed title defect.

The 560-character unbroken goal wraps and clips to two lines without increasing horizontal width. The explicitly labelled blank-goal fixture displays `Untitled work` / `未命名工作`; normal RunCreate still rejects blank goals. Actual narrow English and Chinese captures include the fallback and long title. Nine key PNGs were visually inspected; no image editing occurred.

During the controlled four-second create delay, English and Chinese composer Close/Back/Start controls and all twelve underlying cards were disabled. The middleware rejected the request before production dispatch with HTTP409 `QA_FIXTURE_WRITES_DISABLED`; this was a test-only busy-state observation, not a persistent-work execution. The Chinese response body is saved. Controls recovered, and the UI showed its generic unknown-result warning. No create retry was made. The fictional draft was explicitly discarded through the visible guard.

A1 had a zero-size hidden hit target while work dialogs were open and returned after closing them. Desktop before/after rectangles match exactly: x1163.171875,y426,width104.8203125,height340. Narrow restored rectangle: x305.234375,y516,width72.7578125,height236. Assistant/Work/Close controls were usable through repeated opening and closing. The reviewed closeout screenshot shows the original full 2D character. The console API returned zero error/warning entries; no broader console-history claim is made.

## Scoped permission, fixture and closeout

The historical default-sandbox bind denial remained a separate prerequisite until supported scoped execution was allowed and the exact loopback listener was observed. First allowed execution created this round's fresh schema3 Store but stopped before binding on a QA evidence assertion (state was read from JSON instead of its column). The corrected QA launcher verified and reused only that newly prepared synthetic Store, without reseeding, and its separately allowed execution listened only on127.0.0.1:5191. This was not a source defect or an approval rejection.

An initial browser call took985.7seconds; its binding was subsequently recovered using the existing test tab. The service completed its30-minute bounded lifetime. A separately reviewed10-minute extension on the same loopback address completed the remaining captures/served hashes and exited0 at2026-10-13T14:09:11.579886Z. A default-sandbox ps inspection was denied before any signal; no inspection workaround or signal followed, and the timer stopped the service normally. Port5191 has no listener at closeout.

Final Store state: schema3; twelve cancelled v3 runs; zero model/tool calls, model usage, agent steps, public captures, connector intents and computer jobs. Scheduler, real provider, public capture, browser, computer, connectors, replay and hardware execution were disabled. No older database was opened, copied or migrated. English restored; viewport override cleared; the new test tab closed.

Existing acceptance5190 PID82674 and independent demo8843 PID79955 remain listening and untouched. Original main worktree/runtime/8832 were not changed;8832 has no listener. Prior4e and1e reports retain their exact recorded hashes. Existing QA files were not edited in this continuation. Reading reused the same-round186-file ledger, supplementing changed handoff/product/decision/software-check and module/layout contracts.

The pending CSV Save disposition and unknown-effect MCP evidence remain unchanged, without retry/replay. No FYP public-network/provider/hardware execution, existing credential/security change, sandbox weakening or model override occurred. Legacy demo tests remain manual loopback application acceptance, not general cross-app agent capability. This bounded result leaves the prior CSV, public-network, live-model and paired-identity gates outside its scope.

One reviewed fictional PNG was saved to Library as `libfile_f9774079d5f881918d8a29127487f5fc`; local identity metadata was persisted successfully. The complete local capture/measurement manifest and a compact supporting manifest accompany this report.
