# 2026-11-11 merge plan — reading and verification

Grok Bot, 11 November 2026. This note records what was read and what was run for [the merge guide](../../../desk-companion/docs/merge-guide-2026-11-11.md). It does not edit living docs. The throwaway integration branch was not pushed.

## Read

- `AGENTS.md` in full, from the repository entry that opens with this checkout.
- `product.md`: the 7 November opening, the current-requirements section, and the contract rows that later conflicted with #97. Not the whole historical contract.
- `handoff.md` in full on `main`, then both sides of each living-doc conflict while merging.
- `decision-log.md`: the opening through the 30 September software-plan entries, then each new `##` section that a merge touched. Not the whole Senplate-era archive.
- `work-log.md` and `START_HERE_NEXT_CHAT.md`: the conflicted tails and openings, not every historical section.
- `desk-companion/docs/merge-guide-2026-11-10.md` from `origin/cursor/merge-guide-2026-11-10-1da6`. The first read truncated the middle of step 3; the resolutions below were produced by merging, not by copying an unread passage.
- `desk-companion/backend/desk/runtime.py` and `app.py` at each code-overlap step, plus `routines.py`, `exchange.py`, `TaskPanel.tsx`, `MemoryPanel.tsx`, `App.tsx`, and the route prefixes of the five new services.
- Pull-request tips for #98, #95, #96, #99, #101, #102, #103, #104, #105, #108, #109, #110, #111, #112, and #97, via `gh pr view`. `origin/main` was `855e60ee9f413de84474e3e0b9975b9b9a3d5fbc`.

## What was merged

Local branch `cursor/merge-integration-throwaway-f524` from that `main`. Ordinary `git merge`, no rebase, no force-push. Order: #98, #95, #96, #99, #101, #102, #103, #104, #105, #108, #109, #110, #111, #112. Conflict files and resolutions are in the guide. The branch was not pushed.

## Checks

From `desk-companion/`, after step 14 and before the #97 dry merge:

```sh
export PYTHONPATH="$PWD:$PWD/backend"
uv run --no-sync pytest -q --tb=line
uv run --no-sync ruff check
```

From `desk-companion/frontend/`:

```sh
npm test
npx tsc --noEmit
```

- Backend: 2139 passed, 1 failed, 519.18s. The failure is `tests/test_public_capture_transport.py::test_public_unicast[::ffff:93.184.216.34]` on CPython 3.12.3. Two warnings (Starlette/`httpx` deprecation, empty `pytest.raises` match).
- Frontend: 348 passed, 0 failed, 0 skipped.
- Ruff 0.16.9: all checks passed.
- `tsc --noEmit`: exit 0.

No other failure appeared. No commit was pushed to #108–#112 or to any Codex branch.

## #97

`git merge --no-commit --no-ff origin/codex/alice-home-wake-20261107` (`ebf6d917`) conflicted in eight documentation files. No code conflict marker. The merge was aborted. `Runtime.tick` on that uncommitted merge still had mailbox, shopping, trips, offline calendar, `memory_followups.tick`, and `purchase_cards.release_quiet_notices`.

## Docs updated by this pull request

- Added `desk-companion/docs/merge-guide-2026-11-11.md`
- Added this QA note

Not updated, on purpose, so the conflict surface against `main` stays valid: `handoff.md`, `work-log.md`, `decision-log.md`, `AGENTS.md`, `START_HERE_NEXT_CHAT.md`, `product.md`, and the 10 November merge guide.
