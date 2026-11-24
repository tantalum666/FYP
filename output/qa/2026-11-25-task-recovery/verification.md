# Group 2 · Interrupted task readback

25 November 2026. Branch `cursor/task-recovery-readback-f7ae`, from `origin/main` `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d`. The only open pull request before this work was #158, the local page handoff. That branch and pull request were not changed.

Status: implemented and locally verified. Not merged, not deployed, and not a live-account acceptance.

## Gap

The task page already listed linked file actions, but an unknown result and a write that never happened were not distinct, and the button said Continue even when continuing must not repeat the action. A paired display could also open a private task and read its steps, because the task routes only hid private rows when the privacy toggle or an away display was on.

## Behavior

- An unknown file says the safe next step is Check result, which only rereads the file.
- A cancelled, failed, or expired action says no new file was written.
- A review says it is waiting for approval and that opening the chat does not approve or send it.
- While a result is unknown or waiting, the button is Discuss this task and says it does not check, approve, or write again.
- A second task with the same title does not receive the file. A completed step stays completed.
- Repeating Check result does not change the file time.
- A paired display gets `PRIVATE_TASK_HIDDEN` for a private task and cannot post a progress note. A revoked display gets `AUTH_REQUIRED`. Hiding private context does the same for the owner.

No new dashboard or control was added. Check result stays on the existing file card.

## Checks

| Check | Result |
|---|---|
| `tests/test_task_job_journey.py` | Passed, including the new selected-task, paired, revoked, hide, and repeated-reconcile case. |
| `tests/test_task_recovery_ui.py` | Passed. Local Chrome at 1440×1000 and 320×740. The task card shows the unknown result and Discuss. Check result leaves the file time unchanged. The same-titled other task has no linked file. |
| Frontend `npm test` | 440 passed, 0 failed. |
| `npx tsc --noEmit` and `npm run build` | Passed. |
| Ruff on the edited Python files | Passed. |
| Full backend `pytest` | 3057 passed, 1 skipped, 0 failed, 996 seconds. Python 3.12. |

Two frontend source checks and nine backend assertions were already failing on `fc3b8d2`. They now call the current timeout, Today suggestion, fingerprint, ambiguous reprice phrase, unadmitted managed origin, Google caption, and forget-context behavior. No assertion was removed.

No paid model call, live account, CI workflow, provider change, or deployment was used.

## Screenshots

- `/opt/cursor/artifacts/task-recovery-desktop.png`
- `/opt/cursor/artifacts/task-recovery-narrow.png`
- `output/qa/2026-11-25-task-recovery/desktop-recovery.png`
- `output/qa/2026-11-25-task-recovery/narrow-recovery.png`

The Pi update from `92acac8e` to `b759950c` stays a separate device step.
