# Group 2 current handoff

6 November 2026. After a text or voice goal change steers one current Work run, the same conversation shows one verified result from the existing offline deterministic executor. The result's goal line is the changed goal. An unverified, failed, or interrupted result is not shown as success. The same operation id does not publish or show it twice. [Contract](desk-companion/docs/conversation-work.md), [QA](output/qa/2026-11-06-conversation-work-verified-result/verification.md). No new task store, queue, schema migration, or model approval tool. No paid call.

Merge note for Codex: #89, then #90, then #91, then this PR. Each PR is one offline conversation-work slice on the previous branch. Do not merge this PR before #91.

4 November baseline remains: **PR74–77 are merged into main through [PR85](https://github.com/tantalum666/FYP/pull/85), together with the reviewed Grok journeys.** Code mergeb663204 exactly matches reviewed affbad2d; candidate151f807 is the verified application tree. All four original PRs were independently read back merged. [Receipt](output/qa/2026-11-04-merge-74-77/publication.json), [QA/results](output/qa/2026-11-04-merge-74-77/verification.md). Pi is paused, experimental budgets closed, verification local only.

## Current software

Primary Web conversation, concise shared UI, mobile Alice, explicit local media controls, OpenAI realtime/local Alice wake, persistent application Work and the repaired offline mailbox/shopping/calendar flows now share one code baseline. Existing permissions, proposal decisions, task/job queues and validated backup contracts are retained. An explicit goal change from text, from a reviewed voice snapshot, or from the voice review screen uses the same steer, then shows one verified offline result in that conversation. [Desktop](desk-companion/docs/desktop-conversation.md), [OpenAI/wake](desk-companion/docs/openai-alice-wake.md), [application Work](desk-companion/docs/application-work.md), [Grok review](output/qa/2026-11-04-grok-journey-review/verification.md).

## Verification and runtime

This slice: ruff on the touched Python, conversation-work 60 passed, integration acceptance 7 passed. The full backend pytest suite was 1828 passed and 1 failed. The failure is the pre-existing `test_public_unicast[::ffff:93.184.216.34]`; this slice does not change that transport check. Frontend tests passed 323, and `tsc --noEmit` passed. No new paid call. [QA](output/qa/2026-11-06-conversation-work-verified-result/verification.md). Offline advice remains explicitly different from sending, buying or accepting invitations.

The existing normal preview/private env/wake-model cache in `/Users/tantalum/.codex/worktrees/personal-agent-20261031/FYP` was preserved, not upgraded by this merge. Its current provider configuration must be retained when a later rollout is requested; do not substitute the providers-off QA runtime. Check actual processes/in-flight calls before switching source. Keys, raw media, stores and models remain ignored. The test preview is cleaned up at closeout.

## One next step

The same conversation shows one verified offline result after the goal changes. Next, a later turn in that conversation can ask about the work and be shown this same verified result again, without a second executor run and without a provider call. Live accounts, payment, Pi, and a paid model comparison stay closed. Keep [personal-agent research](research/personal-agent-research-index.md) and the existing authority boundaries.
