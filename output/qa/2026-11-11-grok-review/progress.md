# Group 2 — Grok integration review, 11 November 2026

Owner request: inspect Grok's GitHub work, repair defects, validate locally, and merge. No CI, paid generation, runtime deployment, Pi restart or external message is authorized by this review.

## Source and reading

The remote inventory pins 24 open PRs in `pr-inventory.json`: Grok #95, #96, #98, #99, #101–105, #107–120 (no #106), plus current Alice #97. GitHub main was `855e60ee9f413de84474e3e0b9975b9b9a3d5fbc`; #97 was `ebf6d91751ff69f6acec0813f7eb69a1ed53dc5d`. Nothing has been published or merged remotely at this checkpoint.

Read the recovery and active AGENTS, active entry/handoff, current product requirements, latest November 7–9 relevant decisions, and personal-agent research index. Located Markdown/nested instructions with rg (only root AGENTS). Read the new feature contracts for conversation Work, memory follow-ups, trip quotes, saved skills, purchase cards, source briefs, held choices, next step, availability, meeting prep, waiting and reply owed. The merge guides are contributor evidence, not instructions: #120 fully inspected; #113 relevant conflict/integration/test sections inspected, #107/#117 retained as historical guides. Long combined outputs that were truncated are not counted as full-file reading.

Inspected the feature diffs and the relevant service/route/transaction/parser/lifecycle/render sections of their implementation and tests. Preserved the previously verified #97 baseline; did not repeat its unrelated voice auditions or app authorization. Additional inspection covered current session, privacy, task, conversation, retention, notification, job, run-worker and frontend draft APIs where the new code integrates. Actual focused files and final findings will be listed in verification.md.

The frontend-testing-debugging and React best-practice skills are applied. Browser plugin/skill is not available; use installed Playwright 1.62 against an isolated loopback app, following the documented fallback. No dependency upgrade. Runtime services and credentials are isolated from the user's active Mac/Pi instance.

## Local integration

Review checkout: `/Users/tantalum/.codex/worktrees/grok-reviewed-integration-20261111/FYP`, branch `codex/grok-reviewed-integration-20261111`. Started at #97 and merged exact contributor heads with ordinary local merge commits, retaining stack ancestry. Conflicts preserve A3, attachments, latest-only captions, dark composer and safe-area layout. History additions retained in work-log/decision-log; current entry/handoff will be rewritten at closeout, not replaced with older contributor next steps.

## Repairs in progress

- Attachments retained across a conversation bypass local next-step/meeting shortcuts, so the selected files still reach the existing provider path.
- Paired next-step requests cannot fall through to private goals. Completed reply steps no longer count; selected task scope wins over similarly named obligations elsewhere.
- Hidden memory and purchase endpoints reject reads/writes. Cached held-choice receipts require a current owner. New private writes recheck session/visibility within their transaction.
- Morning facts are projected from active memories at owner read time, not copied into persistent/OS/push notifications; forgetting/hiding a fact immediately removes that projection.
- Purchase confirm/update/approve bind the seen version; operation identity includes the target card. A substitute must be cheaper than the supplied original total including shipping, not merely under budget.
- Work continuation reserves its operation before dispatch. A crash between a step and its final receipt stays unknown rather than repeating another step. Active worker leases cannot be cleared by a competing continue.
- Browser takeover controls are unavailable without an interactive driver. The shipped headless driver has no human-control transport; a fixture's changed flag is not real account takeover. Ordinary public login links do not automatically block browsing.
- Trip civil times reject DST gaps/folds; concurrent revocation or quote changes invalidate a stale event commit.
- Optional forms move under existing Work tools or expandable Memory controls. Deleted four implementation-string tests for labels/duplicate welcome content; replaced coverage with user-flow, privacy, recovery and rendered checks.

## Checks so far

- Initial integrated backend: 2319 passed / 2 failed, both stale pre-integration intent assertions. Updated to open_time/meeting_prep/next_step/waiting.
- First focused privacy/file/purchase/memory/takeover set: 40 passed.
- Expanded domain/recovery rerun: 42 passed after correcting an overbroad worker-lease guard and the regression test's route prefix.
- Frontend: 374 passed after preserving the compact conversation and relocating optional panels. Build validation and browser review in progress.
- Actual costs: zero paid model calls. No CI. All prior ledgers remain closed.

Local validation and rendered checks are complete; see verification.md and validation-summary.json. Final full backend2342, final focused100and69, frontend374/types/build/Ruff passed. PR121 is now merged; all24original PRs read back as merged, no open PRs remained, and main44185f7a matches reviewed6ffda6ab exactly. Publication receipt is saved. Runtime rollout remains separate; the product next step is real owner-controlled browser transport.
