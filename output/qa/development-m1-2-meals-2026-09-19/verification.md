# M1.2 local software verification

2026-09-19 · Group 2 · LOCAL_PROTOTYPE_VERIFIED. Scope: station-confirmed personal meal pairing, sequential portions, versioned reference nutrition and anonymous school samples. P0 / M1.1 history remains valid for its own scope. This report does not establish hardware, model, clinical or commercial performance.

## Preparation and isolation

[Full reading record](reading-record.json): 81 owned Markdown files / 7,136 lines, 66 batches plus the individually reread truncated batches. No reading-period file changes. Context compaction reused that completed record. Subsequent relevant edits and new authored documents were reviewed without restarting the library read.

Private backups: .runtime/backups/m1-1-before-meals-20260919.dump and m1-1-code-before-meals-20260919.tar.gz. New tables were added without resetting the live DB. Original demo API8799 / Web127.0.0.1:5177 is preserved; UI QA uses senplate_meals_qa / API8800 / Weblocalhost:5178. These are software environments, not two hardware stations. Native Debug Simulator has a fixed QA-only endpoint selection and a separate Keychain service.

## Automated checks

| Check | Observed result |
|---|---|
| Full Python API suite | **55 passed**, 34.02s, 2 upstream Starlette/httpx/anyio deprecation warnings; 33 retained tests + 22 meal cases |
| Ruff | API, tests, dev.py and new QA setup script pass; an overly broad historical-script check found 25 pre-existing style violations in build_business_plan_zh.py, which was not edited |
| Web | TypeScript / Vite build passed; final build and formatting output retained in web-build.log |
| iPhone Simulator build | Xcode26.6 / iOS26.5 build and launch succeeded; own 17Pro and SE3 only, Rillora untouched |
| Generic iphoneos build | **BUILD SUCCEEDED**, signing disabled; validates physical-camera compilation, not signing or physical capture; see iphoneos-build.log |
| Pair code and QR | Swift parser: 4 accepted / 12 rejected; menu parser refuses meal codes. Vision decoded the actual browser-rendered pairing QR from 01-device-pair-request.png |
| Data provenance | 4 raw USDA hashes and 20 normalized nutrient values match their source responses |

### Six successful staged native runs

XCResult files live under /Users/tantalum/Library/Developer/XcodeBuildMCP/workspaces/FYP-db1e8417c72a/result-bundles. Exported attachments and manifests are in ios-01, ios-02, ios-03-pass, ios-04-pro, ios-04-se3 and ios-05.

1. test01RequestPairing: 34.1s. Own QA account submits meal code; PIN5525 matches Web applicant Jamie QA. Device approval performed through Web, not automatically on the phone.
2. test02BeginRice: 21.6s. Native chooses rice, captures zero start; confirmation disabled until a valid increase.
3. test03RecordAndComplete: 56.3s. Native records rice200 / chicken100 / broccoli150; provided450, remaining350; reference477.5kcal /39.97g protein. Further weight inputs in this stage use the QA API fixture, not a physical scale.
4. test04RecordsChineseAndLargeType on 17Pro: 52.7s. English / Chinese history and maximum accessibility type, including persisted language after relaunch.
5. Same read-only review on SE3: 104.4s including simulator preparation; narrow-screen English, Chinese and large-type screenshots inspected.
6. test05PreservedDemoPreview: 35.3s. Normal endpoint / original account still displays order#003; English Home shows the new meal entry. It does not accept, fulfill or cancel that order.

The initial stage3 failed only at an exact-label assertion: SwiftUI combined “Energy, 477.5 kcal” under nutrition.energy_kcal. Screenshot and API already showed correct completion. Fixed the test locator, preserved the failed bundle / attachments in ios-03, and reran the stage against a new isolated QA meal successfully. No live records were reset.

## Cross-client and fault evidence

[Checkpoints](cross-client-checkpoints.json) and [sample CSV](anonymous-samples.csv) contain source-tagged, non-secret snapshots.

- Personal pairing code expired after120s and required explicit station approval. Backend also covers expiry, rejected / reused / wrong-purpose codes, competing applicants, revoked users and cross-workspace console keys.
- Web sending an unstable200g reading disabled portion confirmation; fresh stable200g restored it. Native choice immediately appeared on the station. Portion-window tests reject gaps, late unprojected packets, decrease, plate removal and tare/calibration changes. Plate removal between items also blocks finishing based solely on a matching final weight.
- Personal meals are unavailable to work context / other users. Work snapshot exposes a mode notice, with no personal weight, events, portions, reference nutrition or history. Completed device screen does not keep the prior private meal visible.
- School sample S-79A94FA1C0: 450g provided,300g remaining, complete reference match. S-F267136ADE: unknown mixture250g, plate removed, remaining null, nutrition unavailable. Report: 2completed /700g provided /300g observed remaining, **1 with remaining /1 unknown**. No child accounts or waste/consumption ratio.
- Completion response was deliberately held after HTTP200 for operation41ac6927-bd06-443e-9c61-ed3e98735b1d. Browser timed out, kept the original pending key after reload, then recovered through “Check and retry”. Database has **one** completion history row. Fault interception was cleared afterward.
- A held references response separately timed out. The catalogue error remained visible and station actions stayed disabled through successful active-state polling. Refresh reloaded references and restored actions. This validates the distinct reference-load error handling.
- School filters: Device source returned no simulated samples. Chinese dates use Chinese formatting. CSV API parsed into2rows with a blank unknown remaining field, explicit simulated source and illustrative_unreviewed plan. Export UI was exercised; no claim of external delivery.

## Visual inspection

Reviewed native pairing, English completed portions, reference nutrition, Chinese detail and SE3 normal / maximum-type screenshots. No truncated quantity / food labels were observed in these inspected states; long pages scroll. This is not a full VoiceOver audit.

Reviewed Web at1440×1000 and390×844. Narrow document scrollWidth equals390; no horizontal page overflow. Captures include 04-device-school-en.png, 05-school-report-zh.png, 06-school-report-narrow-zh.png and 09-school-report-final-en.png. Source and uncertainty labels remain visible.

React review covered unconditional hooks, stable record keys, event-driven writes, effect cleanup and obsolete-response guards, labels / disabled states, immutable updates and localized dates. Adding hooks during Vite HMR caused one transient development-only hook-order error; a full reload restored correct hook order. Subsequent final-state logs were checked separately. No production-render failure was inferred from that HMR transition.

## Preserved state and open work

Original run1807c798-872f-469f-b88c-db49050f5455 remains1600g. Orders#001collected /#002ready /#003submitted remain. The private QA dataset holds the meal examples. The standalone device screen is ready to start another test; original workbench and normal iPhone endpoint retain their existing accounts.

Physical data collection, weighing calibration/tolerance, RGB-D / model accuracy, Pi load, real-camera capture, iOS17, native response-loss injection, full VoiceOver and long-duration load remain unverified. Current samples use stepped simulation time and do not establish a continuous real-world measurement rate. Camera/scale cannot rule out an unobserved equal-weight substitution; cooking state and added ingredients require reliable human/reference matching.

Next batch: M1.3 food / recipe / reviewed-plan configuration and meal-end disposition, starting with a shared versioning / reporting contract. Source/input confidence and current baselines remain; no deployment, submission, purchase, trademark filing, external message, initial commit or sub-agent work.

The document / protected-asset / link / identity closeout is recorded in [closeout-validation.json](closeout-validation.json).
