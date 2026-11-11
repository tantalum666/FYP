# Saved skills — 10 November 2026

Grok Bot completed this slice. It adds a local schedule to the owner-checked skill from PR #108. It is one offline capability, not a merge of the other open pull requests.

## Why this one

PR #108 saves a checklist the owner has checked, then waits for approval of an exact fill. The [research index](../../research/personal-agent-research-index.md) says Grok keeps a verified flow as a skill and starts it from a routine when the time arrives. [Routines](routines.md) still run only the code-owned reviews `day_briefing` and `task_review`, and those reviews publish a result immediately.

The valuable next step is the time trigger, on the clock that already exists. Each occurrence prepares the saved fill and still waits. Quiet hours, proactive off, and a missed time do not prepare a run later. Editing a skill into a new version is the following slice: a skill still has one version, so there is no old run to invalidate yet.

## What the owner can do

On Tasks, open **Saved skills**. Write a title, the steps, and the input names. The skill is saved only when **I checked this by hand** is checked. That sends `passed: true`. Leaving the box unchecked sends nothing. A request that omits `passed`, or sends `passed: false`, does not become a skill.

Later the owner fills those names and chooses **Prepare**. The run stays `pending`. **Approve** writes one local result for that exact fill. **Stop this one** closes it with no result. The result’s basis is `owner_approved_local_check`. `system_verified` and `external_receipt` are false. Steps are stored and shown as text. An instruction inside a step does not complete a task, send mail, or create a job.

The same fill can be scheduled. **Schedule** stores the frequency (`once`, `daily`, or `weekly`), the first local minute, the timezone, and the inputs. A blank note is omitted. A note that is present but empty is rejected and does not create a schedule. The schedule is immutable: pause, resume, or cancel it, or create another. Pause and cancel leave the stored fill in place.

The existing routine clock reaches the schedule from the end of `RoutineService.tick`. It does not add a second scheduler and it does not change `Runtime.tick`. An occurrence prepares one pending run only while the local clock is inside two minutes of that occurrence, proactive suggestions are not off, and quiet hours are not in effect. Quiet hours follow the desk timezone. The prepared run uses `origin: schedule` and still waits for **Approve** or **Stop this one**.

A later tick does not prepare that occurrence again. A time more than two minutes late is missed and is not prepared when the desk is next awake. Quiet hours and proactive off consume the occurrence the same way. Pause skips the times that pass while paused. Resume of a one-off whose time has already passed does not prepare it. Cancel stops later occurrences. A run that was already prepared stays pending; pause and cancel do not decide it.

A schedule operation uses an operation id. The same id and body returns the same schedule. A different body with that id conflicts. If the save is interrupted before commit, nothing is stored and the same id can commit once. There are at most 20 schedules on the desk, including finished ones.

Only a visible owner session can read or decide. A paired display cannot. Another login cannot. Hiding private context returns `PRIVATE_CONTEXT_HIDDEN` and does not include the title or the fill.

## What this slice does not do

- It does not call a model, open a mailbox, a shop, a calendar account, or a payment account.
- It does not change `Runtime.tick`. On this branch the quiet release stays mailbox, shopping, then offline calendar. After the #107 order it must still be mailbox, shopping, trip quotes, offline calendar, then `memory_followups.tick()`. The skill schedule stays inside `routines.tick()`, which already follows that block.
- It does not add `saved_skill_bundle`. `mailbox_bundle`, `shopping_bundle`, and `offline_calendar_bundle` stay the portable keys. A backup does not restore these skills or schedules.
- It does not edit a skill or change `saved_skills.version`. A later slice can refuse approval when the run’s skill version is no longer the current one.
- It does not put the schedule in the routine delivery inbox, and it does not catch up a missed day the way `day_briefing` does.
- It does not send mail, buy, book, or complete a task.

## Where it merges

Branch `cursor/skill-schedule-be49` is based on `cursor/saved-skills-d761`. Merge #108 first, then this branch.

Touched shared files:

- `desk-companion/backend/desk/routines.py` — `saved_skills.release_due(conn)` at the end of `tick`, in the same write transaction, after the briefing loop. No new `Runtime.tick` call.
- `desk-companion/frontend/src/workspace/SavedSkillsPanel.tsx` — the schedule controls stay inside the existing saved-skill card.

`runtime.py` is not edited. #97, #102, and #104 still touch other regions of `app.py` and `runtime.py`. This slice does not.

New behavior lives in `backend/desk/saved_skills.py` and the saved-skill tests. The schedule tables are `saved_skill_schedules` and `saved_skill_occurrences`.

## Codex handoff

Keep the service’s own session and private-context checks. Do not treat an omitted `passed` or an omitted note as a value. Do not replay a side effect after a lost response; the operation row and the schedule or run row commit together, and a raised `_before_commit` rolls both back.

Keep the two-minute window. Do not prepare a missed, quiet, or proactive-off occurrence later. Do not approve from the clock. Pause and cancel must not clear stored inputs or decide a run that is already pending. Do not add these rows to a backup bundle or to the `day_briefing` result shape. The UI copy should keep saying the result is saved on this desk after approval.

The next slice is an edit that stores a new skill version and refuses approval of a run prepared against the previous version.

## Local verification on this branch

Base is `cursor/saved-skills-d761` at `0277903`. Backend **2049 passed, 2 failed**. The failures are the two already known on this line: `test_restart_runs_only_the_approved_folder_job` and `test_public_unicast[::ffff:93.184.216.34]`. Frontend **332 passed, 0 failed**. `npm run build` succeeded. Chrome on the Tasks page left the checklist unchecked, then saved it, scheduled the fill, and after the occurrence showed one pending run. Approve replaced that with “Saved on this desk after your approval.” The same result was visible at 390×844. Detail is in [the QA note](../../output/qa/2026-11-10-saved-skill-schedule/verification.md).
