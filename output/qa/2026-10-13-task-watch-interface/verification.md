# Task-change watch interface verification

Date: 2026-10-13. Same ongoing personal-agent implementation intake; this UI slice inherited the 186-file full-reading ledger and focused rereads. Source edits started only after the parent released the voice publication freeze.

## Implemented

- A sibling English/Simplified Chinese “Watch task changes / 关注事务变化” entry beside scheduled routines. Owner-only private creation/review; hidden mode stores a metadata projection and permits only pause/cancel.
- Explicit 1–10 task IDs and six supported field choices, selected-scope fingerprint, separately acknowledged local retention, explicit UTC expiry within 30 days, lifetime and UTC daily review budgets. Accounting labels use the actual persisted budget day, not an inferred “today.” No automatic task enrollment or initial review.
- One coalesced pending review with separate version-exact acknowledgment; opening or reading never acknowledges. Current-task inspection reads the existing guarded API and labels titles/values as current records, not historical snapshots.
- Private read hook with selection/generation/epoch fencing; transient same-view read failures preserve the editor and exact unknown-write queue while disabling actions/retries. Identity, hidden, offline/stale and access/context revocation remove private state. Inspect denial and redacted success also invalidate the parent immediately.
- Read and mutation `RESPONSIBILITY_CONTEXT_CHANGED` is a privacy boundary, not a reason to resubmit a new operation. The private draft/queue is cleared and the owner is told a sent action may have saved and to inspect current history before repeating. Exact retries survive only same-view transient failures, never a revoked epoch.
- Explicit “Compile current task evidence” prefills a fresh deterministic Work review with every enrolled task ID. Missing IDs block rather than silently shrink scope. Retention and sharing remain unchecked; no memory/conversation/provider/browser/connector/mutation grant or voice origin is copied. Work still requires its existing review and Start. Watch acknowledgment and independently started Work remain separate.

## Checks

- `npm run typecheck`: passed; [log](typecheck.log)
- `npm test`: 186/186 passed, including 17 new task-watch tests; [log](frontend-tests.log)
- `npm run build`: passed; existing >500 kB chunk warning remains; [log](build.log)
- New suites: `responsibilities.test.ts`, `responsibilities-lifecycle.test.ts`, `responsibilities-callbacks.test.ts`, `responsibilities-render.test.ts`
- Executed production hooks and mutation callbacks using deterministic hook slots/deferred transports, including unchanged-read no acknowledgment, stale action callbacks, unknown-response exact operation retry, parent privacy clearing, context-changed 409, current-record denial/redaction and bilingual task status. These are not mounted-browser interactions.
- Rendered actual review components in both languages, checking escaped titles, disabled stale controls, missing-ID block and independent acknowledgment/compilation language.
- Existing voice origin/expiry/dirty-navigation/privacy/retry and work-search suites remained passing. No changes to voice implementation or search implementation.
- Independent UI audit evidence is maintained separately under `../2026-10-13-task-watch-ui-audit/`; findings about current-task privacy propagation and current task status were fixed and rechecked.

## Boundaries

No new dependencies, service/provider calls, microphone, notifications, user computer access, Git operation, A1/art asset change, hardware action or automatic run creation. Production build writes its normal ignored distribution output. Actual mounted browser, mobile/Pi and live model acceptance remain separate. Backend SQLite/evaluator/worker verification and shared capability documentation are owned by the parent/backend workers.

## Focused reading

Inherited evidence: `output/qa/2026-10-12-agent-kernel/reading-union-status.json`, complete 186-file union. Focused complete reads: AGENTS.md; product.md (split to avoid truncation); handoff.md; source-change-responsibilities-design.md; routines.md; task-tracking.md; personal-context.md; agent-runs.md; voice-work.md. Source-level reads covered the changed components plus existing RunPanel, RunComposer, types, useAgentRuns, private mutation queue, response fence, DraftGuard, Modal, owner workspace context and relevant hook/render/voice tests. No new full-repository reading claim is made for this continuation.
