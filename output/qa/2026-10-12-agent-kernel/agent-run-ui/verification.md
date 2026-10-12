# Durable work UI verification

Date: 12 October 2026, 15:15 UTC. Group 2. This is the second implementation batch, after published first checkpoint `546734273c9c8305cf6226e96a8e07854ba5c0b1`. It does not claim the second batch has been published or browser-accepted.

## Delivered frontend scope

- New `desk-companion/frontend/src/workspace/agent/` components, typed contracts and memory-only source-upload adapter; new `frontend/tests/agent-runs.test.ts`
- Compact Work tasks entry and focused modal; explicit persistent-run creation, current-source/provider review, source upload/inspection, fixed local versus bounded adaptive model labels
- Exact source/task/calendar selection and scope revision; separate local retention and provider transmission choices; optional required sections and model-proposed changes remain subject to exact later review
- Goal/plan/step/status/evidence/partial-coverage display; answer, pause, cancel, revision and explicit uncertain-model retry controls
- Independent cancellation mutation queue; frozen expected versions rather than silently rebasing a draft; no request bodies in local/session storage
- Pending/unexpired proposal links only; parent-owned AssistantPanel integration fetches the actual existing proposal review
- Real artifact metadata, plain-text preview and explicit download with byte-size/SHA-256 comparison; saved bytes, structure and semantic quality remain distinct
- Identity, session, private visibility and selected-run fences; modal/navigation draft guards; English and Simplified Chinese; wrapping small-screen layout

Parent owns AssistantPanel integration and root documentation. Other workers own backend, browser panel and artifact services. No backend, artwork, DeviceApp or existing personal-context source was changed by this frontend task. No push was performed by this worker.

## Checks actually run

From `desk-companion/frontend`:

1. `node --experimental-strip-types --test tests/agent-runs.test.ts`: **13 passed**
2. `npm test`: **75 passed, 0 failed** across the current shared frontend tree. [Log](frontend-tests.log)
3. `npm run typecheck`: passed
4. `npm run build`: TypeScript and Vite production build passed. Existing large-bundle warning remains; it is not a failed build. [Log](frontend-build.log)
5. Local Prettier applied only to this task's new frontend directory/test

Focused tests cover retained-run opt-in, verified source eligibility, exact provider grants, business sharing, source/count/section ceilings, immutable reviewed payloads, explicit uncertain-model retry, upload UTF-8/filename/size checks, same-key raw Unicode upload recovery with browser storage made inaccessible, evidence labels, privacy epoch transitions and source-level integration invariants.

The component-contract tests inspect integration source; they are **not React DOM or real browser tests**. They supplement behavior tests for pure request/action/recovery helpers. Source hashes are in [the manifest](source-hashes.json). Supplemental Markdown reading, including repaired truncated ranges, is recorded in [the read ledger](reading-ledger.json).

## Review fixes and remaining acceptance

Independent review led to explicit Composer `Modal.dirty`, source byte-limit enforcement, pending/unexpired proposal gating, unknown-source exclusion, combined model-selection limits and a dedicated `retry_model` confirmation. Additional fixes prevent leaving an unresolved upload through the review step, reset discarded controls on internal navigation and fence before as well as after dispatch.

Real browser acceptance for this second batch remains required: English/Chinese and narrow layout, nested dialog focus/Escape/discard, file selection and unknown upload recovery, actual source → retained run → Markdown/CSV preview/download, partial coverage, live proposal review, repeated controls, owner→paired and hide→show late responses, stale-version recovery, and independence from ordinary chat/A1. The earlier Mac checkpoint QA does not validate these new components.

No real provider, microphone, external account, hardware, external notification or browser-control action was used in these checks. Fast-running work can change version while a pause/cancel review is open; the UI fails closed and asks for a fresh review rather than automatically retrying or rebasing. Source/run/artifact deletion is not implemented and persistent retention is disclosed before creation/upload.

**Hidden-context control limitation:** RunPanel closes and disables its entry while private context is hidden, offline/stale or unavailable to an owner. Although the backend permits owner metadata-only pause/cancel while Hide private is on, this UI does not expose that separate control projection. There is no other agent-run stop button in that state; the existing device Stop controls physical/output jobs. A connected owner can reveal private context and then cancel. Revoked/hidden context blocks further authorized dispatch, but already dispatched work may still complete; this is not immediate remote cancellation or rollback. Adding a metadata-only stop surface is separate follow-on work and must not rehydrate goals, sources or previews.
