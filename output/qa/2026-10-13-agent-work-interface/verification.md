# Group 2 | Agent work interface continuation

Completed source/checkpoint: 13 October 2026, cloud workspace. This continues the existing implementation and inherits the 186-document reading ledger; it is not a new whole-repository reading claim. This interface change touched only `desk-companion/frontend/src/workspace/agent/`, three focused test files and a test-only TSX loader. AssistantPanel, browser/connector review-panel routing and backend services have separate integration changes.

## Implemented user flows

- A connected owner with hidden private context can open a content-free Work list and pause or cancel a versioned run. Only opaque ID, known state, version and normalized timestamps are retained/rendered. There are no hidden-mode scope, detail, source, proposal or artifact requests. Goals, source names, questions, mode, reasons and file/review content never enter the hidden view's state, even if a list response unexpectedly includes them
- Pause and cancellation use independent memory-only queues. An in-flight or uncertain pause does not disable cancellation. Repeated recovery retains the exact operation key/body/version; polling failure leaves only safe rows mounted, disables controls until refresh, and preserves recovery. Stale version checks prevent changing a newer run through an old confirmation. Session/privacy transitions remount the view and invalidate late replies
- Explicit chat-to-work handoff prefills only the requested text. It chooses model mode only when the scope actually advertises it; otherwise deterministic compilation remains clearly labelled. No source, personal context, connector grant, provider choice, sharing permission, retention choice or Start operation is automatic. Original chat text stays in the assistant input. Active Work drafts/retry data require guarded navigation before replacement
- The Work modal has its own guard registry; an unsent parent chat message is not mistaken for an existing Work draft. This was checked against the actual Modal implementation and a React rendering regression
- Model mode can select current public browser catalog entries, with separate public-only permission. Public browser sources count toward the ten-item evidence limit. Linked reviews/results open the existing browser panel rather than exposing an approval method in the run component. Verified export bytes remain distinct from unresolved execution/cleanup
- Operator-granted MCP tools are opt-in, capped at eight and require separate permission to return public/synthetic responses to the selected exact model destination. They cannot coexist with private files, tasks, calendar records or selected memory/history. Every call still uses the separate exact review. Linked cards use the service's opaque intent ID, never an arbitrary remote review URL; a returned MCP response is not independently verified completion
- Personal continuity is explicit: up to eight permitted facts plus one permitted saved thread, no automatic current-chat selection. A separate derived-output-retention acknowledgement explains that reports/plans/drafts may repeat the chosen context and earlier outputs/provider copies are not erased by later forgetting. Personal context is not source evidence or action approval. Invalidated context bindings cannot be renewed through Resume or steering
- Model/tool attempt limits default to eight with service ceilings of 24/16; lower supplied ceilings are enforced. The UI calls these attempt limits, not monetary budgets. Unknown paid calls require their separate retry review
- All added controls, notices and errors have English/Simplified Chinese copy. Existing output previews remain escaped text. A1 and DeviceApp were not changed

## Verification actually run

- `node --experimental-strip-types --test tests/agent-*.test.ts`: 42 passed, 0 failed, including existing run regressions (`focused-final.log`)
- `npm test`: 125 passed, 0 failed, no skips (`frontend-aggregate.log`). The prior baseline was 79 tests; this final run also includes the concurrently integrated connector-review checks. The manifest pins this interface change, not every parallel integration file; later source changes require a fresh aggregate run
- `npm run typecheck`: passed (`typecheck-final.log`)
- `npm run build`: passed (`build.log`); existing large-chunk warning remains
- `.venv/bin/python scripts/check_assets.py`: passed; bundled complete A1 PNG and licensed VRM match provenance (`assets.log`)

Seven new tests render the actual production components with React's server renderer: English/Chinese hidden cards, stale/terminal controls, browser uncertainty, unselected permissions, incompatible selection disabling, connector result labelling and modal guard isolation. The test-only loader uses the installed TypeScript compiler and Node's supported module-registration API; it does not install dependencies, run a browser or change production execution.

Other tests exercise real request projection, selection/consent validation, immutable request snapshots, independent write queues and permanent identity/privacy fences. A small set of source-structure assertions checks hook/component integration. Neither these checks nor successful compilation are evidence of actual browser interaction or genuine model planning.

## Explicit limits and next integrated check

No live model/provider call, external connector call, Mac operation, browser security retry, credential setup, push, merge, deployment or hardware operation was performed in this interface verification. Existing cloud-browser/DNS restrictions remain unchanged. No new Playwright acceptance, real downloaded CSV, private external-account flow or target-device performance is claimed. Closing a panel does not cancel server work; cancellation does not undo completed effects.

The integration gate is to finish the exact connector review-panel routing, rerun the aggregate on the integrated final source, and check the hidden-owner stop and chat-goal/review transitions in an authorized real browser when available. Continue independent cloud work rather than treating this source/checkpoint as complete personal-agent capability.

`source-manifest.json` pins the interface source/test bytes and verification logs. `reading-supplement.json` records the inherited reading basis and actually reread related contracts. Root handoff/product/work-log updates and Git publication are recorded separately for the integrated task.
