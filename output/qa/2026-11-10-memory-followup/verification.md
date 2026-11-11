# Memory follow-up verification

10 November 2026. Offline. No paid model call, live mailbox, calendar, merchant, or Pi change.

## Reading

Read in full: `AGENTS.md`, `START_HERE_NEXT_CHAT.md`, `handoff.md`, `product.md`, `research/personal-agent-research-index.md`, `desk-companion/docs/companion-gaps.md`, `desk-companion/docs/delivery-readiness.md`, `desk-companion/docs/memory.md` (through the 29 October section, which was the end), and `research/2026-10-03-dot/proactive-task-tracking.md`.

Read the 4–7 November decisions in `decision-log.md`, and `desk-companion/docs/task-tracking.md` through the 29 October continuation. Read the follow-up, quiet-hour, notice, and memory routes that this slice reuses, plus the open PR file lists for #95, #96, #97, #98, #99, and #101.

## Choice

Browser takeover, conversation Work, the folder-job clock, and the Alice home are already open. A saved fact in `owner_memories` could expire, but Alice never raised it at a time the owner approved. Task follow-ups and the morning/evening check-ins do not do that. This slice adds that one path.

## Scope

New service `desk/memory_followups.py`, routes, a Memory page section, and tests. `runtime.py` only constructs the service and calls its tick after memory expiry. `app.py` only registers the router. No edit to conversation Work, computer use, folder jobs, mailbox/shopping/calendar bundles, or the Alice home files.

## Checks

- `PYTHONPATH=. .venv/bin/pytest tests/test_memory_followups.py -q`: 9 passed after the browser found that Dismiss was sending `dismiss` instead of `dismissed`. The re-run covers draft-does-not-write, owner and display boundaries, operation retry, rejected confirm, omitted fields, current wording, quiet-hour hold across restart, proactivity off, forgotten memory, snooze, handled, the three-raise cap, a dropped notice, and dismiss.
- `npm test` in `frontend`: 331 passed, 0 failed.
- `npm run build` (`tsc --noEmit` and Vite) passed.
- `uv run --no-sync ruff check backend scripts tests` passed.
- Full backend, same pytest command, no `DESK_*` overrides: **2043 passed, 2 failed**. The failures are the known `test_public_unicast[::ffff:93.184.216.34]` and `test_restart_runs_only_the_approved_folder_job`.
- Chrome on `http://127.0.0.1:8831/?page=memory`: saved a fact, prepared a follow-up, saw that nothing is scheduled until approval, approved it, read the pending reason, then dismissed it. The list API matched the page. Screenshots: draft, approved, dismissed.

A timed raise was not waited out in Chrome. The injected-clock HTTP tests cover quiet hours, restart, and a dropped delivery.
