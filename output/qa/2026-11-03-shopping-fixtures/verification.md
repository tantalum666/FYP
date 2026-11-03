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
uv run --no-sync ruff check backend/desk/shopping backend/desk/assistant.py backend/desk/assistant_routes.py backend/desk/app.py backend/desk/runtime.py tests/test_shopping_fixtures.py
uv run --no-sync pytest tests/test_shopping_fixtures.py tests/test_permissions.py -q
```

Ruff: all checks passed.

Pytest: **28 passed** (6 shopping, 22 existing permission decisions) in 12.03s, plus the existing Starlette/httpx test-client deprecation. The shopping file alone was 6 passed in 3.90s.

## Gaps

- No real merchant, inventory, shipping quote, address, or payment. A fixture is not an order receipt.
- Sync interruption is `disconnect_after` on the JSON sync call. It uses the same commit boundary as a dropped client; it is not a cancelled socket in the middle of a byte.
- Portable JSON backup does not include the shopping cursor tables. Whole-file SQLite copies do. Backup code was not changed.
- Full backend and frontend suites were not re-run.
