# Staple purchase card — 11 November 2026

Grok Bot, offline only. No paid model call, no live mailbox, calendar, merchant, or payment account, and no Pi or VPS change.

## Reading

Read in full: `AGENTS.md`, `handoff.md`, `research/personal-agent-research-index.md`, and `desk-companion/docs/merge-guide-2026-11-10.md` from `origin/cursor/merge-guide-2026-11-10-1da6` (PR #107). Also read the current-requirements and capability sections of `product.md`, `desk-companion/docs/delivery-readiness.md`, `desk-companion/docs/companion-gaps.md`, `desk-companion/docs/mailbox-journey.md`, and `desk-companion/docs/shopping-fixtures.md`.

Open PRs #95–#109 were listed. Their areas were not edited. `exchange.py` was not edited. `mailbox_bundle`, `shopping_bundle`, and `offline_calendar_bundle` stay in the backup payload.

## Choice

The research index’s second acceptance starts by saving an owner-confirmed product, quantity, merchants, shipping-inclusive budget, substitution rule, and address scope. That card was not in main and not in the open slices. Trip quotes, skills, memory follow-ups, browser takeover, Work continuation, and the folder-job clock stay untouched.

## Checks

From `desk-companion/`:

```sh
uv run --no-sync ruff check backend/desk/purchase_cards.py backend/desk/tasks.py backend/desk/runtime.py backend/desk/app.py tests/test_purchase_cards.py
PYTHONPATH="$PWD:$PWD/backend" uv run --no-sync pytest -q --tb=line
PYTHONPATH="$PWD:$PWD/backend" uv run --no-sync pytest tests/test_purchase_cards.py -q --tb=short
```

Ruff passed. Full backend suite: **2039 passed, 2 failed**. The failures are the known `test_public_unicast[::ffff:93.184.216.34]` and `test_restart_runs_only_the_approved_folder_job`. After that suite, the purchase-card test gained one assertion that a later over-budget offer does not replace a recorded receipt. Re-running `tests/test_purchase_cards.py`: **5 passed**.

From `desk-companion/frontend/`:

```sh
npm test
npx tsc --noEmit
```

Full frontend suite: **333 passed, 0 failed**. `tsc --noEmit` passed after the form stayed available following a receipt.

## Browser

`http://127.0.0.1:5190/?page=tasks` on the local owner session. Saved a Tissues card, confirmed it, checked a matching offer, approved it, recorded fixture receipt `rcpt-1`, then checked an over-budget offer. The task stayed Waiting, with “Fixture receipt rcpt-1 recorded. Not a live purchase.” The card said “Total including shipping is over the budget.” and “Nothing has been bought.” No control said a purchase succeeded.

Screenshots: `purchase-card-confirmed.png`, `purchase-card-needs-approval.png`, `purchase-card-receipt.png`, `purchase-card-over-budget.png`.

GitHub Actions was not used.
