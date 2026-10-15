# Group 2 Current Handoff

Updated: 15 October 2026. **The reviewed #7–#14 code stack is merged into main. This #6 delivery reconciles the tooling research and records the independent review.** PRs #4 and #5 remain separate.

## Current state and evidence

- Owner-reviewed facts, one owner-named folder on the existing note-job ledger, a shared persona, quiet-hour holds, failure/recovery copy and replaceable text adapters are implemented.
- Review fixes close paired access to facts through assistant/text/voice paths; reject symlinks in every folder ancestor; preserve persona versions across reset/migration; and retain drafts and repeat-safe save recovery. source-map-js is patched to 1.2.2.
- [QA](output/qa/2026-10-15-grok-review-merge/verification.md): actual merged code `2c1e465` passed 182 backend tests, 17 frontend tests, Ruff, typecheck, production build and npm audit (zero findings). Browser fixtures cover memory persistence/lost replies, conflicting persona editors and an independently verified folder write. One upstream Starlette test-client deprecation remains.
- Providers were disabled; no live model, camera, microphone or hardware action. Two temporary browser tabs, interception, viewport override and QA server were cleaned up. Original A1 branch and private runtime were not changed.
- A1 is the user's selected identity and intact 2D is the latest visual direction, retained on [PR #4](https://github.com/tantalum666/FYP/pull/4). The separate kernel is [PR #5](https://github.com/tantalum666/FYP/pull/5). Neither is part of this merge.

## Remaining

Named real-application/remote-PC execution; archive and complete business backup; owner choice of real provider/model and spend cap; real voice/wake/AEC and consented posture labels; Pi/iPhone/optics/RIG/cleaner verification. School submission status was not refreshed. Research notes are dated evidence, not measurements of commercial products.

## One next step

**Define one real target computer/application task and allowed data scope, then validate approval → execution → independent read-back, including refusal, cancellation and unknown-result recovery, on the existing JobService.**
