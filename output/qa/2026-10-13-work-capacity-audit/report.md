# Independent retained-capacity audit

Status: passed after two independently identified fixes. 2026-10-13 08:05 UTC.

## Scope and reading

Inherited the same ongoing round's 186-document full intake, as directed by the parent; no new independent project-intake claim. Focused rereads: AGENTS.md (complete), product.md (204 lines, full with overlap reads for the initially truncated segment), handoff.md (54 lines, complete), relevant latest decision-log entries through task-change responsibilities, and output/qa/2026-10-13-work-capacity-design/contract.md (104 lines, complete). Read capacity service/limits and touched admission/list/search paths, Store.connection, owner gate, implementation tests and frontend contracts. Source changes were owned by implementers; this reviewer wrote only this audit directory. No Git, Mac, live provider, network service, dependency or credential operations.

## Finding corrected

SQLite accepts a literal NUL after an otherwise valid JSON object as end-of-input. Reproduction with the environment's SQLite: json_valid('{"byte_count":1}\0garbage') returned 1 and json_extract returned 1; Python's admission decoder rejects that metadata. Original capacity projection consequently advertised known bytes for invalid retained metadata; an analogous malformed privacy settings object also passed projection. Reported to backend implementer, who inserted literal-NUL rejection before JSON parsing in the shared guarded scalar projection and added production regressions. Independent tests now cover both metadata and privacy settings.

## Backend execution

- Independent suite: 20 passed in 8.53s, backend-first.log (run occurred after fix landed)
- Independent + implementation suite: 80 passed in 21.37s, backend-combined.log; only existing Starlette/httpx deprecation warning
- Exact audited source hashes: backend-source.sha256
- Command from repository root: PYTHONPATH=desk-companion/backend:desk-companion/tests desk-companion/.venv/bin/python -m pytest -q desk-companion/tests/test_work_capacity.py output/qa/2026-10-13-work-capacity-audit/test_independent_capacity.py

The independent suite executes real isolated SQLite and checks duplicate/escaped byte_count keys; boolean/large string/large number metadata; UTF-8 metadata bounds at 65,535/65,536/65,537 bytes; scalar-only result materialization and cap+1 row limits; fresh settings-version/personal-epoch/session-revocation denial; corrupt settings fail-closed. The combined production suite additionally exercises all-resource cap+1, terminal and reserved accounting, exact byte fullness, actual owner and paired denial, concurrent snapshot consistency, query-only/no file/reconcile/service reads, no database mutation, shared constants/list wrappers, concurrent admission, original-key recovery at full count/bytes, retained superseded/unlinked per-run outputs, response no-store and origin protection.

Source review confirms query-only consistent read transaction and fresh final authority transaction. Default contract is global aggregates only; per-run values are limits. No construction tables/files/workers; only scalar projections reach application code. Existing admission still finds original (kind, operation_key) before quota scans; cancelled/unknown/superseded rows remain retained. Constants preserve source 1MiB/100/64MiB, artifact256KiB/400/64MiB and per-run4/1MiB, runs100, watches20. Source/artifact page defaults50/max100, search page default20/max50 and corpus600 remain unchanged.

A brief execution-transport disconnect occurred before the first audit write/test process was created. That failed call produced no test result and is not counted; confirmed execution resumed and all listed checks completed.

## Frontend

Independent production-hook/callback/React-SSR audit: 33/33 passed, recorded in frontend/results.json with exact source hashes; runnable harness frontend/audit.mjs. Source hooks/components are executed through a custom React hook runner and transport fixtures, with actual React SSR for copy/render. No browser DOM or physical device/layout acceptance is claimed.

A second actionable issue was reproduced and fixed: capacity denial invalidated the shared fence and masked views, but already-captured RunDetail proposal/browser/connector review callbacks could still invoke parent navigation because RunWorkspace go/commit only checked captured freshness. The UI implementer added fence.accepts(epoch) at both dispatch boundaries. The independent failing case now passes and verifies all three stale linked-review callbacks are inert after denial.

The final UI matrix covers ordinary failure isolation versus shared access-denial invalidation (including reordered same-epoch denial), identity/privacy/offline/stale/A-B-A late-response fences, no new timer/provider request, explicit refresh without scope/draft/retention reset, unknown values without zero fallback, collapsed bilingual readable summary, per-run limits clearly not usage, actual same-operation retry after unknown mutation, voice-origin/expiry recovery, full-capacity pause/cancel/upload/preview/download and hidden watch saved-count/cancel behavior. See frontend/report.md for complete procedure and limitations.

### Additional admission parity checks

Independently inspected and executed the implementer's subsequently added test_work_capacity_admission.py: 9 passed. Full retained-run original-key recovery/cancel and full watch original-key recovery/cancel keep capacity occupied, strict read-only connection rejects accidental SQL writes, and provider/network seams remain unused. All eight recorded source hashes rechecked unchanged before execution. See backend-admission.log. Total distinct capacity/backend audit cases executed: 89 (69 implementation + 20 independent).
