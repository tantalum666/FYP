# Group 2 Current Handoff

28 October2026, Asia/Hong_Kong. **Current implementation is in the managed integration checkout below.** This milestone integrates the previously local Alice/Omni/web/phone source onto archived main, then fixes maintainability, selected-task context and interaction recovery. Publication readback is the current finalization step; see QA for its eventual result.

## Current state

- Checkout:`/Users/tantalum/.codex/worktrees/software-ai-maintenance/FYP`; branch`codex/software-ai-maintenance-20261028`, based on main46ac167. The old dirty`grok-review-merge-20261015/FYP`checkout and private backups are preserved; do not reset them or copy their old code over this branch.
- [Maintenance contract](desk-companion/docs/software-maintenance.md): phone home/plan/management/data/environment split; web/phone share login, session recovery and event editing. Phone root920→363lines; this is responsibility separation, not a blanket code-quality metric.
- Selected task ID passes the real voice-start route, is server-resolved and binds owner/task replay. Cross-task replay and invalid/hidden/unauthorized selections fail before a provider connection. Changes still require owner review. Ten new backend tests use scripted providers; no new live-model claim.
- [QA](output/qa/2026-10-28-maintainable-ai/verification.md):303backend/65frontend, Ruff, types/build; actual browser guards, late-response and session-expiry recovery; independent persistence readback. New native build/launch and [screenshot](output/qa/2026-10-28-maintainable-ai/iphone-simulator-final.jpg) verified. Native touch/keyboard, real devices and energy still unverified.
- Retains main's Vite8.3.5. New CI checks tests/lint/build with models/executors off; CI completion must be read back, not assumed from workflow creation.

## Review environment

Web5190/API8831 are served from this checkout by dev exec70382. The isolated fictional runtime remains at`/Users/tantalum/.codex/worktrees/grok-review-merge-20261015/FYP/desk-companion/.runtime/web-ui-implementation-20261027`; preview/native flags on, providersnone, background AI and executors off. Local preview renews expired sessions without unmounting drafts and never automatically retries writes. Credentials/databases remain ignored.

iPhone17Pro/iOS26.5 UDID`F57B6381-6448-434C-AE61-A2663F3458A7`, bundle`dev.group2.deskcompanion`, built from this checkout. Real mirror3200 remains exec11290. Do not restart a static8853 concept as the app. Do not stop another simulator's helper.

Qwen remains a tested baseline with other candidates open. Pi stays paused; old paid budgets are closed. No new microphone/camera/user-screen sharing, hardware, school-report change/submission, or external contact occurred.

## One next step

Finish this milestone's exact GitHub head/PR/CI readback, then carry the native Plan→New→Save→Back and software-keyboard/draft-recovery validation as the next acceptance gate. Keep model quality/real-device evidence separate from scripted protocol and browser results.
