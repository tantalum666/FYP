# Next slice: find retained work and files

Status: implementation complete, aggregate software validation passed (747 backend /152 frontend); actual browser acceptance remains separate. Read-only inspection completed during the current release check. The owner asked for continuing useful agent capabilities; this local retrieval closes a concrete usability gap without a model or paid service.

## Current gap

Work lists up to 100 broad run records by update time. File lists are opaque-ID ordered, with no unified search. Generated artifact names are generic. Steering overwrites the run's goal; artifacts retain run_id but not an immutable original goal or plan revision. Search must not invent historical associations.

## Backend contract

Add POST /api/work/search as a read-only owner endpoint, with normal cookie/origin/X-Desk-Request protections but no operation receipt. Keep private query text out of URLs and storage.

Input: query (trimmed, at most 200 characters), kind (all/run/artifact/source), limit (default20/max50), offset (bounded), and snapshot for subsequent pages. Output: compact discriminated items, total, snapshot, next_offset, search_scope=local_metadata, ranking=lexical_v1 and file_status_basis=last_recorded.

Read the entire bounded corpus in one SQLite snapshot: 100 runs, 100 sources and 400 artifact reservations. Fail clearly if data exceeds its admitted cap, rather than silently claiming complete search. Project an explicit whitelist; never reuse broad run _view(), read source bodies, reconcile files, dispatch tools/models or write an index. Recheck actual owner/session/privacy revision before response, including hide/show and delayed requests. Snapshot fingerprint binds query/filter and searchable metadata; changed pagination returns WORK_SEARCH_CHANGED.

Normalize Unicode NFKC, casefold and whitespace. Require all query terms, with unspaced Chinese handled as literal substring. Rank exact opaque ID, exact own title/current goal, own phrase, all own terms, then linked metadata; only then recency and stable kind/ID. No semantic, fuzzy or cross-language synonym claim.

Searchable metadata: run current goal/ID/selected source names; artifact name/ID/current linked goal/provenance source names; source name/ID. Return match reasons. Never include session hashes, operations, reports, evidence/tool payloads, memory/history, provider config or host paths.

## Honest relationships

Label associated goal as Current linked goal. Current output requires exact membership in current_artifact_ids. Earlier requires known membership in artifact_ids and exclusion from a present valid current list. Missing/legacy/unfinished linkage is unknown; no run ID is unlinked. Filename/date/supersedes_id never prove original goal or revision.

Search file status is last-recorded only. Exact detail/preview/download performs existing fresh byte checks. Do not cast a search hit into a full source/artifact record. Multiple names remain separate choices; no automatic resume, sharing or download of a best match.

## UI and implementation seams

New work_search.py plus Runtime/router wiring; tests/test_work_search.py. Frontend new workSearch.ts, useWorkSearch.ts and WorkSearchPanel.tsx; guarded integration into private RunPanel. Explicit submission, no keystroke or four-second search polling. Fence query/filter/sequence and identity/privacy, clear private results on hidden/offline/stale/sign-out, never persist browser storage or URL query state.

Run selection opens existing exact detail, with fresh versioned controls. Artifacts/sources use existing detail and preview/download contracts. Preserve genuine dirty/retry guards and the transient-refresh fix from the preceding release. Labels and safe rendering support English and Chinese.

## Acceptance

Older strong matches outrank newer weak ones; all admitted records beyond existing pages are covered. Test Chinese/English/mixed/fullwidth and literal injection-like text, duplicate names, exact current/earlier/unknown membership, missing parents and pre-link publication windows. Verify deterministic pagination/change conflicts, owner-only access, hidden/revoked/delayed privacy rejection, compact projection and zero model/file-body/database writes. UI tests cover response reordering, explicit ambiguity selection, guarded navigation, stale results, exact endpoints and honest recorded-status labels. Add actual browser search→choose→detail and hide-during-request evidence when a supported environment is available.
