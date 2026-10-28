# Group 2 · Local validation only

28 October 2026. The owner reiterated: do not use CI; validate locally. This change removes `.github/workflows/desk-companion.yml` and makes that rule explicit in AGENTS, product, contribution guidance, current entry, README, maintenance contract and handoff. Historical CI annotations remain historical evidence, not a project gate or next task.

GitHub's Actions inventory endpoints returned403 for the local CLI credential. No token permissions or billing settings were changed. Removal of the workflow definition from the repository is the chosen implementation; this is not a claim that the account-wide Actions service was disabled.

Local verification for this configuration/document-only change:

- No workflow YAML remains in the current Git index.
- All281 application file hashes match the tested integration manifest.
- Application source, dependencies and test implementations are unchanged. The earlier450 backend/89 frontend pass is reused as dated evidence, not claimed as a new run.
- Changed Markdown link targets, Git whitespace and staged secret scan are checked before publication.

The owner's code-quality question is answered from the [completed Grok integration review](../2026-10-28-grok-review-merge/verification.md). That review distinguishes the original stack, its compatibility with #60, and the repaired merged result. The original combined candidate had15 failed/422 passed backend tests; after repairs the suite reached450 passes. The original Grok rehearsal had separately recorded3 failures. Neither result justifies describing the original code as ready to merge unchanged.

Its useful design includes a bounded agent loop, one shared tool policy and existing approval/job services. Its main weaknesses were cross-module invariants: global transcript retention, stale read-cache replay, owner checks at final apply/decision, imported-job/path validation, calendar-default insertion, and stream/identity lifecycle recovery. Those findings were repaired before the previous merge. No new security scan or live-provider test was performed in this turn.
