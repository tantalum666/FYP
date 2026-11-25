# Group 2 · Current handoff

25 November 2026, Hong Kong. Public `main` remains `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d` (PR #157). [Product](product.md) · [decisions](decision-log.md) · [work history](work-log.md).

## This slice (#161)

Branch `cursor/suggestion-followup-status-e853` product tip `be5cfaf3d11f24c3d566ac17d8c9689002bcdfe6` (unchanged): proactive finding → Sources → Follow up on this → private task by id → revisitable status; stale evidence refused. [Verification](output/qa/2026-11-25-initiative-followup/verification.md).

## Four-way + live-owner cleanup closeout

UI port failures fixed on #158/`70accc16` and #159/`1f760a41`. Remaining `test_live_owner_page` `COMPUTER_CLEANUP_REQUIRED` was **not** Vite contention: old `_kill_chrome` kill-all fallback SIGKILLed the worker before cleanup; product blocker was correct; screen already returned `BROWSER_PAGE_LOST`. Chrome-only fix + regression on #158 tip **`0e9ea44a`**. Fresh local four-way tip **`0234fc1ebb`** (main→158→159→160→161): backend **3082 passed / 1 skipped / 0 failed**; frontend **442**; four Chrome UIs **4 passed** @1440+320. Prior trees `43b82c75` / `23d9f44a` preserved. No GitHub merge.

Per-PR heads: #158 `0e9ea44a` · #159 `1f760a41` · #160 `d8aad9fb` · #161 product `be5cfaf3` / notes tip after this commit · #162 `3079cddf` (FastClient active budget, from main).

## Running software (unchanged this slice)

Normal Mac Web and Simulator still run application `b759950c`. Defaults stay GPT-6.2 Sol / GPT-Live-1.1 / A3 v9.

## Not done

No GitHub merge, CI, deploy, Pi/hardware, live mailbox, paid model, or feature import across #158–#160 beyond the harness fixes above.

**Next step** — Parent rechecks remaining weekly included usage, then Codex review of open PRs #158–#161 and #162 (managed FastClient active budget). The Pi update from `92acac8e` to `b759950c` stays a separate device step.
