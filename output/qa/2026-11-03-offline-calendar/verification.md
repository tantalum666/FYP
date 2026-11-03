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

104 passed, same warning, 26.93s. That run was before the quiet-hold and backup changes.

## Quiet hold and portable backup

Same ruff command, plus:

```text
uv run --no-sync pytest tests/test_offline_calendar_journey.py tests/test_backup_persona_jobs.py tests/test_exchange.py -q --tb=short
uv run --no-sync pytest tests/test_integration_boundaries.py tests/test_memory_gaps.py tests/test_risk_gaps.py tests/test_tasks.py tests/test_backup_persona_jobs.py -q --tb=line
```

Ruff clean. First command 17 passed, 8.84s. Second command 51 passed, 12.47s. The journey file now covers a quiet-hour hold that survives a second process, is restored, and is published once by `Runtime.tick`, plus backup → restore → sync that keeps both task ids. Display export, preview, and apply return 403. A tampered cursor is `INVALID_BACKUP`. A backup without `offline_calendar_bundle` still previews.

No GitHub Actions run. No paid model call. No live calendar request.

## Docs updated

`desk-companion/docs/offline-calendar-journey.md`, `modules.md`, `software-maintenance.md`, `pr5-integration.md`, `product.md`, `research/personal-agent-research-index.md`, `decision-log.md`, `handoff.md`, `work-log.md`, this file.

## Gap

Full backend and frontend suites were not re-run. This slice still does not connect a live calendar account. The two earlier gaps, dropped quiet-hour notices and missing portable cursor state, are covered by the checks above.
