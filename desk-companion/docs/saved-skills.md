# Saved skills — 10 November 2026

Grok Bot completed this slice. It is one offline capability, not a merge of the open pull requests.

## Why this one

The open pull requests already cover conversation Work re-show and continue (#95, #96, #99), the folder-job clock (#98), browser takeover at a verification wall (#101), memory follow-ups and the morning check-in (#102, #103), and offline trip quotes plus re-approval (#104, #105). Codex #97 owns the shared Alice home, chat attachments, Gmail and Outlook drafts, and voice preferences.

What is still missing, and named in the research, is Grok’s reusable skill. The [research index](../../research/personal-agent-research-index.md) describes a verified flow saved as a skill. [Routines](routines.md) only run the code-owned reviews `day_briefing` and `task_review`. The October capability gap’s acceptance for this row is a versioned declarative skill whose inputs cannot add code, tools, or permissions. Mail, shopping, and travel already have offline journeys on main or in those pull requests. This slice does not continue them.

The one-effect assistant loop is a separate gap. It lives in `text_ai.py`, which #95 and #97 already edit, so it is not this change.

## What the owner can do

On Tasks, open **Saved skills**. Write a title, the steps, and the input names. The skill is saved only when **I checked this by hand** is checked. That sends `passed: true`. Leaving the box unchecked sends nothing. A request that omits `passed`, or sends `passed: false`, does not become a skill.

Later the owner fills those names and chooses **Prepare**. The run stays `pending`. **Approve** writes one local result for that exact fill. **Stop this one** closes it with no result. The result’s basis is `owner_approved_local_check`. `system_verified` and `external_receipt` are false. Steps are stored and shown as text. An instruction inside a step does not complete a task, send mail, or create a job.

A blank note is omitted. A note that is present but empty is rejected and does not create a run. An approval without the prepared `input_hash` does not approve. The same operation id and body returns the same row. A different body with that id conflicts. If the decision is interrupted before commit, the run stays pending and the same id can commit once.

Only a visible owner session can read or decide. A paired display cannot. Hiding private context returns `PRIVATE_CONTEXT_HIDDEN` and does not include the title.

## What this slice does not do

- It does not call a model, open a mailbox, a shop, a calendar, or a payment account.
- It does not change `Runtime.tick`. Quiet release stays mailbox, shopping, offline calendar on this branch. After #102–#105 it must still be mailbox, shopping, trip quotes, offline calendar, then `memory_followups.tick()`.
- It does not add `saved_skill_bundle`. `mailbox_bundle`, `shopping_bundle`, and `offline_calendar_bundle` stay the portable keys. A backup does not restore these skills.
- It does not schedule the skill. A later slice can point an existing routine at one saved skill without a second scheduler.
- It does not edit the living handoff, work log, decision log, product contract, or research index.

## Where it merges

Branch `cursor/saved-skills-d761` is based on current `main`. It can merge before or after #95–#105. It does not need to be inside that stack.

Touched shared files, each with a small addition away from the other slices:

- `desk-companion/backend/desk/runtime.py` — `self.saved_skills = SavedSkillService(self)` immediately after `personal_context`. No new tick call.
- `desk-companion/backend/desk/app.py` — `saved_skill_routes` immediately after `digest_routes`.
- `desk-companion/frontend/src/workspace/TaskPanel.tsx` — `<SavedSkillsPanel>` under the task list, after `WorkToolsEntry`.

#97 also edits `app.py` and `runtime.py`, in other regions (weather, outbound mail, app connections, Microsoft apps). #102 inserts memory follow-ups beside `memory_routes` and before voice. #104 inserts trip routes after `offline_calendar_routes` and `self.trips` after shopping. Those lines are not the ones this slice edits. After merging, confirm the tick block and the three bundle keys are still intact.

New files: `backend/desk/saved_skills.py`, `frontend/src/workspace/SavedSkillsPanel.tsx`, `SavedSkillRun.tsx`, `savedSkillState.ts`, `saved-skills.css`, `tests/test_saved_skills.py`, `frontend/tests/saved-skills.test.ts`.

## Codex handoff

Keep the service’s own session and private-context checks. Do not treat an omitted `passed` or an omitted note as a value. Do not replay a side effect after a lost response; the operation row and the run row commit together, and a raised `_before_commit` rolls both back. Do not point a routine, a model tool, or a backup bundle at this table unless that is a separate reviewed slice. The UI copy should keep saying the result is saved on this desk after approval.

## Local verification on this branch

Base `855e60ee`. Backend **2042 passed, 2 failed** (the two failures already on this main: `test_restart_runs_only_the_approved_folder_job` and `test_public_unicast[::ffff:93.184.216.34]`). Frontend **332 passed, 0 failed**. New tests: 8 backend, 2 frontend. Chrome drove the Tasks page through an unchecked save, a checked save, prepare, and approve. Detail is in [the QA note](../../output/qa/2026-11-10-saved-skills/verification.md).
