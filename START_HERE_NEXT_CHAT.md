# Group 2 · Current continuation

13 November 2026. Continue in `/Users/tantalum/.codex/worktrees/alice-motion-20261113/FYP`, branch `codex/alice-natural-motion-20261113`. Read [AGENTS](AGENTS.md), [product](product.md), [handoff](handoff.md), latest [decisions](decision-log.md) and [motion repair QA](output/qa/2026-11-13-alice-motion-repair/verification.md).

The owner's reversed-hand/stiffness correction is implemented at c65ac229 and belongs to existing [PR123](https://github.com/tantalum666/FYP/pull/123), still unmerged. 379 main/358 compatible frontend tests and both builds pass. Normal Mac web8831 and rebuilt native Simulator show the corrected greeting. A3 is retained. Pi received and served the same compatible frontend, then became unreachable while its local kiosk loaded Alice; physical Pi animation remains unverified. Full main/Grok integration was not deployed as part of this frontend update. No CI or paid calls.

Next: recover the existing Pi connection and check its local renderer, without treating Mac's device view as Pi performance evidence. Preserve all original runtime/data/backups; power diagnosis stays deferred. The previous659403c2 motion clip is historical and was rejected by the owner.
