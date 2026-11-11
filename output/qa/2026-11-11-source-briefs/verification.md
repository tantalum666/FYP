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

Focused checks, before the full suites:

- `uv run --no-sync ruff check backend/desk/source_briefs.py tests/test_source_briefs.py` passed.
- `uv run --no-sync pytest -q tests/test_source_briefs.py`: 6 passed.
- `node --experimental-strip-types --test tests/source-briefs.test.ts`: 3 passed.
- `npx tsc --noEmit` passed.

Full backend and frontend suites, and the browser pass, are recorded when they finish. GitHub Actions was not used.
