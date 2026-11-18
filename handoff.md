# Group 2 · Current handoff

18 November 2026, Hong Kong. Continue from `/Users/tantalum/.codex/worktrees/proactive-agent-merge-20261117/FYP`, branch `codex/official-text-sessions-20261118`. [PR 132](https://github.com/tantalum666/FYP/pull/132) is based on the deployment handoff in PR 131. [Product](product.md) · [decisions](decision-log.md).

## Source and acceptance

Ordinary OpenAI chat uses official Sessions and Functions. The normal composer, local tools, owner review cards and receipts remain the user-facing path. Compatible follow-ups reuse the same session. File attachments keep the existing Responses path. An uncertain request can recover a verified result or a local review, with no automatic repeat of a business action. [Contract](desk-companion/docs/official-text-sessions.md) · [protocol and browser QA](output/qa/2026-11-18-official-text-sessions/verification.md).

Quiet-time findings now share one notice for up to three current items. One acknowledgment leaves the other findings available. This reuses the existing findings, notifier, preferences and delivery records. [Claude article and implementation choices](research/2026-11-18-always-on-personal-agent.md).

## Installed baseline

Normal Mac Web, the native iPhone 17 Pro Simulator and Pi last deployed `c607759e`. A3 version 9, the original stores and independent Mac/Pi Google grants were verified there. Background inference was off. The new source used isolated application stores for both scripted and separately authorized real-provider acceptance. The previous live test budgets remain closed. The owner deferred the physical iPhone, and Pi power work remains paused. [Deployment PR](https://github.com/tantalum666/FYP/pull/131) · [readback](output/qa/2026-11-18-three-end-rollout/verification.md).

## Real text acceptance

The dedicated FYP key completed one GPT‑6.2 Sol session using the owner's locally controlled US$0.25 allowance. Alice called `owner_clock` once, returned `Asia/Hong_Kong` UTC+08:00 and answered the Singapore follow-up with a zero-hour difference. The provider reported 30,476 total tokens. DELETE succeeded and subsequent GETs returned 404. The prior GPT‑6.1 Sol request with `spend_control` received HTTP 400 before any session was created. The separate batch is closed. [Live readback](output/qa/2026-11-18-live-text-clock/verification.md).

## Next release decision

Choose the production spending policy and isolate the text-model selection from the managed browser's existing 6.1-only eligibility before promoting 6.2 as the normal text default.
