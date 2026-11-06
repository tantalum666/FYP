# Group 2 current handoff

6 November 2026. Ordinary Alice text can admit an explicit goal change into an existing Work run, offline, including interruption and unknown-result recovery. [Contract](desk-companion/docs/conversation-work.md), [fixture](desk-companion/fixtures/conversation-work/changed-goal.json), [QA](output/qa/2026-11-06-conversation-work-changed-goal/verification.md). No new task store, queue, schema migration, or model approval tool. No paid call.

4 November baseline remains: **PR74–77 are merged into main through [PR85](https://github.com/tantalum666/FYP/pull/85), together with the reviewed Grok journeys.** Code mergeb663204 exactly matches reviewed affbad2d; candidate151f807 is the verified application tree. All four original PRs were independently read back merged. [Receipt](output/qa/2026-11-04-merge-74-77/publication.json), [QA/results](output/qa/2026-11-04-merge-74-77/verification.md). Pi is paused, experimental budgets closed, verification local only.

## Current software

Primary Web conversation, concise shared UI, mobile Alice, explicit local media controls, OpenAI realtime/local Alice wake, persistent application Work and the repaired offline mailbox/shopping/calendar flows now share one code baseline. Existing permissions, proposal decisions, task/job queues and validated backup contracts are retained. [Desktop](desk-companion/docs/desktop-conversation.md), [OpenAI/wake](desk-companion/docs/openai-alice-wake.md), [application Work](desk-companion/docs/application-work.md), [Grok review](output/qa/2026-11-04-grok-journey-review/verification.md).

## Verification and runtime

This slice: ruff on the touched Python, conversation-work 9 passed, integration acceptance 7 passed, and the text/goals/permissions/shopping/mailbox/calendar/agent-run regressions 97 passed. No new paid call. The 4 November full suite remains 1769 backend/319 frontend with primary-chat/393px phone checks; this slice did not rerun that suite or the UI. Offline advice remains explicitly different from sending, buying or accepting invitations.

The existing normal preview/private env/wake-model cache in `/Users/tantalum/.codex/worktrees/personal-agent-20261031/FYP` was preserved, not upgraded by this merge. Its current provider configuration must be retained when a later rollout is requested; do not substitute the providers-off QA runtime. Check actual processes/in-flight calls before switching source. Keys, raw media, stores and models remain ignored. The test preview is cleaned up at closeout.

## One next step

Continue ordinary Alice conversation-to-Work on this baseline with offline unseen variants: phrases and source layouts outside the changed-goal fixture, then a voice snapshot that steers an existing run. Live source accounts, payment and Pi remain separately scoped. Keep [personal-agent research](research/personal-agent-research-index.md) and the existing authority boundaries.
