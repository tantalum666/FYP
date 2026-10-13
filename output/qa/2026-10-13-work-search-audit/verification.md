# Independent retained-work search audit

13 October 2026. Same ongoing implementation task; inherited 186-document intake and focused supplemental reads are recorded in `reading-supplement.json`. Source snapshot hashes are recorded in `source-manifest.json`; hashes identify reviewed content and do not substitute for reading.

## Results

- 23 independent pytest cases passed (`pytest.txt`, `test_independent_search.py`), using real isolated SQLite and a local in-process HTTP client
- Six independent deterministic executions of the actual search hook passed (`hook-audit.mjs`, `hook-results.json`), including state observed before effect cleanup
- No unresolved blocker found in the reviewed search boundaries
- One display honesty issue was reported: substring ID matches were labelled “Exact record ID”. The implementation owner changed the label to “Record ID”; source reinspection confirms the fix

Backend checks cover all 600 admitted records across deterministic pages, older exact-title ranking, NFKC/casefold and Chinese/mixed literal queries, injection-like literal text, snapshot change conflicts, exact current/earlier/unknown relationships, missing or invalid parent linkage, and conservative booleans. Delayed corpus processing injects hide, hide/show, owner revocation, expiry and personal privacy epoch changes; all reject late responses. Private report/tool/body/path fields do not enter the returned compact projection. SQL traces show no search writes and explicit corpus projection; source reading and artifact detail/reconciliation traps are not entered. Metadata-only fixtures have no file bodies to reconcile. Static inspection confirms no model dispatch surface in the search service. Shared settings reads use the existing settings helper, not a broad run view.

The real app route checks reject missing request header, absent owner cookie and untrusted origin. A valid cookie and X-Desk-Request succeeds without an operation ID or receipt and returns no-store. Offset without a snapshot is rejected.

Frontend checks execute the real hook with independently implemented deterministic state/effect and transport substitutes. They cover owner replacement, hiding, stale state, session/offline events, exact selection among duplicate names, delayed detail responses, query-response reversal and clearing a pending selection. Results are masked before effect cleanup and obsolete detail promises return null. Source inspection checks explicit submission, labels bound to submitted query/filter, exact-ID detail routes, previous/next snapshot use, no search persistence, and existing dirty/busy navigation guards. Compact hits are not used as full source/artifact records. The independent script was rerun after the pagination update.

## Scope and limits

These are software-boundary checks, not mounted React/browser, live model, public service, hardware or deployed acceptance. No credentials, paid calls, user data, Git writes, external service changes or source implementation edits were made by this reviewer. All test records are synthetic. One upstream FastAPI/Starlette TestClient deprecation warning was observed; the HTTP checks passed. Initial audit assertions were refined for the existing settings helper and the implementer's boolean-preserving SQLite projection; these were test assumptions, not application failures.

The coordinating owner remains responsible for final frozen full-suite/type/build checks, project contract/handoff/work-log updates and any authorized publication. This report is evidence for that integration, not a release claim.

## Final UI guard recheck

After the UI owner froze the last two guard changes, the six hook scenarios were rerun and passed. `final-guards-audit.mjs` additionally extracts and executes the actual final `RunWorkspace.commit` and `WorkSearchPanel.open` function bodies: an older forced reload cannot unlock a newer one; parent privacy invalidation cannot unlock; a search-fence change between exact-detail resolution and handoff suppresses navigation; an unchanged exact selection may hand off. All four checks passed (`final-guards-results.json`). Final source hashes were refreshed. No new issue found.
