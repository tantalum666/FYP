# Source comparison — reading and verification

11 November 2026. Grok Bot. Offline only. No paid model call.

## Read

- `AGENTS.md` (full, entry rules)
- `handoff.md` (full, 7 November live-agent handoff)
- `research/personal-agent-research-index.md` (full)
- PR #107 `desk-companion/docs/merge-guide-2026-11-10.md` on `cursor/merge-guide-2026-11-10-1da6` (full)
- `product.md` lines 1–83 (current requirements and the implementation table)
- `desk-companion/docs/companion-gaps.md` (full)
- `research/2026-10-12-personal-agents/grok-capability-gap.md` section 2
- `research/2026-10-12-personal-agents/dot-capability-gap.md` sections 4 and 6
- Open PR file lists for #95–#110, and the `app.py` / `runtime.py` hunks for #102, #104, #108, and #110
- `Runtime.tick`, route registration in `app.py`, `store.operation`, shopping owner-session pattern, `personal_context.require_visible`, `MemoryPanel` mount, UI copy default view, and the macOS path check in `docs/integration-acceptance.md`

Not read in full: the rest of `product.md`, the historical research files, and the open PR diffs beyond the file lists and the hunks above.

## Chosen slice

Offline source comparison. Handoff: `desk-companion/docs/source-briefs.md`.

## Verification

Local only. GitHub Actions was not used.

- `uv run --no-sync ruff check backend/desk/source_briefs.py tests/test_source_briefs.py` passed.
- `uv run --no-sync pytest -q tests/test_source_briefs.py`: 6 passed.
- `npx tsc --noEmit` passed.
- Frontend `npm test`: **333 passed, 0 failed**.
- Backend, from `desk-companion/` with `PYTHONPATH=.:backend`: **2040 passed, 2 failed**, 413.13s. The failures are the ones already known on this `main`: `test_restart_runs_only_the_approved_folder_job` and `test_public_unicast[::ffff:93.184.216.34]`.

Chrome on `http://127.0.0.1:5190/?page=memory` opened a comparison, refused a quote that was not in the note, then saved both cited points, the unknown point, and the missing source. The same saved card was visible at 390×844 on `/?surface=phone` under More → Saved memories, and in 简体中文 after the language control. The question and the note text stayed as typed. Draft controls were gone after save. No model call was made.
