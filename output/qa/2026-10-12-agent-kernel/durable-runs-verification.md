# Group 2 | Durable-run implementation verification

Date: 12 October 2026. Status: **owned source frozen for parent aggregate and publication**. Parent-reported first published kernel checkpoint: `546734273c9c8305cf6226e96a8e07854ba5c0b1`; this report does not claim the new run files have been pushed. Exact current file bytes are pinned in [owned-file manifest](durable-runs-owned-files.json).

## Delivered slice

- Additive strict run schemas, persistent run/step/event/attempt/intent state and one bounded worker
- Real owner-session-hash authority, selected immutable source and task/calendar scope, exact provider consent, late-result generation fences and owner/private run proposal guards
- Deterministic local evidence compilation, bounded exact admitted decimal CSV sums, actual source-linked Markdown and CSV artifacts through the independent artifact service
- Configured-model protocol supports persisted plan/read or batch-read/ask/report/propose/finish decisions, accumulated observations, owner answers and continuation after independently verified review outcomes
- Explicit pause/resume/cancel/steer and uncertain provider retry, interrupted-call reservation, saved returned-decision recovery, canonical matching child-intent recovery, independent saved-record verification
- Required output/evidence/coverage/section/effect manifest; unread or partially transmitted inputs and rejected required effects cannot be converted into success by a model message
- Shared text response transport is bounded before JSON parsing and does not retry paid attempts

The service's actual contract and limits are [agent-runs.md](../../../desk-companion/docs/agent-runs.md). The broader [design](../../../planning/2026-10-12/durable-agent-run-design.md) now points to this delivered subset instead of implying all roadmap items are implemented.

## Owned files and integration

Owned new files: `agent_run_schemas.py`, `agent_runs.py`, `agent_planner.py`, `agent_tools.py`, `test_agent_runs.py`, `test_text_response_bounds.py`, and `docs/agent-runs.md`.

Narrow shared-file edit: `text_ai.py` transport response reading only. Updated focused documents: `docs/provider-policy.md` and the durable-run design. The ten-file hash manifest includes these final exact files.

Parent owns Runtime/app service and worker integration, shutdown sequencing, route mounting and the legacy assistant route's narrow run-origin filter/confirmation guard. Source/artifact services and frontend are separate workers' changes; their independent reports remain authoritative for their internals. The source contract used here was fully read through EOF, recorded in the [supplementary reading ledger](reading-durable-runs-supplement.json).

## Final owned/affected checks

1. `pytest -q tests/test_agent_runs.py tests/test_text_response_bounds.py tests/test_provider_policy.py`: **130 passed**, one upstream Starlette/httpx deprecation warning. Includes **38 run tests**, **13 text transport tests**, and 79 existing provider-policy cases. [Exact log](durable-runs-tests.txt)
2. `pytest -q tests/test_tasks.py tests/test_personal_context.py tests/test_agent_runs.py tests/test_text_response_bounds.py`: **88 passed**, same upstream warning. This includes existing provider generation, reply caching, consent and background task behavior. [Exact log](durable-runs-affected-tests.txt)
3. Ruff checks over owned run code, shared `text_ai.py` and both new test files: **passed**
4. All relative links in the three owned/updated Markdown documents resolve. Supplementary full-read evidence is recorded separately
5. Independent reviewer reported **5/5** final matching-intent/collision/auth checks passing on unchanged source hashes and no remaining reproduced blocker

Parent is running the authoritative whole-tree backend/frontend/lint/type/build aggregate after all workers freeze. Do not add overlapping focused test totals together or label these checks a final complete-project pass.

## Meaningful actual outcomes tested

- Uploaded selected source -> production run service -> real immutable Markdown/CSV files -> authenticated download -> independent SHA-256 comparison
- Real SQLite task draft remains unsaved until review, then continuation rereads the actual saved task/version/evidence
- Real calendar creation is verified against requested canonical fields/count/version; changing the event before verification produces unknown rather than success
- Rejected required change yields partial; missing/partial source coverage and missing requested sections yield partial; reading a missing source after publication does not retroactively repair an old artifact
- Deterministic restart and steering reuse immutable acquired source evidence and retain earlier artifact versions
- Scripted model decisions exercise selection, read batches, clarification, report composition, proposal review and post-effect continuation. These are protocol fixtures, not live-model success
- Interrupted provider call is not automatically replayed; saved returned decisions resume without another call; shutdown and lease reclamation fence late results
- Crash after child draft creation but before parent link recovers the same draft. Cancellation finds orphan draft receipts; confirmed effects are not rolled back
- Cancellation between artifact writes prevents the second dispatch and still lists already-created output
- Real controller HTTP requests cannot list/confirm/cancel run-origin drafts; real owner can; unrelated legacy controller drafts retain their previous behavior
- A mismatched operation receipt is not adopted, classified as run-origin or cancelled. Canonical matching-intent recovery remains successful
- Raw text responses reject declared/streamed oversize, compression, trickle deadline violations, malformed/deep JSON and invalid provider parts; Qwen/Gemini usage and injected transport compatibility remain covered

## Review fixes and interim evidence

Independent review caught and fixed: model-section/deterministic-evidence count mismatch; calendar create readback that initially checked only existence; provider excerpt versus citation-range mismatch; omitted source page and aggregate byte caps; orphan draft after pre-link crash; cancellation between two file dispatches; uncapped control receipt growth; incomplete-source acceptance; inherited unbounded buffered provider response; paired-controller exposure through legacy proposal routes; and wrong-draft adoption via operation-key collision.

An interim whole-backend diagnostic contained four failures after the first streaming implementation encountered already-consumed `MockTransport` JSON responses. A bounded preloaded-test path and regression fixed that compatibility issue; the final affected legacy tests above pass. The original diagnostic is retained as [interim transport compatibility evidence](durable-runs-interim-backend-transport-compatibility.txt), not presented as the final aggregate.

## Unverified and deliberately incomplete

- No live provider request, paid usage or genuine-model usefulness/naturalness assessment was performed
- Source line coverage and file hashes do not fact-check prose. Structural `succeeded` still reports quality unassessed
- No run-facing browser write tool, arbitrary web search, general desktop control, human takeover, parallel children, recurring goal scheduler, deletion interface or durable notification outbox ships in this slice
- The browser service remains separately admitted for its own fixed public/synthetic workflow. This implementation does not bridge private run data into it
- The streaming response deadline is checked after headers and between raw chunks, with a five-second HTTPX phase timeout. Header parsing and blocked OS calls are not forcibly terminated; no hard process deadline is claimed
- Actual frontend/target-browser acceptance, final full-tree aggregate, remote CI and publication are owned by the parent and separate QA task

A1 artwork, DeviceApp layout, school documents, original assets, user runtime data and hardware operation were not changed by this slice.
