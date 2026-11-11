# Open time in the conversation — 11 November 2026

Grok Bot. Offline. No paid model call, no live mailbox, calendar, merchant, or payment account, and no Pi or VPS change.

## What was read

- `AGENTS.md`, full, as the repo entry rule.
- `handoff.md`, full.
- `product.md`, the current requirements and the branch-status sections through the 30 October application note.
- `research/personal-agent-research-index.md`, full.
- `desk-companion/docs/companion-gaps.md`, full.
- The merge guide on `origin/cursor/merge-guide-2026-11-11-f524` at `desk-companion/docs/merge-guide-2026-11-11.md`: merge order, the living-doc rule, the `Runtime.tick` order, the `goals` import conflict, the three backup bundle keys, and the Codex #97 dry-merge notes. A middle stretch of the per-PR notes was truncated in the read.
- The local-reply order in `assistant.py` and `text_ai.py`, plus the conversation, calendar, and copy sections needed to place one asked question.

`handoff.md`, `work-log.md`, `AGENTS.md`, `START_HERE_NEXT_CHAT.md`, `decision-log.md`, `product.md`, and the research index were not edited. The slice handoff is `desk-companion/docs/open-time.md`.

## What was chosen

Alice answers “When am I free tomorrow?” and “Does Thursday at 15:00 work?” from the saved calendar. The research index still wants a personal agent that can look at the day and say what is possible. The calendar list only names saved events. An unsolicited nudge can use a gap, and it stays silent in quiet hours. This question is asked, so she answers, and she does not book anything. Open pull requests already cover Work continuation, the folder-job clock, browser takeover, memory follow-ups, the morning check-in, trip quotes, skills, the staple card, source briefs, held choices, and “what should I do next?”. This slice does not edit those areas.

## Checks

- `uv run --no-sync ruff check` on `open_time.py`, `assistant.py`, `text_ai.py`, and `tests/test_open_time.py`: passed.
- `tests/test_open_time.py`: 10 passed.
- Frontend `npm test`: 331 passed, 0 failed. That run includes `tests/open-time.test.ts`.
- `npx tsc --noEmit`: exit 0.
- Browser at `http://127.0.0.1:5190/?page=assistant`, `DESK_TEXT_PROVIDER=none`. Clicked the new starter and Send. The reply named Tomorrow 12 Nov 2026, the openings 08:00–10:00 and 11:30–21:00, the label “Open on the saved calendar”, and the sentence that an open stretch is not a claim of being free and nothing was booked. The turn had no confirm control. A following “What is on tomorrow?” named Project discussion and was not labelled as an opening.
- Full backend suite: recorded below when the local run finishes.

`Runtime.tick` is unchanged. The three portable bundles are unchanged. Schema version stays 3.
