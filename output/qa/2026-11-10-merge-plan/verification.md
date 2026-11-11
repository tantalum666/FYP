# 2026-11-10 merge-plan verification

Grok Bot, for Codex. Local check only. No GitHub Actions, no paid model call, no push of the integration branch, no update to PR #97.

## Read for this task

- `AGENTS.md` (repo entry and the banner that later conflicted)
- `handoff.md` on `origin/main` (full, 25 lines) and each conflicting side while merging
- `product.md` current requirements and the table rows that #101, #102, #103, and the #97 dry merge touch
- `decision-log.md` from the 2026-11-05 Pi entries through the 2026-11-07 live-evaluation decision, plus each new section that conflicted
- `docs/merge-guide.md` opening and order (historical 2026-10-27 plan; not reused as the order)
- `planning/2026-10-14/pr-stack-merge-order.md` opening (historical merge-commit rule)
- `START_HERE_NEXT_CHAT.md` on main
- `desk-companion/backend/desk/runtime.py` tick and service wiring, `app.py` routers, `exchange.py` backup keys (`mailbox_bundle`, `shopping_bundle`, `offline_calendar_bundle`)
- Pull-request file lists and the `runtime.py` / `app.py` diffs for #103 and #105

`work-log.md` was not reread from the start. Conflict regions and the appended sections were read on each side.

## What was merged locally

Throwaway branch `cursor/merge-integration-throwaway-1da6` from `origin/main` `855e60ee9f413de84474e3e0b9975b9b9a3d5fbc`. Ordinary `git merge` of #98, #95, #96, #99, #101, #102, #103, #104, #105 in that order. No rebase. The branch was not pushed.

#97 was dry-merged with `--no-commit` and then `git merge --abort`. Its branch was not checked out and was not pushed.

## Tests on the combined tree, before the #97 dry merge

Backend, `desk-companion/`:

```sh
export PYTHONPATH="$PWD:$PWD/backend"
uv run --no-sync pytest -q --tb=line
```

**2103 passed, 1 failed**, 464.71s. The failure is `test_public_unicast[::ffff:93.184.216.34]`. `test_restart_runs_only_the_approved_folder_job` passed.

Frontend, `desk-companion/frontend/`:

```sh
npm test
```

**338 passed, 0 failed**, 0 skipped.

## Docs updated

- Added `desk-companion/docs/merge-guide-2026-11-10.md`
- Added this QA note

`handoff.md`, `decision-log.md`, `work-log.md`, `AGENTS.md`, and `START_HERE_NEXT_CHAT.md` on `main` were left unchanged so the conflict notes stay valid against `855e60ee`.
