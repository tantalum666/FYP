# Independent selected-task responsibility audit

Date: 2026-10-13. Scope: real cloud-local SQLite, FastAPI TestClient HTTP, actual deterministic Markdown/CSV files. Synthetic data only; no providers, external services, live credentials, hardware, desktop operations or Git publication. Source code was not changed by this auditor.

## Findings sent for correction

1. **Final response privacy epoch (reproduced):** after detail projection, set hide-private true and then false in committed settings transactions before `_reply`. The initial implementation rechecked only the final Boolean, returning the pre-revocation private projection. Reproduction: `test_final_reply_rejects_hide_then_show_epoch_change`. Required correction: capture and revalidate privacy/settings epoch for private reads and mutation replay responses.
2. **Expired pending delivery (reproduced):** create a review, pass expiry, advance. The initial implementation set status expired but left pending_count=1. Its terminal action guard prevents pause/cancel. Root confirmed that expiry must dismiss/version the retained pending review, leaving it inspectable. Reproduction: `test_expiry_dismisses_existing_pending`.

## Verified before corrections

Initial complete run: 19 passed, 2 above regressions failed. An earlier test harness error referred to a nonexistent `current_revision`; corrected to the actual `revision()` API before interpreting product results. Extended selective run: 26 passed, 3 deselected (10,000 ticks already passed; two reported regressions awaiting fixes). Injected evaluation savepoint rollback and nondecreasing daily watermark: 2 passed separately.

Coverage includes exact source projection, no initial reviews, 10,000 unchanged ticks without revision change, irrelevant/task scheduling edits, A→B→A coalescing, transaction-coupled dirty rollback, source operation replay, concurrent workers and enrollment, pending/versioned acknowledgment, restart, pause/cancel fences and operation-budget reserves, daily/lifetime quotas, clock rollback, missing-source block-once, genuine owner session checks, actual approved controller/display denial through HTTP, final logout/hide recheck, hidden response redaction, hash collisions, background comparisons after logout, no implicit AgentRun, stale Work scope denial, explicit current-data Work, unchanged original tasks, and independently read actual Markdown/CSV bytes and hashes.

Runtime worker wiring and browser/UI interactions are outside this auditor's checks. Root is independently checking worker integration; frontend worker/auditor owns actual UI behavior. The backend handoff test does not establish browser clicks or a global exactly-one run-per-review guarantee.

## Reproduction

From repository root:

    PYTHONPATH=desk-companion/backend desk-companion/.venv/bin/python -m pytest -q output/qa/2026-10-13-task-watch-authority-audit/test_independent.py

## Final verification

Both findings were corrected by the implementation worker and independently retested. All **31 tests pass** in 17.02 seconds; see `pytest-final.txt`. The final scope includes the injected post-write evaluation failure rollback, daily watermark rollback/restart, and genuine paired controller/display HTTP denial. Ruff passes for the independent test file. No unresolved backend blocker was found within this audit scope.

One FastAPI/Starlette test-client deprecation warning remains; this is not a functional failure. No live UI/browser result is claimed. Final source fingerprints are recorded in `verified-files.json`. Root owns product, handoff, work log and shared capability-contract updates.
