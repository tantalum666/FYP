# Offline mailbox journey verification

3 November 2026. Slice: authorized-mailbox journey on offline fixtures only. Branch `cursor/mailbox-offline-journey-9739` from main `dac527b386c268caa96d9388d0c11d206b4f6856`. No Gmail, Outlook, credential, paid model, or GitHub Actions run.

## Reading scope

Read in full for this task: `AGENTS.md` (workspace rule), `handoff.md`, `desk-companion/docs/pr5-integration.md`, `desk-companion/docs/mailbox-journey.md` (written this slice), `desk-companion/fixtures/mailbox/README.md`.

Read the current-task sections, not every historical markdown: `product.md` opening requirements and the personal-agent bullet; `decision-log.md` entries through 2026-10-31; `research/personal-agent-research-index.md` §4 gap table and §5 (mail → task → advice); `desk-companion/docs/task-tracking.md`, `software-maintenance.md`, `modules.md` mailbox-related rows.

Implementation surfaces actually inspected: `backend/desk/tasks.py` (create, action, listing), `assistant.py` propose/decide, `assistant_routes.py`, `permissions.py` (`SOFTWARE_PROPOSALS`), `store.py` connection and `operation`, `runtime.py`, `app.py` owner/session routes, `notify.py`, `workspace_data` quiet hours, `agent_runs.py` proposal visibility, `google_calendar.py` as the existing connector pattern, and the HTTP shapes in `tests/test_tasks.py`, `tests/test_notify.py`, `tests/test_goals.py`. This record is the file list, not a claim that every line of those modules was reread after the implementation settled.

## Scope chosen

Reuse `TaskService`, `AssistantService`, and `Notifier`. The tracked Work item is the existing task id. New tables (`mailbox_connections`, `mailbox_threads`, `mailbox_messages`, `mailbox_attempts`) are created with `CREATE TABLE IF NOT EXISTS` on the same store and use `BEGIN IMMEDIATE`. Schema version stays 3. No `agent_runs` row, no frontend Work UI, no portable JSON import of mailbox rows.

## Checks

| Check | Command | Result |
|---|---|---|
| Mailbox HTTP journey | `cd desk-companion && PYTHONPATH=/tmp/desk-py python3 -m pytest tests/test_mailbox_journey.py -q --tb=line` | **8 passed** (3.88s on the closeout rerun). Covers duplicate, out-of-order, replayed operation id, owner note preserved, restart, revoke, disconnect, draft owner confirm/cancel, display 403, invalid fixture rejected before insert, quiet hours. |
| Ruff on touched Python | `python3 -m ruff check` on `mailbox.py`, `mailbox_fixture.py`, `assistant.py`, `assistant_routes.py`, `runtime.py`, `app.py`, `exchange.py`, `tests/test_mailbox_journey.py` | All checks passed on the closeout rerun, and again after the quiet-hold and backup changes. |
| Quiet retry and backup roundtrip | `python3 -m pytest tests/test_mailbox_journey.py -q --tb=short` | **9 passed** (5.30s). Adds quiet hold until `Runtime.tick`, restore of that hold, and backup → restore → list → replay → next sync without a second task. |
| Existing backup and notice paths | `python3 -m pytest tests/test_exchange.py tests/test_backup_persona_jobs.py tests/test_memory_gaps.py tests/test_risk_gaps.py tests/test_tasks.py tests/test_integration_boundaries.py tests/test_notify.py tests/test_nudges.py -q --tb=line` | **64 passed** (15.58s). |
| Full backend | `PYTHONPATH=/tmp/desk-py python3 -m pytest -q` from `desk-companion` | After the same wheels were installed into `/usr/local/lib/python3.12/dist-packages` (subprocess tests use `python -I` and drop `PYTHONPATH`): **1693 passed, 1 failed**. Failure: `tests/test_public_capture_transport.py::test_public_unicast[::ffff:93.184.216.34]`. `ipaddress.IPv6Address("::ffff:93.184.216.34").is_reserved` is true on this interpreter, so `is_public_unicast` returns false before the mapped-v4 check. That file was not edited. |

Dependencies used only to run tests on this VM: fastapi, uvicorn, python-dateutil, pwdlib[argon2], httpx, websockets, icalendar, recurring-ical-events, cryptography, python-socks, pytest, ruff. They are not committed.

## Updated docs

`product.md`, `research/personal-agent-research-index.md` (mail gap rows), `desk-companion/docs/pr5-integration.md`, `modules.md`, `software-maintenance.md`, new `docs/mailbox-journey.md`, `handoff.md`, `decision-log.md`, `work-log.md`, this file.

## Publication

Pull request: https://github.com/tantalum666/FYP/pull/79 on `cursor/mailbox-offline-journey-9739`. Open, not merged. The implementation commit is `7c016960b5c773d82db52d96231dd7a39a3fda28`; this note is a later documentation commit on the same branch.

## Not claimed

Real mailbox acceptance, send, live push, or a fix for the IPv6-mapped unicast case. Quiet-hour redelivery and portable mailbox backup are covered by the 3 November follow-up on the same branch. Confirming a draft still uses the existing task note action, which clears `check_in_local`.
