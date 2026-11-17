# Group 2 · Current handoff

18 November 2026, Hong Kong. Resume in `/Users/tantalum/.codex/worktrees/proactive-agent-merge-20261117/FYP`. The deployment record is on `codex/three-end-rollout-20261118`. Follow [AGENTS](AGENTS.md) and the current [product contract](product.md).

## Running release

Mac Web on port 8831, the native iPhone 17 Pro Simulator on iOS 26.5 and the Raspberry Pi kiosk run `c607759e`. GitHub confirms PRs 124–128, the integration and the saved handoff are merged. The deployed runtime paths match tested candidate `42bc01ec`. [Integration PR](https://github.com/tantalum666/FYP/pull/129) · [handoff PR](https://github.com/tantalum666/FYP/pull/130) · [GitHub receipt](output/qa/2026-11-18-three-end-rollout/github.json).

Both original databases passed upgrade rehearsal, private backup verification and live integrity checks. Mac has 128 application tables and Pi has 127. Each retained its own original records, keys, A3 settings and cached sample at version 9. The native app cold-starts against the normal Mac service and its own bridge confirmed the A3 selection, owner session and grant versions. The Pi launches the new release and its actual display shows Alice connected. [Deployment report](output/qa/2026-11-18-three-end-rollout/verification.md) · [machine-readable readback](output/qa/2026-11-18-three-end-rollout/release-readback.json).

Mac and Pi independently verified Gmail and Google Calendar with provider reads. Microsoft registration/consent remains outstanding. The owner deferred the physical iPhone. The Pi retains its original CPU ceiling and RTC setup. Pi power diagnosis remains paused.

## AI and budget

Official Responses handles changed-source research, and multi-step browser jobs use the official managed executor. Background model research is disabled on both installed servers. The prior US$5 test batch and all four hosted sessions are closed. Existing full-suite and live results are in [integration QA](output/qa/2026-11-17-proactive-agent-merge/verification.md).

## Next software task

Move the ordinary text entry point from the existing compatibility loop onto official OpenAI sessions/functions. Reuse the current business tools, authority checks and conversation recovery, starting with the [capability map](desk-companion/docs/personal-agent-status.md).
