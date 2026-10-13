# Exact URL capture lifecycle and source adapter QA

13 October 2026. Same ongoing 186-document project intake; see `reading.json` for
inherited evidence and focused reads. This worker owned the lifecycle, minimal
source/file/accounting helpers, focused tests and `docs/public-captures.md` only.
The coordinator owns shared product/handoff/decision/work logs, runtime/routes
mounting and Git publication. Schema, policy, transport and UI have separate owners.

## Implemented

- Durable local retained review, exact intent/owner/privacy-bound approval, one
  physical worker, conservative dispatch marker and no retry/restart replay
- 200 lifetime captures / 600 successful operation receipts; original-key lookup
  precedes new admission, unsupported keys fail before persistence
- Bounded SQL projections for private/scalar metadata, receipts, source identity
  and authority; hidden stop never deserializes private intent/acquisition JSON
- Acquisition-before-publication and returned-source-ID-after-publication through
  the existing immutable writer, with transaction-aware source-only accounting
- Exact-key canonical source identity, no quota double charge, no nested database
  connection in write checkpoints, readback-only recovery independent of new quota
- Post-link cancellation fences independent verification both before I/O and at
  status commit; retained bytes remain unknown until an authorized later readback
- Current-response session/privacy recheck, canonical UTC dual-clock rollback
  checks, shutdown cleanup in finally and worker-control failure disabling

## Executed local evidence

Focused lifecycle tests and existing artifact/capacity/Work regressions run with
`.venv/bin/pytest -q tests/test_public_captures.py tests/test_artifacts.py tests/test_work_capacity.py tests/test_agent_runs.py`.
Final frozen-candidate run: **196 passed** (48 lifecycle cases plus 148 existing artifact/capacity/Work cases), with one existing FastAPI/Starlette deprecation warning. The final console log is `tests.txt`; source hashes are `source-manifest.json`.
Ruff passes for the four changed backend files and the new lifecycle test file.

The lifecycle matrix includes exact duplicate/collision ordering, concurrent
approval, hidden corrupt and oversized metadata, owner/session/epoch/expiry and
rollback, restart, 200/600 limits, blocked worker, shutdown/database failure,
source-slot races, same-operation recovery with unrelated corrupt accounting,
source identity corruption including boolean/integer canonical distinctions,
temporary-only, link-count-two, single-link final, post-link cancellation and
post-read/pre-verification cancellation. No failure test manufactures a replacement
source, repairs a temporary file or triggers another GET.

One independently observed loopback HTTP fixture uses the production capture
client with a test-only connection injection. It records one GET `/doc`, original
Host and fixed headers; validates exact raw/extracted hashes and source bytes;
explicitly selects the source in ordinary deterministic Work; and independently
reads/downloads/hashes both generated Markdown/CSV artifacts. No model call occurs.
The loopback fixture does not exercise real public DNS/TLS or weaken production
address admission.

## Independent review corrections

The separate audit exposed and this worker fixed:

1. Source metadata and operation receipts were initially bounded only after
   materialization; SQL CASE now bounds all projected values before Python
2. Python equality allowed `True == 1` in otherwise equivalent metadata; actual
   and expected canonical request digests must both match the stored receipt
3. Cancellation immediately after linking could previously let the shared writer
   automatically promote the source; final readback/status now uses the checkpoint
4. Forged verified lifecycle without acquisition/source/approval was rejected
5. Unicode-over-byte-limit/NUL operation keys were previously accepted before
   projection rejected them; admission now rejects unsupported keys before writes
6. Corrupt settings-version/personal-epoch values are now SQL-bounded scalars

The coordinator separately caught the production client import path and requested
canonical wall-clock rollback and robust worker/shutdown control; both are covered.
Independent audit separately reported **40 lifecycle audit + 16 runtime wiring checks passed**, with eleven inspected source hashes unchanged. Evidence remains under its own QA directory and is not claimed as this worker's test run.

## Boundaries

Only fictional fixtures, temporary SQLite/files and an isolated loopback server
were used. No actual public site, credential, paid model, user runtime migration,
network setting, browser fallback, hardware or live account was touched. No Git
operation was performed by this worker. Real mounted UI, browser-saved output,
public-DNS/TLS and model-quality acceptance remain separate. A1, DeviceApp, artwork,
school files and original runtime data were outside this worker's edits.
