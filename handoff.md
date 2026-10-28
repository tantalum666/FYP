# Group 2 Current Handoff

28 October 2026, Asia/Hong_Kong. Current continuation: **older-memory continuity and shared memory browsing**, on `codex/native-memory-reliability-20261028` in `/Users/tantalum/.codex/worktrees/grok-reviewed-fixes/FYP`. Base is main `9bfe2eedf0ea05b9f7d143a18388d84e36e19de0` (local-validation-only policy). Publication is recorded in this checkpoint's QA; a branch/PR is not main merge or deployment.

## Completed in this checkpoint

- Fixed the recent40 prompt window being mistaken for all memory: English/Chinese queries, correction/deletion drafts and exact forgetting now cover all active facts. Shared filtered projection preserves owner checks, confirmation/version checks and bounded prompt/results.
- Deletion/expiry outside that40-fact window now changes the conversation revision and clears stale replay/recall focus. No additional transcript store, model connection or provider fee.
- `MemoryFactList` handles shared web/phone search/rendering; `MemoryPanel` owns requests/writes/draft guards. During correction, search and competing fact actions are locked. Save/error messages stay near the list and previous wording has a separate line.
- [QA](output/qa/2026-10-28-native-memory/verification.md):8 failures reproduced before repair;43 focused and459 full backend checks,89 frontend, Ruff/types/build. Actual1365×900 web,393×852/320×740 phone search, correction, navigation/draft recovery and API readback passed. Phone browser Plan→New→Save→Back passed.
- Current source was built, installed and launched on iPhone17Pro/iOS26.5. Live native Alice frame and the event saved in the browser were visible. **Native touch/soft keyboard remains unverified:** mirror taps did not produce app transitions, while native CUA showed a transformed/offscreen Device Hub thumbnail and rejected coordinate input. Builds/AX labels do not close that gate.

## Current environment and preserved work

- API `127.0.0.1:8832`, exec85864; Vite `127.0.0.1:5191`, exec5997. Isolated runtime: this checkout's `desk-companion/.runtime/native-memory-20261028`, with42 fictional facts and a demo event. Preview loopback enabled, providersnone; background/extraction/push/computer/Linux executorsoff. Recheck listeners before reuse.
- Simulator UDID `F57B6381-6448-434C-AE61-A2663F3458A7`, bundle`dev.group2.deskcompanion`; launch-only defaults override selects API8832. Native saved server/TLS policy unchanged. Mirror `http://localhost:3200`, exec56630, scoped to that Simulator with cleanup trap.
- Previous #60/#61 runtimes/worktrees and school files are preserved; old5190/8831 processes were not running at startup. Do not present old process IDs as active or migrate private data automatically.
- Grok20–59 plus#60 were already merged through[PR61](https://github.com/tantalum666/FYP/pull/61); all41 original PR receipts remain in[prior QA](output/qa/2026-10-28-grok-review-merge/publication.json). This continuation does not reopen that review or merge unrelated historical PRs.

## Boundaries

**Local validation only; no GitHub CI.** Pi paused, previous paid budgets closed, no live media or external accounts used. Qwen remains the measured baseline; alternatives and fair comparison remain open. Alice and Plan/More are retained. Full product readiness is tracked by[delivery gates](desk-companion/docs/delivery-readiness.md), including native/real-device acceptance, human voice, notification delivery and posture.

## One next step

Validate one actual task from web discussion through exact-content approval, the existing bounded file job, independent result verification, and phone continuation; include lost acknowledgement/restart without duplicate execution. Use a disposable local fixture and offline/scripted model responses, reuse TaskService/JobService and fix observed integration failures. Native input remains a separate open environment gate rather than a reason to stop independent software work.
