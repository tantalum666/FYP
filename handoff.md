# Group 2 Current Handoff

30 October 2026, Asia/Hong_Kong. Current checkpoint: **bounded real application execution, scripted complex-task recovery and shared web/phone controls**. Workspace `/Users/tantalum/.codex/worktrees/grok-reviewed-fixes/FYP`, branch `codex/application-execution-20261030`, based on PR67 head `6bc8f19d6476577f5178e0c74374152646591b4a`. Publication readback is recorded with this milestone; no implicit merge or Pi deployment.

## Completed and verified

- Generic typed workbook/document/PDF/text jobs now use the existing JobService, PermissionService and TaskService. Scoped source reads use actual Chromium; Calc formulas and Writer editing/export use actual UNO. Owned staging, source/dependency/task versions, immutable history, independent reopen and atomic publication are separate modules. [Contract/setup](desk-companion/docs/application-execution.md).
- The fictional complex case actually ran: initial Aster HKD 809.60 → revised colour constraints infeasible → scripted black-and-white clarification → Delta HKD 669.24, including ten extra copies. Five artifacts, seven unfinished source tasks/14.5 hours, five calendar events and the same second rehearsal ID moved to Thursday. [Artifacts and actual QA](output/qa/2026-10-30-application-execution/verification.md).
- Saved-but-unacknowledged workbook survived process/application restart and read-only reconciliation with identical SHA/mtime. Another clean container restart verified all five files. Queued Full-access work was blocked after withdrawal. Failed Calc/PDF/startup attempts and fixes remain in the evidence.
- Shared cards show exact patches, Allow once/Not now, real results and downloads. Task pages project durable stages and last verified files. Actual web creation, phone update, 393px readback/unsent-draft retention and declined change passed. Actual Calc result changed 285 → 380; decline left the latter unchanged. Alice home remains.
- Local full suite: 524 backend / 89 frontend; final focused checks, Ruff/format, TypeScript/Vite and visual/readback evidence in QA. PDF pages were rendered and inspected. No CI.

## Current local environment

Owned Colima profile `fyp-apps`, Docker context `colima-fyp-apps`, container `desk-applications`, internal network `desk-apps-internal`. Only `.runtime/app-desktop` is VM-mounted; its `inputs` and generic helper `support` are read-only in the container, `workspace` writable. No key, core database, repository, oracle or Docker socket is mounted. Chromium sandbox is retained. [Prepare helper](desk-companion/scripts/application_desktop/prepare.py) pins/verifies the upstream seccomp content; the run recipe explains DNS and display-lock repairs.

Core runtime `.runtime/application-main-01` is outside the desktop mount. Preview API `127.0.0.1:8854`, Vite `127.0.0.1:5191`, phone `?surface=phone`, providers `none`, final permission Ask. Main case task `5909669a950c47c58f7477ea0da8a025`; separate UI task `d8f5a1ea81024d08aab42ce7ff2e15f2`. Desktop viewer uses an owned loopback SSH forward at `127.0.0.1:5530`; cancel only that forward, never Colima's shared control master. Recheck listener ownership before reuse. All input/data here is fictional.

## Boundaries to preserve

The application acceptance driver is scripted test infrastructure, not a model planner or tool. **No autonomous Qwen/Realtime/Live complex-task pass and no new model call occurred.** Normal HTTP still stops after one effect-producing tool; durable stages do not implement continuation. Production OpenAI provider wiring, human speech/AEC and unseen task variants remain open.

The prior OpenAI USD5 round is closed (USD0.3035168833 conservative estimate); old Qwen budgets are closed. The previously authorized key remains only in ignored 0600 `desk-companion/.env.local`; never print or publish it. No new paid round follows automatically from this handoff. Native iOS touch/keyboard remains open and was not rebuilt/retested in this application round. Pi/Luwu paused; school originals unchanged.

PR64 memory, PR65 permissions, PR66 OpenAI evaluation and PR67 fixtures remain the prior unmerged stack. Grok20–59/#60 were already integrated via PR61. Do not repeat that merge or describe a pushed branch as deployed.

## One next step

Implement an offline-tested, resumable model-driven task turn over these shared typed tools/stages, including a held-out source/layout case and interruption. Reuse current job/permission/receipt boundaries rather than adding a planner-specific queue or one-shot fixture solver. Only after that, wire the normal OpenAI conversation paths and scope a small newly authorized paid voice comparison.
