# Work interface refresh lifecycle review

Updated 2026-10-13. Same implementation round; inherits the completed 186-document reading union. Focused source review covered work metadata, goal handoff, selected context/tools, connector results/reviews, Assistant routing, Modal/DraftGuard and private mutation queues. No browser launch, network operation or backend modification was performed.

## Confirmed issue and localized correction

`useAgentRuns` previously cleared its entire snapshot whenever any list/scope/detail poll failed. `RunPanel` conditionally mounts `RunDetail` and `RunComposer` using that snapshot. A transient background refresh could therefore destroy an unsent goal/control draft and clear an uncertain write's original operation ID through mutation-hook cleanup, without a discard decision. This was proven by the source lifecycle, not claimed as browser reproduction.

The corrected hook retains the exact same-view snapshot only for explicit connection loss and HTTP 408/429/500/502/503/504 errors. It reports `fresh: false`; control/start/retry/review entry points and source upload dispatch are disabled. Current draft state and mutation queues remain mounted. Authentication/privacy failures, missing resources and unexpected failures still clear, as do selection/session/privacy transitions and the containing workspace's disconnected state. Per-read failure guards also handle a later access denial after a parallel request first failed transiently.

`SourceUpload` checks a current freshness ref after asynchronous local file reading and before POST, and checks it for exact-request retries. Initial chat goals wait for current scope before acknowledgment, so initial loading does not consume a goal without opening its composer.

Changed production files are confined to `useAgentRuns.ts`, `RunPanel.tsx`, `RunDetail.tsx`, `RunComposer.tsx` and `SourceUpload.tsx`. The run contract was updated; no shared mutation implementation or connector behavior was changed.

## Local evidence

- 34 focused frontend tests passed: agent refresh lifecycle, agent metadata, rendered markup, and agent work tools
- Full frontend suite passed: 131 tests, zero failures. The first full run identified an old exact-source assertion that required the former unconditional clearing behavior; its expected contract was updated to conditional fail-closed clearing and a freshness-gated but independently queued Cancel button, then the full suite passed
- TypeScript `tsc --noEmit` passed after the correction
- The new five tests execute the actual data-hook source with deterministic React-style hook slots and deferred reads. They establish snapshot identity across failure/recovery, stale flags, fail-closed error classification, the parallel late-denial race, selection/privacy fences and freshness wiring
- Existing queue tests continue to establish stable immutable IDs and separate cancellation queues
- These hook/SSR/source checks are not a mounted React browser or Mac interruption test. Parent integration owns final production build, release hashes and later actual UI acceptance

## Additional review result

No other concrete blocker was established in the reviewed connector path: approval and cancellation have separate queues, unknown approvals remain locked, exact acknowledgment keys bind displayed version/hash/content, refresh failure does not recreate their queue owner, and results are presented as untrusted observations. Parent chat text is retained when handing a goal to work. Full hidden/offline/session/linked-modal acceptance still needs the planned actual Mac UI exercise.
