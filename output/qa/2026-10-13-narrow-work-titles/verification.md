# Retained Work card title preservation

Updated 13 October 2026. This is a focused supplement to the ongoing cloud continuation, against the materialized source supplied as `9cb5fc5` with documentation head `9e4318d`. The coordinator owns remote publication and exact commit verification. No Git operation was performed by this worker.

## Reported defect and diagnosis

The coordinator relayed an actual Mac browser observation on the earlier `4e508411`: retained Work goal titles disappear at 390 × 844. This worker has not seen that browser's DOM measurements and did not run a browser. The source condition remains in the current materialization.

The likely mechanism is a column flex list (`.agent-run-list`) capped at 18rem on narrow screens and 32rem on desktop. Its grid-button children (`.agent-run-choice`) had implicit `flex-shrink: 1`. When enough retained cards consume the list height, their title rows are eligible for compression; those rows have `overflow: hidden` for the existing two-line clamp. Narrower line wrapping and the smaller list cap increase the pressure. This is a source-derived diagnosis pending confirmation from actual browser dimensions; it is not a measured layout result.

## Minimal repair

The only production change is an explicit `flex-shrink: 0` on `.agent-run-choice`, plus a comment explaining why. The bounded list can scroll instead of compressing cards. Both list height caps, overflow policy, title clamp/wrapping, desktop grid, translations, buttons, selection handlers and draft guards are unchanged. There are no source/voice/capture semantics, A1, DeviceApp, backend, runtime database, permission or network changes.

- [Exact production delta](production.patch)
- [Prepatch stylesheet](agent-before.css)
- [Frozen source/test hashes](source-freeze.json)
- [Same-task reading supplement](reading-supplement.json), inheriting the existing 186-document intake

## Software verification

All checks used the existing installed dependencies; there was no browser/dependency installation.

- New focused regression on unmodified CSS: one expected failure for missing zero shrink; three other checks passed. [Before-fix log](regression-before.txt)
- Complete frontend suite: **242 passed**, zero failures/skips. [Full log](frontend-tests.txt)
- TypeScript: passed. [Log](typecheck.txt)
- Production build: passed. Existing large-chunk warning remains; no new build error. [Log](build.txt)
- Bundled A1 PNG and VRM hashes match provenance manifests. [Log](asset-check.txt)

`work-card-layout.test.ts` checks the explicit base-rule non-shrinking constraint and preserves bounded scroll and title wrapping. Its React server-rendered production list JSX checks 100 synthetic long/empty English/Chinese goals, selected/busy markup, and exact selection callback behavior. Status/mode helpers are supplied as test callbacks. This is source and SSR coverage, **not rendered dimensions, browser accessibility, clicks or scrolling**. The test would not detect every future competing CSS rule; actual mounted UI acceptance remains necessary.

The source/test files were frozen before the coordinator's aggregate verification. Shared product, handoff and work log were intentionally not edited by this worker; the coordinator owns those updates. Independent audit and backend/aggregate checks are separate and must be reported from their own evidence.

## Remaining browser verification

The coordinator should revalidate the new exact source in the same authorized isolated Mac setup:

1. At 390 × 844, populate enough retained synthetic cards to exceed the 18rem list cap. Record list client/scroll heights, card computed flex-shrink and goal bounding rectangles; each title must have a nonzero rendered height
2. Check English and Chinese, long unbroken titles and empty-title fallback; scroll to the final retained card and identify/select it without horizontal overflow
3. Check the desktop view with short and overflowing lists; preserve the 32rem cap, two-column layout and goal clamp
4. Repeat selection/open/close and confirm existing busy/draft guards and A1 temporary modal blocking still behave correctly

No true 390px fix acceptance, real microphone/model/public-network test or device/hardware result is claimed here. No remote publication or CI result is claimed by this worker.
