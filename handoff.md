# Group 2 current handoff

4 November 2026. **PR74–77 are merged into main through [PR85](https://github.com/tantalum666/FYP/pull/85), together with the reviewed Grok journeys.** Code mergeb663204 exactly matches reviewed affbad2d; candidate151f807 is the verified application tree. All four original PRs were independently read back merged. [Receipt](output/qa/2026-11-04-merge-74-77/publication.json), [QA/results](output/qa/2026-11-04-merge-74-77/verification.md). Pi is paused, experimental budgets closed, verification local only.

## Current software

Primary Web conversation, concise shared UI, mobile Alice, explicit local media controls, OpenAI realtime/local Alice wake, persistent application Work and the repaired offline mailbox/shopping/calendar flows now share one code baseline. Existing permissions, proposal decisions, task/job queues and validated backup contracts are retained. [Desktop](desk-companion/docs/desktop-conversation.md), [OpenAI/wake](desk-companion/docs/openai-alice-wake.md), [application Work](desk-companion/docs/application-work.md), [Grok review](output/qa/2026-11-04-grok-journey-review/verification.md).

## Verification and runtime

1769 backend/319 frontend, lint/type/build and actual primary-chat/393px phone checks passed. No new paid-provider, human acoustics, native keyboard, real-account or hardware result. Offline advice remains explicitly different from sending, buying or accepting invitations.

The existing normal preview/private env/wake-model cache in `/Users/tantalum/.codex/worktrees/personal-agent-20261031/FYP` was preserved, not upgraded by this merge. Its current provider configuration must be retained when a later rollout is requested; do not substitute the providers-off QA runtime. Check actual processes/in-flight calls before switching source. Keys, raw media, stores and models remain ignored. The test preview is cleaned up at closeout.

## One next step

Continue ordinary Alice conversation-to-Work admission and interruption/unknown-result recovery on this unified baseline, starting with offline changed-goal cases. Live source accounts, payment and Pi remain separately scoped. Keep [personal-agent research](research/personal-agent-research-index.md) and the existing authority boundaries.
