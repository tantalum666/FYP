# Saved-skill schedule — local verification, 10 November 2026

Grok Bot, Cursor cloud agent. Offline only. No paid model call, no live mailbox, calendar, merchant, or payment account, no Pi or VPS change.

## Reading

Read in full: `AGENTS.md`, `desk-companion/docs/saved-skills.md` (the #108 checklist slice), `desk-companion/docs/routines.md`, and the saved-skill service, routes, panel, and tests on `cursor/saved-skills-d761`.

Read for the choice, not as a full-repo reread: `product.md` current requirements, `handoff.md` (the 7 November live-eval handoff; its next step is browser takeover, which this task does not take), `research/personal-agent-research-index.md` sections 1–2 and the capability table, the October Grok capability-gap rows for reusable skills and scheduled work, `desk-companion/docs/ui-copy.md` (default view and action-time), `Runtime.tick`, the routine tick and occurrence function, and the nudge quiet-hour window. `decision-log.md` was not reread; the user instruction and the saved-skill doc named the next slice.

## Choice

Schedule a saved skill on the existing routine clock. A due occurrence prepares one pending run with the stored fill. The owner still approves it. Quiet hours, proactive off, and a time more than two minutes late are skipped and are not prepared later.

An edit that creates a new skill version was left for the next slice. A skill is still immutable, so there is no old run to invalidate yet. Doing both would mix a scheduler change with a new approval rule.

The schedule is not a `day_briefing` row and does not enter the routine delivery inbox. `RoutineService.tick` calls `saved_skills.release_due` in the same write transaction, after the briefing loop. `Runtime.tick` is unchanged: mailbox, shopping, offline calendar, then the existing later calls, including `routines.tick`.

## Checks

From `desk-companion/`, with `uv run --no-sync` and `PYTHONPATH=.:backend` for the full suite:

- `ruff check` on `saved_skills.py`, `routines.py`, and `tests/test_saved_skills.py` — clean.
- `pytest -q tests/test_saved_skills.py tests/test_routines.py` — 43 passed before the one-off resume test was added. That test then passed on its own. The full suite below includes it.
- Full backend `pytest -q --tb=line`: **2049 passed, 2 failed**, 573.90s. Failures are the ones already known on this line: `tests/test_folder_jobs.py::test_restart_runs_only_the_approved_folder_job` and `tests/test_public_capture_transport.py::test_public_unicast[::ffff:93.184.216.34]`.

From `desk-companion/frontend/`:

- `npm test` — **332 passed, 0 failed**. The saved-skill tests now also cover an omitted schedule note, the skip copy, and the Schedule control.
- `npm run build` (`tsc --noEmit` and Vite) succeeded.

Browser, against the built UI served by the local API on `127.0.0.1:8831` (clean runtime directory, clock file, no proxy): Chrome opened `/?page=tasks`, left the checklist unchecked and saw “Mark it checked only after you have done it.”, then checked it and saved “Friday supply check”. The fill `quantity` 2 and `数量` 两包 was scheduled daily at 2026-11-10 09:00 Asia/Hong_Kong with the note omitted. Before the occurrence, the card read “Daily · Active · 2026-11-10 09:00” and no run was waiting. After the clock entered the two-minute window, the database held one pending run with `origin=schedule`, zero tasks, zero jobs, and zero mailbox rows. Reload showed “Prepared at the scheduled time. Waiting for your approval.” Approve replaced it with “Saved on this desk after your approval.” and removed Approve. The schedule’s next time was 2026-11-11 09:00. The same result was visible in a 390×844 viewport: the sidebar was hidden, the bottom navigation was visible, and the schedule fields stacked. The existing floating companion still overlaps the lower card at that width. Screenshots: `/opt/cursor/artifacts/saved-skill-schedule.png`, `saved-skill-approved.png`, and `saved-skill-schedule-phone.png`.

## Docs updated here

`desk-companion/docs/saved-skills.md` and this note. Living handoff, work log, decision log, product contract, AGENTS, and the research index were not edited.
