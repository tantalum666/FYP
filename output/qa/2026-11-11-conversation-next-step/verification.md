# Conversation next step — 11 November 2026

Grok Bot, offline only. No paid model call, no live mailbox, calendar, merchant, or payment account, and no Pi or VPS change.

## Read

- `AGENTS.md` (entry rules), `handoff.md` (7 November live-agent state), `product.md` (current contract, not edited), `research/personal-agent-research-index.md` (capability table and the “come back with a next step” flow).
- Open PR #113 merge guide `desk-companion/docs/merge-guide-2026-11-11.md` on `cursor/merge-guide-2026-11-11-f524` (full file).
- Focused code: `text_ai.py` message path, `assistant.py` local parser, `moments.py`, `nudges.py`, `AssistantPanel.tsx` reply rendering. Historical gap notes in `desk-companion/docs/companion-gaps.md` and the Dot/Grok capability pages were used only to choose the slice.

## Choice

Alice answers “What should I do next?” / “接下来做什么？” in the existing conversation from the selected task, the soonest timed event, or an open goal. She does not do the step. Moments stay silent in quiet hours and when proactivity is off; this question still answers because the owner asked. Not an approval card.

## Checks

From `desk-companion/`:

```sh
export PYTHONPATH="$PWD:$PWD/backend"
uv run --no-sync pytest -q --tb=line
```

**2043 passed, 2 failed**, 538.78s. Failures are the known main cases `tests/test_public_capture_transport.py::test_public_unicast[::ffff:93.184.216.34]` and `tests/test_folder_jobs.py::test_restart_runs_only_the_approved_folder_job`. The focused file `tests/test_conversation_next_step.py` passed 9 tests inside that run.

```sh
cd frontend && npm test
```

**331 passed, 0 failed.** `npx tsc --noEmit` exited 0. `uv run --no-sync ruff check` passed.

Browser, `http://127.0.0.1:5190/`, automatic local owner, `DESK_TEXT_PROVIDER=none`. A saved task “Print the handout” / “check the room” was created through `POST /api/tasks`. Clicking “What should I do next?” and Send showed the label “Next step” and the sentence that the saved step is check the room and has not been done. No Allow or Confirm control appeared on that reply.

## Docs

Handoff for this slice is `desk-companion/docs/conversation-next-step.md`. Living files (`handoff.md`, `work-log.md`, `AGENTS.md`, `START_HERE_NEXT_CHAT.md`, `decision-log.md`, `product.md`, the research index) were not edited.
