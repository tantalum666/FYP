# Group 2 · Harder application-task preparation

Started29October and completed30October2026, Asia/Hong_Kong. The owner asked to make the proposed real application task substantially harder. The current deliverable is a prepared acceptance task, source pack and independent reference checks. **No voice candidate or desktop application has executed/passed this challenge.**

## Delivered

- [Acceptance specification](../../../planning/2026-10-30/complex-application-acceptance.md): browser/source review → Calc budget/formulas → Writer/PDF → calendar/task state → interruption/recovery, with mid-task constraint changes and a100-point rubric plus hard failures.
- [Fixture package](../../../desk-companion/evals/app_workflow_v1/README.md):11 task rows/9 distinct tasks, meeting-note update, three members' availability and existing events, frozen FX rates, four fictional suppliers/five quote revisions, actual localHTML pages, controller corrections and source hashes.
- [Offline reference](../../../desk-companion/scripts/app_workflow_reference.py) computes expected facts only. [Reference output](reference-results.json) explicitly says applications were not run and candidate submission was not evaluated. The evaluated model must not receive this reference/controller/repository scope.
- [Six consistency checks](fixture-tests.txt), [Ruff](lint.txt), [formatting](format.txt). No production/backend/frontend/provider source was changed, so the earlier504/89 counts are not relabeled as new full-suite runs.

## Independently checked fixture facts

| Stage | Financial result | Calendar result |
|---|---|---|
| Initial:25colour booklets,HKD1300 cap including10%reserve | Aster: delivered736.00 + reserve73.60 =809.60HKD; lowest feasible current quote | Tue3Nov16:15–17:00 andWed4Nov15:15–16:00 |
| Correction:40colour booklets,HKD1000 cap, noWednesday | No feasible quote. Cedar fits price but its current revision arrives too late; a clarification is required | Keep the Tuesday event; update the same second event toThu5Nov15:15–16:00 |
| Approved black-and-white substitution | Delta: minimum50copies,USD78 ×7.80 =608.40HKD +60.84reserve =669.24HKD | Same corrected pair; no duplicate events |

The newer task export and meeting note yield9 distinct tasks,7 still open and14.5 remaining hours. T02 is reopened, T04 is completed by a later update, and the olderT07 row does not count twice. A rate variation to7.90 changes the final winning supplier toBirch, verifying that the reference computes from data rather than returning a fixed answer. A missing currency rate fails closed.

Tests check arithmetic/eligibility, latest quote delivery, item-only discount, task identity/version reconciliation, calendar conflicts/correction, rate sensitivity and the boundary between fixture calculation and actual application success.

## Capability audit

Current JobInput supports only `save_note`, `verify_note`, `save_folder_file`, `verify_folder_file`, `linux_note_preview` and `verify_linux_file`. LinuxDesktopExecutor runs a fixed Mousepad→Chromium local-text workflow. It does not edit a spreadsheet or document, exportPDF, or plan arbitrary browser navigation. The existing HTTP model loop ends after one effect-producing tool. Existing task/job/permission/version/receipt services are useful foundations, but cannot be presented as an implemented solution for the new task.

The single next implementation slice is bounded browser/Calc/Writer operations and independent readback on the existing services, with persistent stage/recovery behavior. First exercise that application path offline. Subsequent real voice/model comparison and native playback acceptance remain separate gates.

## Boundaries and publication

No paid model calls, microphone/camera, applications, account actions, purchase/payment/email/school submission or Pi/Luwu execution occurred. The previous OpenAI round remains closed at its recordedUSD0.3035168833 estimate; Qwen budgets stay closed. All fixture prices, identities and schedules are invented. NoCI.

[Reading record](reading-record.json) distinguishes full contracts from relevant source/architecture sections. Product, current delivery gate, computer-job boundary, entry/handoff, decision log and work log are updated. Markdown/HTML links, JSON/CSV, hashes, private/material scope and staged secrets are checked before publication. The independent branch is `codex/complex-app-acceptance-20261030`, based on openPR66 head`4f96fa7f5d56271a758b8a9e9f66930c7f359c41`; publication is not merge, deployment or benchmark execution.
