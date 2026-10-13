# Mac module resolution correction — frozen integration

13 October 2026. Full existing software check completed with exit0: **1,380 backend / 246 frontend**, Ruff, TypeScript, Vite and unchanged A1/VRM asset provenance. All304 source/test/config/lock hashes match before and after. Existing warning/advisory output is retained in the log.

Actual prior-source Mac failure: [verbatim report and compiler evidence](../2026-10-13-mac-case-resolution/report.md), exact1e52e710. Extensionless `./PublicCapture` resolved to a `.ts` helper on case-insensitive storage instead of the `.tsx` component. No build or UI result was fabricated from Linux CI.

The correction moves helper bytes unchanged from `publicCapture.ts` to `capturePolicy.ts`, changes four production imports and two test resolvers, and adds four whole-src module-path guard tests. [Owner verification](../2026-10-13-case-insensitive-imports/verification.md) records original guard failure, final246 frontend tests, type/build/assets and exact rename paths. [Independent audit](../2026-10-13-case-insensitive-imports-audit/review.md) records28 checks, actual TypeScript resolver simulation in both case modes, import-only diffs and directory-fixture failures/passes. No runtime behavior, locks, backend, CSS, assets, credentials or permissions changed.

Publication must remove the old helper path and preserve the new helper's original Git blob. Parent verifies deletion/addition, all candidate blobs/modes, unrelated remote leaves and branch ref before claiming delivery. Exact CI and actual Mac build/layout remain separate pending observations at freeze.

The original loopback5191 permission error is not resolved by this source fix. Existing Mac task may request its supported scoped approval only after an exact-source build succeeds; no silent escalation, alternate port, security change, old-runtime migration or denied CSV/MCP retry. Actual patched title/layout and public/model/hardware gates are not passed here.
