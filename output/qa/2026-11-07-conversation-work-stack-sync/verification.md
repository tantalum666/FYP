# Sync the conversation-work stack onto main after #94

7 November 2026. Grok Bot completed this through a Cursor cloud agent. Codex reviews and merges. This is a merge sync, not a new feature slice. #95 is `cursor/conversation-work-reshow-verified-b9a2`. #96 stays stacked on that branch. Drafts #73, #87, and #88 were not edited. #94 was not reopened.

## What was read

Full files: [AGENTS.md](../../../AGENTS.md), [handoff.md](../../../handoff.md), [product.md](../../../product.md) through the current-requirements and 30 October sections, [START_HERE_NEXT_CHAT.md](../../../START_HERE_NEXT_CHAT.md), and the prior [re-show QA](../2026-11-07-conversation-work-reshow/verification.md).

Sections: [decision-log.md](../../../decision-log.md) from the 6 November goal-change entries through the new sync entry, [work-log.md](../../../work-log.md) from the 6 November goal-change entries, and [personal-agent-research-index.md](../../../research/personal-agent-research-index.md) section 4 plus the 7 November live update.

Compared `origin/main` at `855e60ee9f413de84474e3e0b9975b9b9a3d5fbc` with #95 at `cd209eaafd9398558c4b8e37c794b74005510518`. Merge base is `f2dbb795f988b762242ef3eebcdba7ecf8a37bb2`.

## Conflict files

Resolved by hand:

- `AGENTS.md`
- `START_HERE_NEXT_CHAT.md`
- `handoff.md`
- `research/personal-agent-research-index.md`
- `work-log.md`

Auto-merged, then checked: `decision-log.md` kept both the re-show entry and the #94 browser/VPS entries. `desk-companion/backend/desk/text_ai.py` kept main's OpenAI text defaults and the re-show call `ConversationWork.turn(..., conversation=conversation)`.

The re-show behavior stays: a later ask reads the verified file again, `result.verified` still requires `verified` plus `byte_readback`, and the offline executor does not run again. #94's browser, VPS, and live-evaluation records stay.

## Commands

From `desk-companion/`. `uv sync --group dev` created `.venv`. `npm ci` in `frontend/` supplied the frontend tests. Neither install is part of the change. No `OPENAI_API_KEY` was set.

```sh
uv run --no-sync ruff check backend/desk/conversation_work.py backend/desk/text_ai.py tests/test_conversation_work.py
uv run --no-sync python -m pytest tests/test_conversation_work.py tests/test_integration_acceptance.py -q
uv run --no-sync python -m pytest -q --tb=line
```

From `frontend/`:

```sh
npm test
npx tsc --noEmit
```

On current `origin/main`, the same folder test was run from a detached worktree:

```sh
python -m pytest tests/test_folder_jobs.py::test_restart_runs_only_the_approved_folder_job -q --tb=line
```

## Results

Ruff passed. Conversation-work and integration acceptance: 75 passed in 38.37s. Full backend: 2042 passed, 2 failed, in 408.19s. Frontend tests: 330 passed. `tsc --noEmit` passed. Paid provider calls: 0. GitHub Actions: not run.

## Failures that this merge did not introduce

`tests/test_public_capture_transport.py::test_public_unicast[::ffff:93.184.216.34]` failed. `is_public_unicast` rejects the address. This sync does not change that transport check.

`tests/test_folder_jobs.py::test_restart_runs_only_the_approved_folder_job` failed with `expired` instead of `succeeded`. The file is identical to `origin/main`. The same command on `origin/main` (`855e60e`) failed with the same assertion. The fixture freezes the first app at 2026-11-07 00:00 UTC, and the restarted app uses the wall clock. At 2026-11-07 07:33 UTC that approved job is already outside its execution window. This sync does not change the test or the folder job code.

## #96 merge

The same five documentation files conflicted when the updated #95 branch was merged into `cursor/conversation-work-continue-once-51ee`. `parse_work_continue` and the one `advance_one` step stayed. A status ask still only re-reads the file. #94 records stayed. The pull request base remains the #95 branch.

From `desk-companion/`, with no `OPENAI_API_KEY`:

```sh
uv run --no-sync ruff check backend/desk/conversation_work.py backend/desk/agent_runs.py backend/desk/text_ai.py tests/test_conversation_work.py
uv run --no-sync python -m pytest tests/test_conversation_work.py tests/test_integration_acceptance.py -q
uv run --no-sync python -m pytest -q --tb=line
```

From `frontend/`: `npm test` and `npx tsc --noEmit`.

Ruff passed. Conversation-work and integration acceptance: 86 passed in 46.30s. Full backend: 2053 passed, 2 failed, in 403.83s. The two failures are the same two named above. Frontend tests: 330 passed. `tsc --noEmit` passed. Paid provider calls: 0. GitHub Actions: not run.
