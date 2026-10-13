# Group 2 · Local work search frontend verification

Completed 2026-10-13 in the authorized cloud source workspace. Frontend source is frozen for aggregate parent verification; backend and global API wiring belong to the coordinating implementation. The prior transient-refresh draft/retry preservation stays intact.

## Implemented

- Private Work exposes a guarded **Find saved work / 查找已保存工作** view. Entering/leaving it and opening a chosen run use the existing unsent-draft/busy guard. Hidden-mode metadata and stop controls are unchanged
- Search is an explicit submit of `POST /api/work/search`. Typing, changing filters, mounting and four-second work polling do not trigger a search. No mutation key, browser storage, URL query state, provider grant or automatic action is introduced
- All / Work / Files / Sources and empty-query browsing use compact discriminated metadata. Duplicate names remain distinct type/ID/date choices. Results report their actual submitted query/filter, independently of unsent input edits
- Previous/next pages bind the original query, filter and metadata snapshot. Changed-page errors discard old results and require explicit resubmission; there is no silent restart or automatic best-match selection
- Exact run/source/artifact GETs validate IDs and record shape before handoff. Compact search hits never become full source/artifact records. Run opening does not resume; existing versioned controls are reached after fresh detail. Reopening the same selected run locks those controls until its forced refresh settles; newer navigation fences older unlocks
- Search has independent request and selection generations plus identity/privacy/freshness fences. Query/results/previews clear on stale, owner, hidden, session, offline or close transitions. Session/offline events invalidate immediately before effects rerender. A late same-epoch privacy denial clears a newer result too
- English/Chinese cards distinguish last-recorded file status, current linked goal and current/earlier/unknown/unlinked output relationships. Name, date and supersession are not used to infer historical goals or currentness. Source labels/content remain escaped React text
- Existing ArtifactList byte/digest/size/download checks and SourcePreview bounded plain-text behavior are reused unchanged after exact detail checks

## Checks actually run

- `npm test`: **152/152 passed**. [Full output](frontend-tests.log)
- New focused coverage: **16 pure/request/lifecycle tests** plus **5 actual React SSR tests**
- `npm run build`: **passed**, including `tsc --noEmit` and Vite. [Full output](frontend-build.log)
- Prettier check of the six owned frontend files and two new tests: **passed**
- `../.venv/bin/python ../scripts/check_assets.py`: **passed**; bundled VRM and original A1 hashes match their provenance manifests
- Existing Vite over-500-kB chunk warning remains; no new dependency or broad rendering refactor

Request/lifecycle tests execute the production hook using deterministic React-hook slots and deferred transport, including query reordering, exact file/source/run GETs, selection reordering, clear, privacy changes, session/offline events, malformed/coerced result fields, snapshot paging and explicit restart. SSR tests render the actual production components with the installed React renderer and compiler in both languages, including duplicate choices, safe text, recorded-status wording and disabled stale controls. Navigation integration is also source-checked.

These are not mounted-browser click/layout evidence. Real search→ambiguous choice→exact detail, same-run reopening, dirty-draft navigation, hide-during-request and file-preview/download acceptance remain assigned to the separate Mac task. No live model, provider, external application or user-computer access was used by this frontend worker.

## Files and coordination

Owned source: `workSearch.ts`, `useWorkSearch.ts`, `WorkSearchPanel.tsx`; focused integration: `RunPanel.tsx`, `labels.ts`, `agent.css`; new tests: `work-search.test.ts`, `work-search-render.test.ts`. The [frozen source manifest](frontend-source-manifest.json) identifies the exact local files. [Supplemental reading](frontend-reading-supplement.json) inherits the ongoing 186-document intake rather than claiming a fresh whole-repository read.

The coordinating parent updates shared product/handoff/work-log and the final search contract; this frontend worker does not overwrite those shared specifications. Independent review is recorded separately in [the work-search audit](../2026-10-13-work-search-audit/verification.md).

The independent reviewer subsequently executed both final navigation guard bodies: superseded refresh cannot unlock, parent invalidation cannot unlock, search-fence change before handoff suppresses navigation, and unchanged exact selection succeeds. All four focused checks and six independent hook scenarios passed; this remains code-level evidence rather than mounted-browser acceptance.
