# Staple purchase card — 11 November 2026

Grok Bot, offline only. No paid model call, no live mailbox, calendar, merchant, or payment account, and no Pi or VPS change.

## Reading

Read in full: `AGENTS.md`, `handoff.md`, `research/personal-agent-research-index.md`, and `desk-companion/docs/merge-guide-2026-11-10.md` from `origin/cursor/merge-guide-2026-11-10-1da6` (PR #107). Also read the current-requirements and capability sections of `product.md`, `desk-companion/docs/delivery-readiness.md`, `desk-companion/docs/companion-gaps.md`, `desk-companion/docs/mailbox-journey.md`, and `desk-companion/docs/shopping-fixtures.md`.

Open PRs #95–#109 were listed. Their areas were not edited. `exchange.py` was not edited. `mailbox_bundle`, `shopping_bundle`, and `offline_calendar_bundle` stay in the backup payload.

## Choice

The research index’s second acceptance starts by saving an owner-confirmed product, quantity, merchants, shipping-inclusive budget, substitution rule, and address scope. That card was not in main and not in the open slices. Trip quotes, skills, memory follow-ups, browser takeover, Work continuation, and the folder-job clock stay untouched.

## Checks so far

From `desk-companion/`:

```sh
uv run --no-sync ruff check backend/desk/purchase_cards.py backend/desk/tasks.py backend/desk/runtime.py backend/desk/app.py tests/test_purchase_cards.py
PYTHONPATH="$PWD:$PWD/backend" uv run --no-sync pytest tests/test_purchase_cards.py -q --tb=short
```

Ruff passed. Purchase-card tests: **5 passed**.

From `desk-companion/frontend/`:

```sh
node --experimental-strip-types --test tests/purchase-cards.test.ts
npx tsc --noEmit
```

Purchase-card UI tests: **3 passed**. `tsc --noEmit` passed.

Full backend and frontend suites, and the browser pass, are recorded below when they finish.

## Full suites

Pending in this note until the local runs complete. GitHub Actions was not used.
