# Reply owed — 11 November 2026

Grok Bot, branch `cursor/reply-owed-conversation-6a62`. Offline only. No paid model call, no live mailbox, calendar, merchant, or payment account, and no Pi or VPS change.

## What was read

- `AGENTS.md` and `handoff.md`, in full.
- `research/personal-agent-research-index.md`, in full. The slice follows section 5’s mail-to-task sentence: a thread carries a deadline, the person the owner still needs to reply to, and what the owner is waiting on. Pull request #118 covers the waiting half.
- Merge guide on `origin/cursor/merge-guide-2026-11-11b-24ac` (`desk-companion/docs/merge-guide-2026-11-11b.md`): the merge order, the `Runtime.tick` list, where next step, open time, and meeting prep sit in `text_ai.py` and `AssistantPanel.tsx`, the #97 `has_files` note, and the Codex handoff. The tool view of the middle of that file was truncated; the call sites were then read from the diffs of #114, #115, #116, and #118.
- `product.md` through the current requirements. `desk-companion/docs/companion-gaps.md`, `mailbox-journey.md`, and the start of `demo-script.md`. `ui-copy.md` default-view section. Historical `research/2026-10-12-personal-agents/grok-capability-gap.md` capability table, not used as a current decision.
- On this branch, before editing: `assistant.py` local message and proposal path, `text_ai.py` `_message`, `tasks.py` `TaskInput` / create, and the assistant panel composer, help list, and turn markup. `waiting_on.py` was read from the #118 branch so this slice would not reuse its phrases or its insertion lines.

`handoff.md`, `work-log.md`, `AGENTS.md`, `START_HERE_NEXT_CHAT.md`, `decision-log.md`, `product.md`, and the research index were not edited. The slice handoff is `desk-companion/docs/reply-owed.md`.

## What was built

`desk/reply_owed.py` answers “Who do I need to reply to?” and holds “I need to reply to Sam about the venue” as a task draft until Allow once. Status stays `todo`. `waiting_for` stays empty. No new table. `Runtime.tick` is unchanged.

## Checks

From `desk-companion/`, CPython 3.12.3, pytest 9.1.1, ruff 0.16.9. `PYTHONPATH` was `$PWD:$PWD/backend`. `DESK_TEXT_PROVIDER` was not a live key. The provider test uses `httpx.MockTransport` and records zero requests.

- `uv run --no-sync pytest tests/test_reply_owed.py -q --tb=line`: **40 passed**.
- `uv run --no-sync pytest -q --tb=line`: **2074 passed, 2 failed**, 473.25s. The failures are the ones already on this `main` (`855e60ee`): `tests/test_public_capture_transport.py::test_public_unicast[::ffff:93.184.216.34]` and `tests/test_folder_jobs.py::test_restart_runs_only_the_approved_folder_job` (`#98` fixes that and is not in this branch). No other failure.
- `uv run --no-sync ruff check`: all checks passed.
- Frontend `npm test`: **331 passed, 0 failed**, about 9.4s.
- `npx tsc --noEmit`: exit 0.

Browser on `http://127.0.0.1:5190/` with `DESK_TEXT_PROVIDER=none` and `DESK_AUTO_OWNER=1`. The empty question said “You do not owe a reply.” “I need to reply to Sam about the venue.” stayed a draft until Allow once. Asking again named Sam and the venue. Tasks listed “Reply to Sam about the venue” as To do, not under Waiting.

## Not done

A live mailbox, a sent message, and a real calendar account are still separate. `我要…` remains a goal, not this slice.
