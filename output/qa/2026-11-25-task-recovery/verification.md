# Group 2 · Interrupted task readback

25 November 2026. Branch `cursor/task-recovery-readback-f7ae`, from `origin/main` `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d`. The only open pull request before this work was #158, the local page handoff. That branch and pull request were not changed.

Status: the independent branch is implemented and locally verified at `59387638`. Not merged, not deployed, and not a live-account acceptance. The combined tree is not fully green.

## Gap

The task page already listed linked file actions, but an unknown result and a write that never happened were not distinct, and the button said Continue even when continuing must not repeat the action. A paired display could also open a private task and read its steps, because the task routes only hid private rows when the privacy toggle or an away display was on.

## Behavior

- An unknown file says the safe next step is Check result, which only rereads the file.
- A cancelled note says no file was written only for `USER_CANCELLED` or `JOB_CANCELLED_BEFORE_DISPATCH`. Cancellation alone, and a failed or expired action, say the outcome was not checked and that Check result only rereads.
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
| Independent backend `pytest` | `PYTHONPATH=backend /tmp/desk-venv/bin/python -m pytest -q --tb=line` on product tree `64975163`. 3057 passed, 1 skipped, 0 failed, 1027.90 seconds. The next commit `59387638` changes only `computer-jobs.test.ts`. |
| Independent frontend | `npm test`, `npx tsc --noEmit`, `npm run build` on the tree committed as `59387638`. 440 passed, 0 failed. Typecheck and build passed. |
| Independent lint | `git diff --check` passed. `ruff check` on the edited Python files passed. |
| Combined tree `8f580c83` | Parents `efc32b09` (#158 `32066b8b` merged onto `fc3b8d2`) and `64975163`, plus the cancellation assertion. `npm test` 440 passed. `tsc` and `build` passed. `ruff check desk-companion/backend/desk desk-companion/tests` passed. `git diff --check` passed. Backend `pytest`: 3060 passed, 1 failed, 1 skipped, 1028.03 seconds. Failure: `tests/test_owner_page_ui.py::test_hold_card_on_desktop_and_narrow_screen`. Takeover returned 200, then `Type on this page` was not visible. The locator matches the `owner_takeover` card that is already on screen before the held controls render. Not rerun. |

The six conflicts were `decision-log.md`, `handoff.md`, `work-log.md` (both sections kept; the Pi sentence stays the device next step and is separate from both slices), `browser-workflow.test.ts` (kept `requestDeadline` checks and the request-timer checks), `moments.test.ts` (kept the fuller Today assertions, which include the shorter set), and `test_chat_attachments.py` (kept one stability check of the same fingerprint). `jobTypes.ts` merged with the final cancellation wording intact.

Two frontend source checks and nine backend assertions were already failing on `fc3b8d2`. They now call the current timeout, Today suggestion, fingerprint, ambiguous reprice phrase, unadmitted managed origin, Google caption, and forget-context behavior. No assertion was removed.

No paid model call, live account, CI workflow, provider change, or deployment was used.

## Screenshots

- `/opt/cursor/artifacts/task-recovery-desktop.png`
- `/opt/cursor/artifacts/task-recovery-narrow.png`
- `output/qa/2026-11-25-task-recovery/desktop-recovery.png`
- `output/qa/2026-11-25-task-recovery/narrow-recovery.png`

The Pi update from `92acac8e` to `b759950c` stays a separate device step.
