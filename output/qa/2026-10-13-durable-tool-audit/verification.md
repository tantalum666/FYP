# Independent durable-tool and personal-context audit

Completed 13 October 2026 UTC. This is a read-only implementation review with isolated regression tests. Production fixes were made by the owning implementation worker and coordinating parent; this reviewer wrote only the audit evidence and uniquely named reproduction tests here.

## Result

No unresolved confirmed blocker remains in the reviewed scope after the fixes below. This is not a claim of exhaustive race coverage, live-provider usefulness, real browser execution, general desktop control or successful deployment.

- 123 focused repository tests passed in 37.30 seconds: agent browser tools, personal-context bridge, integrated personal-context runs, atomic publication, exact effect receipts and durable runs
- 9 independent audit regressions passed in 3.40 seconds
- 13 text-response-boundary tests passed in 0.90 seconds
- Focused tests emitted the existing Starlette/httpx TestClient deprecation warning; no failure remained

## Confirmed findings and verified fixes

### P1: provider dispatch could follow completed cancellation or forgetting

Original path: `agent_planner.decide` projected selected personal context, constructed the request and called `TextAssistant.generate` without a final authority check. A cancellation or memory-forget action completed after projection but before generation, yet the old private marker still reached the generation seam. The later result fence worked, but did not prevent the new request.

Verified fix: `generate_guarded` checks current authority after planner construction and carries a per-call ContextVar guard to the HTTPX request hook after request serialization, immediately before transport. No privacy lock spans network I/O. Independent cancellation and forgetting tests now show zero generation/transport calls at the respective boundaries. Known refusal uses a `dispatch_refused` attempt rather than an unknown paid outcome.

### P2: final browser-observation commit could publish a cancelled or privacy-stale read

Original path: `BrowserService.observe` fenced before observation validation, then committed `observed` and its excerpt without rechecking the parent generation/privacy inside that commit transaction. Cancellation or hide during validation left a retained child observation even though the run discarded its late evidence.

Verified fix: the final `BEGIN IMMEDIATE` validates the browser's session/privacy and invokes a separate transaction-aware run publication checkpoint before updating the observed row. Cancellation and hide injected during validation now leave no published observation. Confirmed cleanup evidence is preserved.

### P2: an unrelated operation receipt could satisfy a required task change

Original path: creating an unrelated task through the normal task service with operation key `assistant-confirm/<proposal-id>` passed the run guard. The verifier compared the saved receipt to its current row without checking that the operation request matched the requested draft. The run could report success with the required task absent.

Verified fix: canonical task/calendar creation/change requests are checked by the operation guard and the outcome verifier. Independent tests prove mismatched requests are rejected before mutation and historical mismatched receipts remain unknown/partial. The coordinating parent also rejects externally supplied `assistant-confirm/` operation IDs at the HTTP boundary. The repository's additional parameterized tests cover all four local mutation families.

### P2: known local projection refusal was mislabeled as an unknown provider outcome

After the dispatch fix, a forget action immediately before projection caused a local exception before generation, but the generic model exception handler still left a running attempt and reported provider uncertainty.

Verified fix: local context/schema/limit assembly is separated from transport and maps known local refusal to `TextDispatchRefused`. The independent regression confirms zero provider calls, preserved privacy failure reason and a terminal `dispatch_refused` attempt. The repository regression also checks persistence across service restart.

## Other boundaries checked

- Artifact publication passes the trusted callback through ArtifactService to ImmutableFiles, including a write transaction immediately before the final no-overwrite hardlink
- Store's trusted operation guard runs before operation receipt replay or mutation application
- Personal context remains metadata-bound to exact session, destination, revision and selected records; it is neither authority nor evidence, and its private binding is omitted from public run views
- The public browser brief accepts only same-run selected public observations and code-owned title/note; model prose, goals, memory and local private sources cannot enter its payload
- Stable tool reservations recover their exact child receipts; unconfirmed child reviews do not trigger paid model polling
- Unknown browser cleanup and changed/missing export bytes cannot satisfy a required verified effect
- Structural output success remains distinct from semantic quality or the owner's broader goal

## Reproduce

From `desk-companion`:

```sh
PYTHONPATH=backend:tests .venv/bin/python -m pytest -q ../output/qa/2026-10-13-durable-tool-audit/test_*.py
.venv/bin/python -m pytest -q tests/test_agent_browser_tools.py tests/test_agent_context.py tests/test_agent_personal_context_integration.py tests/test_agent_run_publication.py tests/test_agent_effect_receipts.py tests/test_agent_runs.py
.venv/bin/python -m pytest -q tests/test_text_response_bounds.py
```

The copied independent tests use existing fixture helpers, real temporary SQLite/file storage, scripted model responses, a fake browser protocol and HTTPX MockTransport. No live provider, MCP server or browser call was made. The historical-receipt test deliberately disables only the local test guard while seeding a pre-fix receipt, then restores it before checking verification; it does not weaken production behavior.

## Reading and source identity

This audit continues the same implementation round and inherits the 186-file full-Markdown reading ledger at `../2026-10-12-agent-kernel/reading-union-status.json`. Relevant project/product/handoff contracts and changed implementation areas were read; no repeat whole-repository reading claim is made. `audit-source-record.json` identifies the reviewed source snapshots. Hashes identify bytes and do not replace reading evidence.

Current main documentation was observed being updated by the parent during the audit. The initial stale statements that browser tools were not integrated and model calls were fixed at eight were reported for reconciliation; this review does not duplicate the parent's documentation or publication responsibilities.
