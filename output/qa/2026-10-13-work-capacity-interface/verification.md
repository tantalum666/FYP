# Retained-capacity interface verification

2026-10-13. Same continuing implementation task, inheriting the [186-document intake](../2026-10-12-agent-kernel/reading-union-status.json). Focused rereads: AGENTS.md, product.md (204 lines), handoff.md (54 lines), latest relevant decision-log.md entries, the complete [capacity design contract](../2026-10-13-work-capacity-design/contract.md), all modified existing UI files and existing production-hook/SSR harness examples. No new independent whole-repository intake is claimed. Root owns shared product/handoff/decision/work-log integration.

## Implemented

- Typed global-only contract validation; strict safe integers and consistency checks, null exact totals for unavailable/incomplete over-limit states, server-derived quota values
- Independent visible-owner hook, no polling, one open read, explicit capacity-only refresh, combined explicit Work refresh and useful successful run/source mutation refreshes
- Parent/local epochs and sequence checks; immediate session/privacy/offline event invalidation, hidden/stale/identity mask via parent fence, unmount closure, stale callback rejection
- Actual auth/owner/privacy/context denial invalidates the shared private fence; ordinary capacity 409/transport failures remain advisory-only
- English/Chinese collapsed native Saved work storage disclosure with counts and full/unknown/over-limit warnings visible in its summary, readable KiB/MiB formatting (exact bytes when rounding), per-file/per-run limit labels, deterministic two-output warning and selected-file size warning without capacity-derived action disabling or mutation/reset behavior
- Existing Watch complete-list/limit count and remaining slots, unknown limit instead of hardcoded fallback; explicit cancelled/expired/budget-exhausted retention explanation, no visible-only endpoint in hidden mode
- [Feature document](../../../desk-companion/docs/work-capacity.md); original A1/DeviceApp, exact-ID Watch handoff, search and voice origin/expiry/retry code paths unchanged

## Executed evidence

The new tests execute production hook state transitions and production upload callbacks using deterministic hook slots/deferred promises, plus real React SSR for the component markup. These are software behavior tests, not a mounted browser DOM, layout, Mac, Pi or live-provider acceptance claim.

After the compact-disclosure refinement and independent-review navigation correction, the complete frontend suite passed 194/194 tests. Standalone TypeScript and production build both passed with exit 0 at 08:02:43 UTC; logs are saved alongside this file. A transport interruption during an earlier type/build process was detected; that incomplete attempt was not counted and both checks were rerun to terminal success. The ten UI/test source hashes are in source-hashes.json. Independent reviewer reproduced old RunDetail external-review callbacks surviving capacity denial before React rerender. RunWorkspace go()/commit() now require the current shared response fence; the independent reviewer confirmed that exact repro now passes. The final independent UI audit passed 33/33 executed cases, including original retry keys, voice expiry recovery, upload retries, existing pause/cancel, artifact preview/download transport, exact watched-ID selection, owner/hidden gates and compact summary/Watch counts. Source/tests were explicitly frozen at 08:05 UTC; all ten recorded hashes were verified unchanged. Root owns the subsequent aggregate frozen checks/publication. Existing large 3D bundle warning is informational, not newly introduced capacity behavior.

No live services, credentials, Mac operation, Git write, dependency change or installation was performed by this interface worker. Runtime build output remains local generated output. Real 390px/desktop UI and hidden stop/download/browser behavior acceptance remain separate from these executed software tests.
