# Offline calendar journey QA

3 November 2026. Branch `cursor/offline-calendar-journey-3bf1`, based on main `dac527b386c268caa96d9388d0c11d206b4f6856`.

## Reading

Entry files read for this task: `AGENTS.md`, `product.md`, `handoff.md`, `decision-log.md` (latest decisions through the PR5 merge), `research/personal-agent-research-index.md`, `desk-companion/docs/pr5-integration.md`. `desk-companion/docs/integration-acceptance.md` is not on main; it was read from open PR #78. Mailbox shape was read from open PR #79 and not copied into mailbox files.

Implementation reading covered `tasks.py`, `schemas.py`, `calendar.py` conflict expansion, `store.py` operations, `assistant.py` propose/decide, `assistant_routes.py`, `permissions.py`, `notify.py`, `app.py`, `runtime.py`, and `exchange.py` export fields. This closeout re-read the conflict-pair return in `offline_calendar/service.py`, the proposal confirm branch, fixture README, and the sections edited below.

Not read as full files this closeout: historical research reports, Pi docs, Codex Work UI, mailbox package, shopping package.

## Scope

New package `desk-companion/backend/desk/offline_calendar/` plus fixtures and `tests/test_offline_calendar_journey.py`. Wiring only in `app.py`, `runtime.py`, `assistant.py`, and `assistant_routes.py`. No mailbox, shopping, Pi, Google/Outlook client, or backup code change.

## Checks

```text
cd desk-companion
uv run --no-sync ruff check backend/desk/offline_calendar backend/desk/assistant.py backend/desk/assistant_routes.py backend/desk/app.py backend/desk/runtime.py tests/test_offline_calendar_journey.py
uv run --no-sync pytest tests/test_offline_calendar_journey.py -q --tb=short
```

Result after the conflict-pair transaction change: ruff clean; 11 passed, 1 pre-existing Starlette/httpx warning, 6.58s.

Adjacent regression, same interpreter:

```text
uv run --no-sync pytest tests/test_calendar.py tests/test_tasks.py tests/test_notify.py tests/test_assistant_data.py tests/test_permissions.py tests/test_exchange.py -q --tb=line
```

104 passed, same warning, 26.93s.

The 11 tests: out-of-order duplicate and field preservation, restart, in-fixture revoke, endpoint revoke, disconnect, stale revision, status cancel, owner confirm/read-back, invalid fixture, quiet hours, runtime isolation.

No GitHub Actions run. No paid model call. No live calendar request.

## Docs updated

`desk-companion/docs/offline-calendar-journey.md`, `modules.md`, `software-maintenance.md`, `pr5-integration.md`, `product.md`, `research/personal-agent-research-index.md`, `decision-log.md`, `handoff.md`, `work-log.md`, this file.

## Gap

Portable JSON export was not extended. Cursor tables exist only in the SQLite file. Full backend/frontend suites were not re-run; the new HTTP journey file is the verification for this slice.
