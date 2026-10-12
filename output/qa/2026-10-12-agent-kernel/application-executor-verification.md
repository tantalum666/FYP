# Bounded application executor verification

2026-10-12 UTC · Group 2 · Additive local implementation and isolated HTTP verification. Source baseline: `50e174f50a4130b3c666f836f666f6aa4cde4b32`. This report covers the executor worker only, not other simultaneous integration work.

## Delivered

- `backend/desk/executor_registry.py`: code-owned action routing and adapter-specific receipt validation; no model-supplied registrations or destinations
- `backend/desk/application_executor.py`: default-off fixed application API adapter, exact canonical `http://127.0.0.1:<1024–65535>`, no redirects or ambient proxy, bounded responses/timeouts, persistent application identity and exact content/title/intent binding
- `backend/desk/demo_application.py`: independent loopback-only CLI service, separate SQLite database, immutable generated-ID records, GET readback and escaped read-only HTML; no delete/update/shell/GUI endpoint
- `backend/desk/jobs.py`: additive `create_record` / `verify_record`, exact approval and persisted-intent validation, registry dispatch; existing lifecycle, note executor seam and strict note receipts retained
- `scripts/check_application_executor.py`, `tests/test_application_jobs.py`, and updated `docs/computer-jobs.md`

`computer.py` itself and original note tests were not changed. The application adapter remains unavailable without explicit operator origin configuration and the existing computer feature switch. A `.json` artifact is an application record identifier, not a host file path. This is API-controlled application execution; no arbitrary PC or browser automation claim is made.

## Actual checks

- [Targeted pytest output](application-executor-tests.log): **86 passed**, comprising 34 existing note cases and 52 new application/privacy cases; 13.22 seconds, one existing Starlette/httpx deprecation warning
- Ruff passed on all six implementation/test/runner files; formatter applied
- Real HTTP integration fixtures run actual Uvicorn listening sockets and inspect independent SQLite records, rather than relying only on fake HTTP responses
- [Standalone process evidence](application-http-integration.json): separate application process on port18840; zero records before owner approval, one 79-byte Unicode record afterward, independent SQLite and HTML readback, exact content/title/approved-intent hashes, repeated preparation still one record, test-owned subprocess stopped and temporary runtime removed
- No dependencies or lockfiles changed by this worker. No paid provider calls, credentials configured, browser clicks, user-computer actions, hardware operations, original data changes, commit, push or merge performed

Tests cover no approval/no effect; disabled adapter; exact target rejection; model target/path/script denial; lost receipt and restart with GET-only recovery; process crash after committed write; stale approval scope and changed persisted intent; expiry; cancellation immediately before dispatch versus after real commit; text injection as inert content and escaped HTML; read-only verification after tampering; cross-adapter source refusal; duplicate/conflicting IDs; changed application instance; foreign Host/Origin; hidden owner metadata-only job listing/detail and blocked prepare/approve while cancellation remains available; no redirect/proxy; body size bounds; and 13 forged receipt-field variants.

## Boundaries

The demo app is a single-host fictional-data test surface, not a production authenticated application. Host/Origin/header checks do not defend against another malicious process on the same host. Its CLI binds only IPv4 loopback. There are no new external accounts or permissions.

The client never retries a dispatched POST. A timeout/error can occur after commit, so it remains unknown until a separate read establishes the result. Cancel cannot retract an HTTP request already sent; verified late success is reported truthfully alongside the cancellation request. Application identity is pinned in the owner-reviewed intent and checked before dispatch; its endpoint also rejects a mismatched instance. The worker does not infer completion of a linked task.

This worker's evidence does not establish integrated frontend/browser usability, current full-suite success, real provider quality/cost, Pi deployment, real Mac control, target hardware behavior or CI. The parent owns integrated UI and final checks. The application database and note/job history are still outside the business JSON backup; capacity/archive policy remains existing prototype scope.

## Reading and documentation

Parent-requested privacy fix was added before the first snapshot: list/detail consult personal-context visibility, preparation/approval require visible owner context, and cancellation/reconciliation remain metadata-only. The two owner-route tests exercise both notes and application records and reveal the same preserved intent only after explicit unhide.

Read gate was cleared by the parent before implementation. [Research/history ledger](grok-research-reading-ledger.json) and [QA ledger](grok-qa-reading-ledger.json) record this worker's full-body assigned reads and exact EOF ranges, including all 38 authored historical QA documents plus the new baseline audit. Updated computer-job contract was read back fully after editing; this report is read back and included in the supplement ledger. Historical QA and the public Grok research are not user authorizations or claims of proprietary implementation access.
