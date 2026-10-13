# Retained-work search: frozen integration check

Completed 2026-10-13 06:44 UTC in the authorized cloud workspace. Source baseline is `8948b73b23591466b1167a68ea5a89b9ca65fa54` (proof-only head for source4e50841). This record precedes this search batch's publication; remote ref/CI and actual browser acceptance are separate evidence.

## Implemented and exercised

Owner-only local metadata search covers up to100 runs,100 source reservations and400 artifact reservations. Explicit query/filter submission uses Unicode lexical ranking and snapshot-bound forward/backward pagination. Duplicate names remain exact-ID choices; current linked goals and current/earlier/unknown/unlinked output membership are not historical-goal assertions. Fresh exact detail and existing previews/downloads perform byte checks; discovery only shows last-recorded status.

Runtime constructs WorkSearchService after the existing source/file/run services and mounts the real owner-only POST route. The search performs no file-body read, reconciliation, model/tool call or database/index write. Current owner session/privacy is checked before and after snapshot processing. UI selection, query order, privacy/session/offline/stale and dirty/retry navigation are fenced without automatic start, retention or grants.

## Frozen checks actually completed

Command: `UV_CACHE_DIR=/workspace/shared/fyp-uv-cache npm_config_cache=/workspace/shared/fyp-npm-cache bash desk-companion/scripts/check_software.sh`

- Original bundled A1 and licensed VRM hashes: passed
- Ruff backend/scripts/tests: passed
- Full backend suite: **747 passed**,195.03s
- Full frontend suite: **152 passed**
- TypeScript and Vite production build: passed
- **236 source/test/config/lock hashes unchanged** between before/after manifests

Full output: [release-software-checks.log](release-software-checks.log). Manifest proof: [release-source-stability.json](release-source-stability.json). Existing Starlette/httpx deprecation, one unrelated pytest empty-regex warning, npm inherited http-proxy config warning and Vite large-chunk advisory remain; no check failed.

Focused implementation evidence: [90 backend search tests](backend-verification.md), [frontend152 tests and21 new tests](frontend-verification.md). Independent audit: [23 backend/HTTP cases, six actual-hook scenarios and four final actual-function guard checks](../2026-10-13-work-search-audit/verification.md). The initial JSON boolean-to-number projection and misleading substring-ID label were corrected and independently rechecked.

## Remaining gates

This is metadata retrieval, not semantic/full-file search, translation, historical-goal reconstruction or automatic resume. SQLite JSON operators require3.38+. No paid calls, credentials, external app access, audio/hardware or deployment. Actual mounted-browser search/choice/detail, narrow layout and delayed-response interruption remain pending in the isolated Mac acceptance path; hook/SSR/function tests are not a substitute. Original8832 preview/runtime is left as found. The existing current Mac task is testing source4e50841 first, not this unpublished search batch.

The next responsibility and voice-handoff design files are proposals only; no implementation or new permission is claimed from publishing those plans. The broader continuous-agent task remains open.

## Documentation

Updated product, decision-log, handoff, work-log, desk-companion README/architecture and focused search design/contract. Inherited186-document intake remains valid; focused reading is documented separately. Publication scan preserves all remote leaves absent from this sparse workspace and never infers deletion. No credential/runtime files or browser screenshots are uploaded.
