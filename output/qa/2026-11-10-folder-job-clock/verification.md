# Folder-job restart clock

10 November 2026. Local only. No paid model call, no GitHub Actions run, no Pi change.

## Reading

- `AGENTS.md` in full.
- `handoff.md` in full, and `product.md` through the current requirements and the 7 November evidence.
- `decision-log.md`: header and the 6–7 November entries. Earlier history was not reread.
- `desk-companion/tests/test_folder_jobs.py` in full.
- `desk-companion/backend/desk/jobs.py`: prepare, approve, `expire`, and `run_one`.
- `desk-companion/backend/desk/app.py` `create_app` clock argument, and `Store.clock` defaulting to `datetime.now(UTC)`.
- `desk-companion/backend/desk/computer.py` `FolderDropExecutor`. It does not read a clock.
- Restart helpers in `test_computer_jobs.py`, `test_shopping_fixtures.py`, and the offline journey helpers, plus a scan of test functions that both inject a clock and construct another app or store.
- `desk-companion/docs/computer-jobs.md` deadline section.
- `is_public_unicast` only far enough to see why the mapped-address test fails. That behavior was not changed.

## Cause

The folder fixture freezes the clock at 2026-11-07 00:00 UTC so a host clock jump cannot expire the five-minute review during HTTP login. Approval then stores a deadline of that instant plus 60 seconds. `test_restart_runs_only_the_approved_folder_job` opened the same database with a new `create_app` and no `clock`. `Store` therefore used the wall clock. `JobService.expire` compared the stored deadline with that wall clock and marked the queued job `expired` once the real date passed 2026-11-07 00:01 UTC.

Inside one process, prepare, approve, expiry and execution already use `store.clock`. The folder executor does not call `datetime.now`. The second clock existed only because the restart test omitted the injected clock.

## Change

The restarted app receives `clock=app.state.store.clock`. The fixture comment records that a later process on this store must keep that clock. The computer-job deadline note now says the same. No production expiry window changed.

A scan of tests found no other function that reopens the same clocked store without passing the clock. `test_local_rule_prepares_a_review_and_does_not_write` builds an empty app in another directory. Shopping, calendar and note restarts already pass their clock.

`test_public_unicast[::ffff:93.184.216.34]` still fails on Python 3.12.3: `IPv6Address.is_reserved` is true for `::ffff:0:0/96` even when the embedded `93.184.216.34` is public, so the mapped-address recursion never runs. Left as requested.

## Checks

From `desk-companion/`:

- `uv run --no-sync pytest tests/test_folder_jobs.py -q`: 11 passed.
- `uv run --no-sync ruff check tests/test_folder_jobs.py`: passed.
- Future date: `LD_PRELOAD=/usr/lib/x86_64-linux-gnu/faketime/libfaketime.so.1 FAKETIME='2035-06-01 00:00:00' uv run pytest tests/test_folder_jobs.py tests/test_computer_jobs.py -q`. `date -u` and `datetime.now(UTC)` both reported 2035-06-01 00:00:00 UTC. 50 passed. freezegun was not used: it replaces the `datetime` class and breaks pydantic on this environment. libfaketime changes the system clock the same way a future host date would, including `datetime.now`.
- A throwaway script that still omits `clock` on the restarted app got `expired` against the real current date. The same script with the shared clock, under the 2035 faketime, got `succeeded`.

Backend suite, `uv run --no-sync python -m pytest -q` (`python -m` so `scripts` imports resolve; the documented `uv run pytest` console script does not put the project root on `sys.path` under pytest 9):

- First run, before frontend packages: 2034 passed, 2 failed, 411.41s. Failures were the mapped unicast test and `test_interrupted_assistant_stream_recovers_once_through_sse`, the latter because `@capacitor/core` was not installed.
- After `npm ci` in `frontend/`, that stream test passed on its own.
- Clean full run with those packages installed: 2035 passed, 1 failed, 415.22s. The only failure is `test_public_unicast[::ffff:93.184.216.34]`.

No GitHub Actions workflow was added or triggered.
