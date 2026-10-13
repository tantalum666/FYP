# Case-insensitive frontend module resolution fix

Continues the existing personal-agent task and inherited 186-document reading record. Baseline source `1e52e7106c03f5a1a365a9859dbec21cb0f921e6`, tree `42079660aad46c72fedc1bace18f22be6bab55a3`. Actual Mac build failure is recorded separately in [the Mac report](../2026-10-13-mac-case-resolution/report.md).

## Correction

Rename `desk-companion/frontend/src/workspace/agent/publicCapture.ts` to `capturePolicy.ts`. The helper bytes are unchanged, Git blob `67630e12e97f8ebdd1407bf684ff78259b8a78ac`. Update four production importers and two test import/mock-resolver files. Keep the `PublicCapture.tsx` component and its extensionless consumers unchanged.

Publication must delete the old helper path, not merely add the renamed file. Exact paths and hashes are in `verification.json`. No package, lockfile, backend, runtime/database, model, network-policy or presentation asset change. The existing `flex-shrink: 0` CSS and its four regression tests remain intact.

## Regression and validation

`frontend/tests/module-paths.test.ts` recursively scans the entire `frontend/src` tree. It groups implementation `.ts`/`.tsx` files by lowercase extensionless relative path and checks directory case aliases. Declaration companions are excluded; different directories and non-module assets remain valid. Source symlinks fail explicitly instead of silently skipping a subtree. Four tests cover the real tree and nested mixed-extension, same-extension, identical-stem, directory-alias and valid-path fixtures. Existing `npm test` wildcard includes the guard in aggregate CI without package changes.

- Before rename: the new guard exited 1 on the actual original source tree, reporting exactly `PublicCapture.tsx` / `publicCapture.ts`; other guard cases passed (`guard-before.log`). No other module/directory ambiguity was found
- After rename: the guard passed 4/4 (`guard-after.log`)
- Full `npm test`: 246 passed, 0 failed (`frontend-tests.log`)
- Separate `npm run typecheck`: exit 0 (`typecheck.log`)
- `npm run build`: exit 0, 2020 modules transformed (`build.log`); existing large-chunk warning remains
- Existing `.venv/bin/python scripts/check_assets.py`: exit 0, bundled VRM and A1 match provenance (`assets.log`)
- Source snapshots before/after each contain 121 files. Exactly the four import-only files changed plus the byte-identical helper move; all remaining production source bytes, including CSS, stayed unchanged

Checks used existing installed dependencies; no install was run. This is Linux software verification, not a successful Mac build or layout acceptance. Parent owns publication and exact-SHA retesting through the existing Mac task. No browser, live provider, public capture, user database, hardware or security-setting action was performed here. Backend suite was not rerun for this frontend-only change.

## Documentation ownership

No authored document references the old helper path. Parent owns updates to software-checks/product/handoff/work-log; requested one software-checks sentence describing the guard. This worker only changed the listed frontend files and this QA directory.
