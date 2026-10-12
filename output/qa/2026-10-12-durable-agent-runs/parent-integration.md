# Parent integration checks — 12 October 2026

Status: frozen software integration passed. This record is not publication or live browser acceptance.

Runtime constructs SourceService, ArtifactService, AgentRunService and BrowserService after their existing dependencies. The application mounts their owner-only routes, schedules agent runs and browser jobs separately, and sets shutdown fences before cancelling worker tasks.

AssistantPanel has compact Work tasks and Browser workflow entries. Work-task review returns to the existing proposal component. The callback waits for a fresh privacy/identity-fenced proposal list, then focuses the matching article after modal dismissal. An already handled/expired/missing proposal shows a clear notice instead of silently losing navigation. Hidden-mode run pause/cancel is currently API-only; the run UI requires revealing private context again. Hiding does not roll back already-issued requests.

The shared assistant proposal routes now attach the real owner session and use run-origin classification to filter listings and guard decisions. The classification comes from durable effect intents reserved before child draft creation, so a crash before parent linking cannot expose the draft to paired controllers. Unrelated legacy proposal behavior is preserved; controller, hidden-owner, orphan-draft and receipt-collision regressions passed in the independent review.

Executed checks:

- `tests/test_workspace_api.py tests/test_software_checks.py`: 9 passed after both service integrations
- `tests/test_agent_integration.py`: 1 passed using actual authenticated HTTP routes, SQLite and filesystem
- Parent integration Ruff check and TypeScript check passed

The integration test checks unauthenticated denial, owner login, actual CSV upload, scope selection, deterministic work execution, two generated outputs, independently recomputed downloaded byte digests, attachment headers, disabled browser capability, logout denial and lifespan shutdown flags. No model, external browser or hardware is used. Scripted/model quality acceptance is separate. The authoritative frozen aggregate check completed with 500 backend tests, 75 frontend tests, Ruff, TypeScript/Vite and original A1/VRM asset hashes passing. See final-software-checks.log. All 186 recorded source/lock/test hashes remained unchanged through the final check; see final-software-source-hashes.json. Existing Vite large-chunk and Starlette deprecation warnings are retained, not treated as failures.

The existing Mac acceptance task failed twice with upstream file-download HTTP 503. A fresh text-only replacement task was admitted using the same isolated workspace and GPT-6.1 Sol Max. No browser result is inferred from task admission; original preview port 8832 remains outside its scope.
