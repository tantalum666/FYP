# Independent case-insensitive module audit

2026-10-13. Result: **PASS for the scoped source fix and regression guard**. Actual Mac build and layout acceptance remain separate.

## Findings and scope

- Reproduced the root cause with installed TypeScript 6.0.3 and the actual `bundler` compiler options. An independently supplied case-insensitive resolution host resolves `./PublicCapture` to the `.ts` helper before trying the `.tsx` component. Case-sensitive resolution instead reaches the component. This is a resolver simulation, not a Mac build.
- After renaming the helper to `capturePolicy.ts`, both case-sensitive and case-insensitive resolution reach the intended modules for RunComposer, RunPanel, PublicCapture, SourcePreview, CaptureProvenance and usePublicCaptures. The retained component export and helper type sharing the identifier `PublicCapture` are legal in separate modules. The hook still uses `import type` for its interfaces and runtime imports for actual helper functions.
- The helper is byte-identical to the pre-edit snapshot. All six modified existing source/test files differ only by the helper import specifier. Existing component import sites remain unchanged. No stale old helper reference remains in frontend source/tests except the deliberate historical-collision regression fixture.
- The new guard walks all frontend `src`, uses extensionless case-normalized TS/TSX path keys, checks case-only directory segments even when child basenames differ, rejects source symlinks rather than silently omitting them, and permits genuinely distinct directories and declaration companions. It covers the current 51 TS and 57 TSX source files; the 13 CSS files are intentionally outside implementation-module collisions. It does not claim arbitrary future JS/MTS/CTS, Unicode filesystem normalization, package alias, or general import-spelling coverage.
- The actual directory walker was independently exercised against four isolated synthetic trees. Original mixed-extension pair, nested same-extension collision and case-only directory trees all fail as intended; distinct-directory/declaration pairing passes. Generated colliding trees were removed after preserving logs so they cannot themselves introduce checkout collisions.
- The guard enters existing `npm test` via `tests/*.test.ts`. The existing check script runs that command before the build, and the existing Ubuntu GitHub workflow invokes the script. No package or workflow change is necessary.

## Independent evidence

- `ts-resolution.json` and `resolve-modules.cjs`: actual compiler resolver reproduction and six fixed import paths, both host modes
- `minimal-diff-check.json`: unchanged helper bytes and import-only replacements
- `independent-delta.json`: required source/test additions, modifications and deletion
- `targeted-tests.log`: 28 independently rerun module guard, capture lifecycle and rendering tests passed
- `scanner-fixture-results.json` and `scanner-*.log`: four independent real-directory scanner fixtures matched expected outcomes
- `baseline-manifest.json`: pre-change frontend source/test hashes

Implementation-owner logs in `../2026-10-13-case-insensitive-imports/` were reviewed: 246 frontend tests passed, separate typecheck and production build completed, and existing A1/VRM asset checks passed. These aggregate checks are attributed to the owner, not claimed as independently rerun here. No browser, network, package installation, credentials, user database or Mac state was changed by this audit. No production code, shared project documents or Git state was edited.

## Publication requirements

Publish deletion of `desk-companion/frontend/src/workspace/agent/publicCapture.ts`, addition of `capturePolicy.ts`, all six changed import-bearing source/test files, and the new `tests/module-paths.test.ts` together. Adding the new helper without deleting the old one leaves the original Mac shadowing defect. Verify the final remote tree contains the new helper and component but not the old helper, then rerun the Mac build on the exact published source before resuming the existing narrow-layout acceptance. Source/CI success cannot substitute for this result.

## Intake and closeout

This is a supplement to the same ongoing task's inherited 186-document intake at `../2026-10-12-agent-kernel/reading-union-status.json`, not a new claim of full-repository reading. Re-read AGENTS.md (1–50), product.md (1–232), handoff.md (1–68), software-checks.md (1–31), public-captures.md (1–191), and decision-log.md latest decisions (850–904). Relevant package/TypeScript/Vite/workflow/check-script configuration, helper and guard were inspected. Existing import-bearing source/tests were compared byte-for-byte to pre-edit snapshots after the exact expected specifier replacements. Dependencies/build output and automatic QA snapshots were excluded from authored-document intake. Reading and checks completed at 2026-10-13 13:01 UTC; project closeout/publication records remain the parent and implementation owner's responsibility.
