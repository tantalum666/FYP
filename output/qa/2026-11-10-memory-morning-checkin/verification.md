# Morning memory check-in verification

10 November 2026. Offline. No paid model call, live mailbox, calendar, merchant, or Pi change.

## Reading

Read in full: `AGENTS.md`, `handoff.md`, `desk-companion/docs/memory-followups.md`, and the memory follow-up service, its HTTP tests, and the Memory page section.

Read `product.md` through the current requirements and the memory row, the 10 November memory-follow-up decision in `decision-log.md`, `desk-companion/docs/memory.md` through the follow-up section, the morning/evening check-in section of `desk-companion/docs/task-tracking.md`, and the default-view section of `desk-companion/docs/ui-copy.md`. Read the nudge service, notice delivery, and the rules tick so the check-in could reuse them.

## Choice

The morning and evening task check-ins stay on the preference clock. They summarize tasks and calendar items. A second scheduler was not added. The memory follow-up tick already runs from the rules loop, so the approved morning check-in is another row on that tick. While it is waiting, follow-ups due by its time are not raised one by one. When the minute arrives, and quiet hours and proactive reminders allow it, one notice cites each fact that is still active. The always-on display only says to open Memory.

## Scope

`desk/memory_followups.py` gained the check-in, and `desk/notify.py` keeps fact text off the device announcement. The Memory page prepares, approves, and dismisses it. `runtime.py` was not given another tick. Mailbox, shopping, and offline calendar bundles were not edited.

## Checks

- `PYTHONPATH=. .venv/bin/pytest tests/test_memory_morning_checkin.py tests/test_memory_followups.py -q`: 21 passed. The 12 new tests cover draft-does-not-write, owner and display boundaries, another login denied, fewer than two follow-ups, operation retry, rejected confirm, omitted fields, one notice for four follow-ups, current wording, no second raise, an already-raised fact left out, early follow-ups waiting, quiet hours across restart, proactivity off, forgotten and expired wording, a dropped notice retried once after quiet hours, wording dropped when the facts are forgotten before that retry, dismiss releasing the follow-ups, and a follow-up approved later still joining. The previous 9 follow-up tests still passed.
- `npm test` in `frontend`: 333 passed, 0 failed.
- `npm run build` (`tsc --noEmit` and Vite) passed.
- `uv`/`ruff check backend scripts tests` passed.
- Full backend, `PYTHONPATH=. .venv/bin/pytest -q --tb=line`, no `DESK_*` overrides: **2055 passed, 2 failed**. The failures are the known `test_public_unicast[::ffff:93.184.216.34]` and `test_restart_runs_only_the_approved_folder_job`.
- Chrome on `http://127.0.0.1:8831/?page=memory`: saved both facts, approved a follow-up for each, prepared one check-in, saw both facts and that nothing is scheduled until approval, approved it, read the single pending reason citing both, then dismissed it. The dentist minute was entered as 09:09 rather than 09:00; 09:09 and 09:15 were both before the 09:30 check-in, and both facts were cited. Screenshots: draft, approved, dismissed.

A timed raise was not waited out in Chrome. The injected-clock HTTP tests cover quiet hours, restart, a dropped delivery, and forgotten wording.
