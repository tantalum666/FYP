# Work metadata search: backend verification

Date: 13 October 2026. Scope: local cloud implementation and isolated SQLite/API
testing, continuing the inherited 186-document intake. This is not a browser,
live-model, provider or remote-publication acceptance claim.

## Owned changes

- `desk-companion/backend/desk/work_search.py`: strict request/result models,
  owner/session/privacy checks, SQL-whitelisted metadata projection, complete
  bounded corpus, Unicode lexical ranking, honest linkage and snapshot pagination
- `desk-companion/tests/test_work_search.py`: dedicated deterministic coverage
- `desk-companion/docs/work-search.md`: actual API/limits/relationship contract
- This QA record, focused test log and `backend-reading-supplement.json`

The parent owns `runtime.py`/`app.py` construction and router wiring, root
specifications and release validation. The frontend worker owns the interface.
No Git writes, credentials, paid provider, external application, real runtime,
artwork or school files were changed by this worker.

## Checks and results

- Before the final UTF-8 byte-bound regression was added, the combined command
  `.venv/bin/python -m pytest tests/test_work_search.py tests/test_artifacts.py tests/test_agent_runs.py -q`
  passed **177 tests in 47.30 seconds**. It included 89 search tests and existing
  exact-file/run regressions
- The final dedicated search suite contains **90 tests**; its completed result
  is saved in [backend-tests.txt](backend-tests.txt)
- `.venv/bin/ruff check backend/desk/work_search.py tests/test_work_search.py`
  passed; both files satisfy `ruff format --check`
- Full application construction and its actual HTTP owner/origin/header routes
  are exercised via `TestClient`, with scheduler disabled and isolated databases
- The existing Starlette/httpx deprecation warning remains; no test failure is
  hidden by that warning
- An independent reviewer separately ran 23 service/HTTP cases and reported no
  backend blocker; its distinct evidence is under `../2026-10-13-work-search-audit/`

## Explicitly exercised boundaries

- All 600 admitted records are reachable through deterministic paging; the last
  artifact/source records beyond existing first-page limits are searchable
- Each over-cap kind fails clearly, even when the request filters another kind
- Older exact titles outrank newer phrases/term matches/linked metadata; ID,
  UTC recency and stable kind/ID tie-breaking remain deterministic
- Chinese literal substrings, mixed/fullwidth English, casefold, combining
  accents, normalized whitespace and Unicode normalization expansion work
- Quotes, SQL-like text, percent/underscore, regex-like and HTML strings remain
  literal data; no model interpretation or execution is used
- Current/earlier membership is exact; missing parents, missing/malformed lists,
  duplicate IDs and pre-link publication windows remain unknown. Null run IDs
  remain unlinked, and steering changes only the displayed current goal
- Snapshot binding detects query/filter/session/metadata/status changes. Changes
  solely to excluded report/tool payloads do not alter the metadata fingerprint
- The corpus uses one historical read snapshot; delayed hide, hide → show,
  revocation, expiry and consent-epoch changes fail in the fresh authority read
- Real synthetic paired controller/display tokens are denied as bearer tokens,
  device cookies and forged owner cookies
- Malformed JSON/non-object metadata fail without partial results. Optional
  malformed scalars, provenance types, surrogates, nested invalid identifiers
  and bool-versus-int distinctions cannot leak broad internal payloads
- SQL typed JSON projection preserves booleans; an initial `json_extract`
  implementation was corrected after a regression exposed conversion to 1
- 64-KiB projected metadata bound is measured as UTF-8 bytes, not characters
- Full before/after database dumps and connection change counts match for
  searches. File readback/reconciliation/publication, broad run views, model
  generation, operation receipts and worker methods are replaced with failing
  sentinels to prove none are used
- Real fixture bytes can be corrupt/missing while search shows last-recorded
  verified. Existing exact detail detects that condition and changes the stored
  status to unknown; missing downloads continue to fail through the old contract

## Remaining limitations

This is complete bounded metadata discovery, not source-content/semantic search,
translation, fuzzy recall, historical-goal reconstruction, automatic resume,
retention cleanup or independent semantic fact checking. It adds no file-body
index or persistence. Exact detail/preview/download remains necessary for
current file evidence and fresh work controls. SQLite JSON operators require
SQLite 3.38+; this cloud runtime reports SQLite 3.53.1. Actual target-browser,
late-response rendering, model quality and remote release checks belong to
separate evidence and are not inferred from these tests.
