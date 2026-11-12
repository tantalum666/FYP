# Group 2 · Current handoff

Published as [PR123](https://github.com/tantalum666/FYP/pull/123), open/unmerged; source659403c2matched remote HEAD. [Receipt](output/qa/2026-11-13-alice-motion/publication.json).

13 November2026. Current source checkout `/Users/tantalum/.codex/worktrees/alice-motion-20261113/FYP`, branch `codex/alice-natural-motion-20261113`, based on merged main6153b41d. This turn implements the owner's Alice-action request. Source publication is separate from merge and deployment. No CI; all paid budgets remain closed.

## Current change

Alice keeps her original VRM and size. Added a brief initial/click/tap wave, natural breathing/relaxed arms/occasional glances, listening tilt/nod, thinking turn and speaking hand/head gestures. `alice-motion.ts` owns pose curves; `interaction.ts` carries only local presentation state from AssistantPanel. VrmViewer reuses its current rig, output-level mouth, spring bones and capped render loop. No root/leg/foot motion, model replacement, new polling or business/permission change.

Actual visual checks fixed arm-axis direction/torso intersection and compacted the forward hand lift to fit phone edges. Navigation pauses the scene; system reduced motion disposes it in favor of the existing static fallback. Shared Web/phone/device source is updated; no native or Pi package was activated.

## Evidence and preview

377frontend tests, types and build pass. Real production-build Chrome runs cover1080×900desktop,393×852/320×740phone, initial/tap/keyboard response, real text-send thinking with mock transport, synthetic voice state/speaker level, pause, reduced motion and one-canvas restoration. No app exceptions, failed responses or horizontal overflow. A short sample renders23frames/1050ms under the30fps cap; this is not Pi performance evidence. [QA](output/qa/2026-11-13-alice-motion/verification.md).

Local animation preview at `http://127.0.0.1:8832/` (`?surface=phone` for phone), isolated test store with schedulers/real providers disabled. Private recording/screenshots/harness: `~/.config/desk-companion/alice-motion-20261113/`. The preview uses mock text/synthetic state for visual acceptance; it is not the owner's normal voice/mail/data runtime. A3 resources and credentials are untouched.

## Retained project state

The previous Grok review is merged through PR121/122, main6153b41d; all24original PRs were confirmed merged. Its [review](output/qa/2026-11-11-grok-review/verification.md) retains privacy/version/recovery fixes and the distinction between fixture takeover and a real interactive browser. That integration had not been deployed to the normal runtime.

Last physical deployment evidence remains9November: Mac backend520ab563/frontend2ed9ef41; Pi feature release520ab563verified before relay loss, final safe-area v2sync unconfirmed. A3/Taiwan Light was selected then. Google Mac Gmail self-send was verified8November; FYP Microsoft/Calendar/Pi consent and real merchant takeover remain separate. Power/red-LED diagnosis remains deferred. Do not overwrite original worktrees, configurations, data or retained releases.

## One next step

Carry the verified motion frontend into the next explicitly scoped normal-runtime rollout, checking the exact source/data/configuration first and retaining the large phone Alice. Real interactive owner browser control remains the next personal-agent capability; do not reopen closed model budgets or infer physical-device success from this preview.
