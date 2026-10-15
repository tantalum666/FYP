# Codex merge handoff for PRs #6–#14

Date: 14 October 2026. Audience: the coding agent that merges. Do not merge from this file until the owner has asked you to merge. The review on 14 October marked these PRs ready. Nothing in this stack was merged by the review.

## Do not merge

- **PR #4** `codex/full-body-3d-avatar` — different stack (A1 / VRM art).
- **PR #5** `codex/personal-agent-kernel-20261012` — different stack, based on #4. Do not rebase #7–#14 onto it. Do not port this stack into it.
- Do not open a hosted model account, create an API key, or start a provider trial. There is no spend cap.
- Do not add unrestricted GUI, browser, inbox, or general app control.

## What remains after this stack is on main

- Provider comparison still waits for an owner spend cap. Leave `DESK_TEXT_PROVIDER` and `DESK_VOICE_PROVIDER` at `none`.
- Unrestricted app control is still not authorized. A later bounded action, if the owner asks, registers on `JobService._bindings` in the existing job contract (approve the full text, independent read-back, cancel). Do not start a second job queue.
- School submission, Pi, real posture labels, RIG, and the cleaner module stay undone.

## Stack

| PR | Head branch | Base before merge | What it does |
|---|---|---|---|
| #6 | `cursor/tooling-review-docs-8674` | `main` | Muse/Dot teardown docs. Parallel to the code stack. |
| #7 | `cursor/owner-memory-agent-8674` | `main` | Owner-reviewed memory. Drafts do not write. Deleted facts leave the model context. |
| #8 | `cursor/folder-job-action-8674` | #7 | One owner-named folder on the existing note-job contract. |
| #9 | `cursor/persona-file-8674` | #8 | One owner-editable persona for text and voice. Tool rules stay in code. |
| #10 | `cursor/quiet-followup-8674` | #9 | Turning a task’s follow-up off skips queued text advice. The task stays. |
| #11 | `cursor/quiet-schedule-8674` | #10 | Quiet hours defer new follow-ups. At most 3 new reminders per scheduler pass. |
| #12 | `cursor/job-recovery-ux-8674` | #11 | Job cards name read-back and folder-binding failures and the next step. |
| #13 | `cursor/text-adapters-8674` | #12 | Qwen and Gemini text calls go through one adapter table. Job actions share `_bindings`. |
| #14 | `cursor/quiet-preference-8674` | #13 | Quiet-hour holds follow the saved preference across restart and edits. This file lives here. |

#7 through #14 are one stack. Each branch contains the commits of the PRs under it. #6 does not.

## Merge order

Use a **merge commit**. Do not squash. Do not use “Rebase and merge”. Squash or rebase-merge changes SHAs and makes the next stacked PR replay commits that are already on `main`.

1. Merge **#7** into `main`.
2. Retarget **#8** onto `main`, then merge it. Repeat for **#9, #10, #11, #12, #13, #14**.
3. After **#7** is on `main`, rebase **#6** onto `main` and merge it. It can happen any time after #7 and before or after #14. Do it after #7 so the four living docs are not the pre-memory copies.

Commands, from a clean checkout:

```sh
git fetch origin
gh pr merge 7 --merge --delete-branch=false

# Repeat this block for 8, then 9, 10, 11, 12, 13, 14.
gh pr edit 8 --base main
gh pr diff 8 --name-only
gh pr merge 8 --merge --delete-branch=false
```

After each retarget, the diff must be only that PR’s own files, not the whole stack again. If the diff still contains earlier PRs’ commits, stop and do not merge.

#6, only after #7 is on `main`:

```sh
git fetch origin
git switch cursor/tooling-review-docs-8674
git rebase origin/main
```

Conflicts belong only in `handoff.md`, `product.md`, `decision-log.md`, and `work-log.md`. Keep `main` for those four. Keep every file under `docs/tooling-and-review/`.

```sh
git checkout origin/main -- handoff.md product.md decision-log.md work-log.md
git add handoff.md product.md decision-log.md work-log.md docs/tooling-and-review
git rebase --continue
git push --force-with-lease origin cursor/tooling-review-docs-8674
gh pr merge 6 --merge --delete-branch=false
```

Force-push only that docs branch. Never force-push `main`. Do not rebase #7–#14 unless a retarget shows duplicate commits.

## Verify

On the tip (after #14, or on `cursor/quiet-preference-8674` before merging) the last local run was:

- `cd desk-companion && uv run --no-sync pytest -q` — 175 passed
- `uv run --no-sync ruff check backend scripts tests` — passed
- `cd frontend && npm test` — 17 passed
- `npm run typecheck` — passed

Re-run that set after #14 is on `main`. No hosted call is part of the tests.

Spot checks if you want them per PR, still from `desk-companion/`:

| PR | Command |
|---|---|
| #7 | `uv run --no-sync pytest -q tests/test_memory.py` |
| #8 | `uv run --no-sync pytest -q tests/test_folder_jobs.py` |
| #9 | `uv run --no-sync pytest -q tests/test_persona.py` |
| #10 | `uv run --no-sync pytest -q tests/test_tasks.py` |
| #11 | `uv run --no-sync pytest -q tests/test_tasks.py tests/test_assistant_data.py` |
| #12 | `cd frontend && npm test && npm run typecheck` |
| #13 | `uv run --no-sync pytest -q tests/test_text_adapters.py tests/test_computer_jobs.py` |
| #14 | `uv run --no-sync pytest -q tests/test_tasks.py tests/test_assistant_data.py` and the frontend commands |

#6 is docs. Confirm `docs/tooling-and-review/` exists and the four living docs still match `main` after the rebase.

## Folder-job check already done in review

PR #8’s path gate is `accept_owner_folder`: absolute path, no NUL, `resolve(strict=True)`, symlink rejected, runtime directory and its parents and children rejected. The model’s `JobInput` has no path field. Writes use `O_EXCL | O_NOFOLLOW` and a 32-hex filename. Read-back is a second open. Cancel does not delete a file that was already written. Owner routes are under `/api/computer` with the owner dependency. Do not widen this while merging.
