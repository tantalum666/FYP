# Group 2 · Selected task-change backend verification

Date: 2026-10-13. Completed owned backend/tests/documentation; frontend and full
aggregate acceptance are coordinated separately by the parent. No Git,
network/provider, credential, browser, hardware or original-asset operation was
performed by this worker.

## Owned implementation

- `desk-companion/backend/desk/responsibilities.py`
- `desk-companion/tests/test_responsibilities.py`
- `desk-companion/docs/responsibilities.md`

Parent owns Runtime/app integration, independent worker-loop tests and shared
project documentation. Frontend owner owns the bilingual panel/hook/types and
explicit Work-composer prefill. Backend source/test/doc fingerprints are recorded
in `frozen-evidence.json`; the source was explicitly frozen before final parent
aggregate execution.

The same ongoing 186-document intake was inherited. Focused current contract
rereads and identity fingerprints are in `reading.json`; this does not claim a
new independent complete repository reading. Handoff/product, source-change
design, routine/task/run/privacy/source contracts and relevant implementation
were read. Automatically generated QA snapshots, dependencies, caches and Git
internals were excluded from the project-Markdown intake.

## Checks and actual outcomes

Command, from `desk-companion`:

`.venv/bin/python -m pytest tests/test_responsibilities.py tests/test_responsibility_worker.py tests/test_tasks.py tests/test_routines.py tests/test_agent_runs.py tests/test_personal_context.py tests/test_artifacts.py -q --disable-warnings`

Result: **203 passed, 1 warning in 64.04 seconds**. Full output is retained in
`regression.txt`. The focused file contains 47 passing cases; the parent worker
file contains two actual application-lifespan tests. Ruff on owned Python source
and tests passed (`ruff.txt`). Links in `docs/responsibilities.md` were checked
against actual local files and passed.

Focused evidence includes:

- 10,000 unchanged advances with a forbidden source-projector/AgentRun-create
  stub: no task projection, review, artifact, AgentRun or workspace revision
- Exact selected scope, unrelated/new task exclusion, same-value/title/scheduler
  quiet changes, all six projections and authoritative task status
- Real transactional source rollback and task-note inserts/deletes, concurrent
  evaluators, enrollment/edit serialization and pause/evaluation fencing
- Stable coalesced ID, review version rejection, explicit acknowledgment,
  restart/dedupe and historical receipt pruning without baseline/budget reset
- UTC daily reservation, metadata-only budget waiting, clock rollback, last
  budgeted pending review coalescence and terminal lifetime exhaustion
- Pause/resume-baseline/cancel/expiry, missing or corrupt source blocking and
  explicit recheck, per-definition capacity and reserved final stop controls
- Real-session HTTP, CSRF/origin infrastructure, hidden metadata/stop controls,
  post-logout comparison without owner impersonation, and fresh final authority
- Four hide→show epoch tests (scope/list/detail/create replay), plus retained
  expired history with no pending delivery
- Deliberately injected evaluation failure after writes: savepoint rollback leaves
  no partial review reservation or consumed baseline, then records one safe block
- Explicit owner-started deterministic Work after a review: actual Markdown/CSV
  download bytes rehashed, CSV parsed, source title found in Markdown, no automatic
  run creation and watched task remains open

An independent read-only auditor ran 31 additional probes and reported all passed
at `../2026-10-13-task-watch-authority-audit/`. That audit initially found a
hide→show response race; the final service captures the settings version in the
initial transaction and checks it again in a fresh final transaction. Expiry was
also clarified to dismiss pending delivery while preserving historical receipts.
The final owned suite includes both regressions. No unresolved backend blocker
was reported by that audit.

## Deliberate simplifications and limits

This is selected local task comparison, not a generic event journal/scheduler or
semantic agent. The mailbox has one row per explicitly enrolled task, hashes
rather than retained before/after text, and one pending review per definition.
No calendar/file/provider integration, automatic AgentRun or direct linked-child
run endpoint is added. Full Work remains an explicit owner choice with fresh
scope and separate retention acknowledgment. No test claims that the review
proves a person saw a card or that local file downloads were saved by a browser.

Terminal definitions count against the total cap and never silently renew or
reset. Ordinary operation receipts are bounded, with independent final pause and
cancel reserves. Current UI clears old private queues on epoch changes, even
though the service protocol can recover an original key under fresh authority;
the documented UI recovery is to reopen current history before repeating.

No live model, actual browser interaction, remote account, microphone, physical
posture/hardware or target Pi test is claimed. The parent owns final aggregate
and publication evidence, which must not be inferred from this focused result.
