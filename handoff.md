# Group 2 · Current handoff

25 November 2026, Hong Kong. Public `main` remains `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d` (PR #157). [Product](product.md) · [decisions](decision-log.md) · [work history](work-log.md).

## This slice (#161)

Branch `cursor/suggestion-followup-status-e853` product tip `be5cfaf3d11f24c3d566ac17d8c9689002bcdfe6` (unchanged this closeout): proactive finding → Sources → Follow up on this → private task by id → revisitable status; stale evidence refused. [Verification](output/qa/2026-11-25-initiative-followup/verification.md).

## Four-way UI failure closeout

Named failures from combined tree `43b82c75`: owner-page `API did not start` (8831 EADDRINUSE) and task-recovery `Leave this one alone` timeout (foreign Vite / shared ports). Root cause: leaky UI harness (shared 5190/8831, no ownership check, Vite without process group). Fixed on source PRs #158 `70accc16` and #159 `1f760a41`. Fresh local four-way tip `23d9f44a`: original two UI nodeids green; four browser UIs 4 passed; full backend **3080 passed / 1 skipped / 1 failed** (`test_live_owner_page` cleanup race — focused alone passed). Full combined backend **not** accepted green. No GitHub merge.

## Running software (unchanged this slice)

Normal Mac Web and Simulator still run application `b759950c`. Defaults stay GPT-6.2 Sol / GPT-Live-1.1 / A3 v9.

## Not done

No GitHub merge, CI, deploy, Pi/hardware, live mailbox, paid model, or feature import across #158–#160 beyond the harness isolation above.

**Next step** — Parent rechecks remaining weekly included usage, then Codex review of open PRs #158–#161 (or a bounded fix for the live-owner cleanup race if authorized). The Pi update from `92acac8e` to `b759950c` stays a separate device step.
