# Held choices — reading and checks

11 November 2026. Offline only. No paid model call, no live mailbox, calendar, merchant, or payment account, and no Pi or VPS change.

## Read for this slice

- `AGENTS.md` (full) and `handoff.md` (full, 7 November live-agent handoff).
- `research/personal-agent-research-index.md` (full). The three life journeys and the 11 November open slices already cover mail, staple purchase, trip quotes, skills, cited notes, memory follow-up, and morning check-in.
- PR #107 merge guide `desk-companion/docs/merge-guide-2026-11-10.md` on `cursor/merge-guide-2026-11-10-1da6` (full, via `git show`). `Runtime.tick` order and the three backup bundles were left as that guide requires.
- `product.md` current-requirements section and the capability table rows for memory and the agent goal. `desk-companion/docs/companion-gaps.md` (full, 26 lines). `desk-companion/docs/ui-copy.md` (opening contract). `desk-companion/docs/task-tracking.md` (through the goal section). `desk-companion/docs/personal-context.md` (through the API boundary). `desk-companion/docs/sources-and-artifacts.md` (artifact revision section).
- Historical gap tables, openings only: `research/2026-10-12-personal-agents/grok-capability-gap.md`, `dot-capability-gap.md`, `muse-capability-gap.md`.
- Implementation surfaces actually edited or called: `runtime.py` service init (tick unread beyond the existing body, and not modified), `app.py` router registration, `store.operation`, `permissions.change`, owner cookie and `personal_context.require_visible`.

PR bodies #108–#111 were read so this slice would not edit skills, the staple card, or cited briefs. Codex #97 was not checked out and was not edited.

## Chosen slice

Held choices. A choice and the assumption it rests on become current only when the owner approves that exact wording. Changing the assumption keeps the previous wording and does not reuse the old approval.

## Checks

- `ruff check` on `backend/desk/held_choices.py` and `tests/test_held_choices.py`.
- `pytest tests/test_held_choices.py`: 10 passed.
- Frontend `tsc --noEmit` passed. `npm test`: **332 passed, 0 failed** (330 already on this main, plus 2 in `tests/held-choices.test.ts`).
- Full backend, from `desk-companion/` with `PYTHONPATH=.:backend`: **2044 passed, 2 failed**, 503.59s. The failures are the ones already on this main (`855e60ee`): `test_restart_runs_only_the_approved_folder_job` (`expired` vs `succeeded`; #98 fixes that and is not in this branch) and `test_public_unicast[::ffff:93.184.216.34]`. No new failure.
- Browser on `http://127.0.0.1:5190/?page=tasks`: saved a draft, approved it, changed the assumption, confirmed the old wording stayed current, approved the new wording, and saw the old assumption under previous wording. The desk stayed connected. No mail, purchase, or booking control was used.
- GitHub Actions was not run.

## Docs updated

- `desk-companion/docs/held-choices.md` (this slice's handoff)
- `desk-companion/docs/modules.md` (one row)

Not edited, so merge conflicts stay where the 10 November guide put them: `handoff.md`, `work-log.md`, `AGENTS.md`, `START_HERE_NEXT_CHAT.md`, `decision-log.md`, `product.md`, `research/personal-agent-research-index.md`.
