# Waiting on — reading and verification

11 November 2026. Branch `cursor/waiting-on-conversation-eae3`. Offline only. No paid model call. No mailbox, merchant, calendar account, or Pi change.

## Read

- `AGENTS.md` in full.
- `handoff.md` in full (7 November live evaluation; not edited).
- `research/personal-agent-research-index.md` in full. The first journey is mail to a task to a suggestion, including something still outstanding.
- PR #117 merge guide `desk-companion/docs/merge-guide-2026-11-11b.md` in full, from branch `cursor/merge-guide-2026-11-11b-24ac`.
- `product.md` current requirements and the 11 November capability table in the research index. `desk-companion/docs/companion-gaps.md` ranks a review of what happened first; that review already exists as the digest page. `desk-companion/docs/task-tracking.md` sections on waiting status and local task sentences.
- Implementation read for the slice: `assistant.py` `_local_message` and `task_message`, `text_ai.py` `_message` and `maybe_extract`, `tasks.py` create/action/listing, `ProposalActionCard.tsx` waiting line, `digest.py` (existing page, not this slice), `ui-copy.md` default-view section.

Not edited: `handoff.md`, `work-log.md`, `AGENTS.md`, `START_HERE_NEXT_CHAT.md`, `decision-log.md`, `product.md`, the research index.

## Chosen

Who the owner is waiting on, answered in the Alice conversation. A draft until Allow once. Contract: `desk-companion/docs/waiting-on.md`.

## Checks

- Backend, from `desk-companion/`, `PYTHONPATH=.:backend`, `uv run --no-sync pytest -q --tb=line`, no `DESK_TEXT_PROVIDER` override: **2063 passed, 2 failed**, 501.34s. Failures are the known `test_restart_runs_only_the_approved_folder_job` and `test_public_unicast[::ffff:93.184.216.34]`.
- Focused `tests/test_waiting_on.py`: 29 passed.
- Frontend `npm test`: **332 passed, 0 failed**. The two new tests are in `frontend/tests/waiting-ask.test.ts`.
- `npx tsc --noEmit`: exit 0.
- `uv run --no-sync ruff check`: all checks passed.
- Browser on `http://127.0.0.1:5190/?page=assistant` with `DESK_TEXT_PROVIDER=none` and `DESK_AUTO_OWNER=1`. The button filled “What am I waiting on?” and the reply was “You are not waiting on anyone.” “I'm waiting on Sam for the budget” showed Permission needed and “Nothing is saved until you allow it.” Allow once saved the task. Asking again replied “Waiting on Sam for the budget.” Tasks showed that title with status Waiting. Recording: `/opt/cursor/artifacts/waiting-on-alice-conversation.mp4`.

GitHub Actions was not run.
