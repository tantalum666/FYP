# Saved skills — local verification, 10 November 2026

Grok Bot, Cursor cloud agent. Offline only. No paid model call, no live mailbox, calendar, merchant, or payment account, no Pi or VPS change.

## Reading

Read in full: `AGENTS.md`, `handoff.md`, `research/personal-agent-research-index.md`, and PR #107’s `desk-companion/docs/merge-guide-2026-11-10.md` (branch `cursor/merge-guide-2026-11-10-1da6`).

Read for the choice and the slice, not as a full-repo reread: `product.md` current requirements, `desk-companion/docs/companion-gaps.md`, `routines.md`, `task-tracking.md`, `mailbox-journey.md`, `responsibilities.md` (opening and HTTP sections), `agent-loop.md` (the one-effect limit), `delivery-readiness.md`, `ui-copy.md` (default view and action-time sections), the October Grok and Muse capability-gap tables, and the 3 October Dot tracking note’s worked example. Open PR file lists for #95–#105 and #97 were taken from GitHub so this slice would stay out of those paths.

## Choice

Saved skills: an owner-checked checklist becomes one immutable skill. A later fill stays pending until that owner approves the exact inputs. The result is local. It is not mail, a purchase, a booking, or a system-verified completion.

## Checks

From `desk-companion/`, with `uv run --no-sync`:

- `pytest -q tests/test_saved_skills.py` — 8 passed.
- `ruff check backend/desk/saved_skills.py tests/test_saved_skills.py` — clean.
- Full backend `pytest -q --tb=line` with `PYTHONPATH` including the desk-companion root and `backend`: **2042 passed, 2 failed**, 427.86s. Failures are the ones already known on this `main`: `tests/test_folder_jobs.py::test_restart_runs_only_the_approved_folder_job` (`expired` vs `succeeded`; #98’s clock fix is not in this branch) and `tests/test_public_capture_transport.py::test_public_unicast[::ffff:93.184.216.34]`.

From `desk-companion/frontend/`:

- `npm test` — **332 passed, 0 failed**. That includes the two new saved-skill tests. `npm run build` (`tsc --noEmit` and Vite) succeeded.

Browser, against the built UI served by the local API on `127.0.0.1:8831` (clean runtime directory, no proxy): Chrome opened `/?page=tasks`, left the checklist unchecked and confirmed nothing was saved, then checked it, saved “Friday supply check”, prepared `quantity` 2 with the note omitted, approved, and saw “Saved on this desk after your approval.” The Approve button was gone. The same saved result was visible at a 390×844 viewport. Screenshots: `/opt/cursor/artifacts/saved-skills.png` and `saved-skills-phone.png`.

`Runtime.tick` was not edited. A pending run stayed pending across a tick. Backup JSON still has `mailbox_bundle`, `shopping_bundle`, and `offline_calendar_bundle`, and no `saved_skill_bundle`.

## Docs updated here

`desk-companion/docs/saved-skills.md` and this note. Living handoff, work log, decision log, product contract, AGENTS, and the research index were not edited.
