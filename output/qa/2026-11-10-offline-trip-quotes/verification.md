# Offline trip quotes

10 November 2026. Grok Bot. Offline only. No paid model call, live mailbox, merchant, payment account, or Pi change.

## Reading

Full: `AGENTS.md`, `START_HERE_NEXT_CHAT.md`, `handoff.md`, `product.md`, `research/personal-agent-research-index.md`, `desk-companion/docs/companion-gaps.md`, `desk-companion/docs/routines.md`, `desk-companion/docs/delivery-readiness.md`, `desk-companion/docs/shopping-fixtures.md`, `desk-companion/docs/mailbox-journey.md`.

Partial: `decision-log.md` through the 6 October personal-agent entry; `research/2026-10-12-personal-agents/grok-capability-gap.md` capability table; `desk-companion/docs/agent-loop.md` and `personal-context.md` openings. Open PR file lists for #95–#103 were checked so this slice would not edit those areas.

## Choice

Mailbox and shopping already keep one task across an offline source. Memory follow-ups, conversation Work, browser takeover, and the Alice home/attachments work are open PRs. The research index still has no offline record of a fare that is quoted, held, refused after a payment failure, or matched to a receipt. This slice adds that, on the existing task table, without a second scheduler or a model call.

## What was checked

- `uv run --no-sync ruff check backend/desk/travel_quotes backend/desk/app.py backend/desk/runtime.py tests/test_travel_quotes.py` passed.
- `tests/test_travel_quotes.py`: 8 passed. Covers one task, omitted fields, null not clearing, a rejected hold storing no success, the same operation id retried, reprice invalidating a hold, payment failure not ticketed, a blocked ticket staying blocked, a matching receipt, a later schedule change, disconnect/gap/conflict/restart, revoke, paired display and hidden private context, and one quiet-hours notice.
- Full backend `pytest`: **2042 passed, 2 failed**. Failures are the known `test_public_unicast[::ffff:93.184.216.34]` and `test_restart_runs_only_the_approved_folder_job` (fixed in #98).
- Frontend `npm test`: 333 passed, 0 failed. `tsc --noEmit` passed.
- Chrome on Tasks → Work & tools → Trip quote read fixture `hkg-tyo`, showed HKG to TYO, 1 December 09:00 Hong Kong to 2 December 14:30 Tokyo, HKD 2080.00, “Not held and not ticketed.”, and “No card is charged.” Approve changed the status to “Held. Not paid and not ticketed.” and removed the approve button. Reload kept the hold and showed the task “HKG to TYO”. SQLite `trip_itinerary.booking_state` was `held` and `ticket_receipt` was empty.

`mailbox_bundle`, `shopping_bundle`, and `offline_calendar_bundle` were not edited. Handoff for this slice is `desk-companion/docs/offline-trip-quotes.md`. `handoff.md`, `work-log.md`, `AGENTS.md`, `START_HERE_NEXT_CHAT.md`, and the research index were left unchanged so the open PRs can merge.
