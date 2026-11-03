# Offline shopping fixtures

3 November 2026. Group 2. Local only. No store account, payment, paid model, GitHub Actions, Pi, or mailbox module.

## Read for this slice

- `AGENTS.md` (workspace entry)
- `product.md` current requirements
- `handoff.md`
- `decision-log.md` from the 2026-10-30 research decision through the PR5 merge
- `research/personal-agent-research-index.md` (shopping journey in sections 4 and 5)
- `desk-companion/docs/pr5-integration.md`
- PR #78 `desk-companion/docs/integration-acceptance.md` on `cursor/integration-acceptance-harness-dcc2` (not on main; not edited)
- Current `TaskService`, `PermissionService`, `Notifier`, `Responsibility` was inspected and not used as a second watch core. Work is the existing agent-run service. Drafts use `AssistantService`.

## Result

Offline fixtures load from disk. Sync commits one sequence number at a time onto one task and one paused Work run. Advice is an owner-confirmed `shopping_advice` draft. Notices fire only for a threshold price drop, a shipment or delay change, or a decision. Revoke returns before the fixture file is parsed.

## Commands

From `desk-companion/` after `uv sync --frozen --group dev` (CPython 3.12.3):

```sh
uv run --no-sync ruff check backend/desk/shopping backend/desk/exchange.py tests/test_shopping_fixtures.py
uv run --no-sync pytest tests/test_shopping_fixtures.py tests/test_exchange.py tests/test_backup_persona_jobs.py tests/test_integration_boundaries.py tests/test_memory_gaps.py tests/test_risk_gaps.py tests/test_tasks.py -q
```

Ruff: all checks passed.

Pytest: **62 passed** in 17.95s. That is the shopping HTTP file, including backup, restore, and a second sync, plus the exchange, persona/job backup, integration-boundary, memory, risk, and task backup files. The earlier shopping-plus-permissions run remains 28 passed in 12.03s. Starlette/httpx test-client deprecation is unchanged.

## Gaps

- No real merchant, inventory, shipping quote, address, or payment. A fixture is not an order receipt.
- Sync interruption is `disconnect_after` on the JSON sync call. It uses the same commit boundary as a dropped client; it is not a cancelled socket in the middle of a byte.
- Portable JSON backup now includes the shopping connection, cursor, applied receipts, subject mapping, and out-of-order buffer. It does not include the owner session, drafts, notices, or the paused Work run row. Whole-file SQLite copies still do.
- Full backend and frontend suites were not re-run.
