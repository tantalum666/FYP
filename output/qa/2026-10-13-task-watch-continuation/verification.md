# Selected task-change watch frozen integration verification

Completed2026-10-13 07:44 UTC in the cloud workspace. Baseline e1807f441a5c9b09d48654825dfac633a2bdee03 already had71 candidate blobs/ref and both exact source CI verified. This new task-watch record precedes its own publication; remote CI and actual browser acceptance remain separate.

## Implemented outcome

Owner explicitly enrolls one to ten saved task IDs and selected fields, a bounded expiry, local retention and review budgets. Initial enrollment is quiet. Transaction-coupled SQLite dirty mailboxes detect only selected saved changes, coalesce one pending review, preserve restart watermarks and support version-exact acknowledgment. Pause, baseline-now resume, cancel, expiry and missing-source recheck have explicit semantics. No model, external message, unselected source or automatic AgentRun is invoked.

Explicit current-evidence compilation hands exact available IDs into a fresh deterministic Work draft. Owner independently reviews current scope, retention and Start. Missing records block rather than silently shrink selection. Current labels and inspected values are not historical snapshots; watch acknowledgment and independently started Work are separate.

## Frozen software result

Command: `UV_CACHE_DIR=/workspace/shared/fyp-uv-cache npm_config_cache=/workspace/shared/fyp-npm-cache bash desk-companion/scripts/check_software.sh`

- Original A1/licensed VRM hashes and Ruff: passed
- Full backend: **840 passed**,289.66seconds
- Full frontend: **186 passed**
- TypeScript/Vite production build: passed
- **262 source/test/config/lock files unchanged** throughout the run

[Complete log](release-software-checks.log), [source stability](release-source-stability.json) and before/after manifests retain exact evidence. This manifest also includes frontend root build configuration/index files in addition to the previous scope. Existing Starlette test-client and unrelated empty-regex pytest warnings, npm inherited configuration notice and Vite large-chunk advisory remain; no failed stage.

## Independent checks and integration

[Backend worker](../2026-10-13-task-change-responsibilities/verification.md):47 focused tests and203 related regressions passed. [Independent backend](../2026-10-13-task-watch-authority-audit/findings.md):31 probes passed, including actual SQLite concurrency/rollback,10000 quiet ticks, genuine paired HTTP identity denial, privacy/operation replay, budgets and explicit Work producing independently read Markdown/CSV bytes.

[UI worker](../2026-10-13-task-watch-interface/verification.md):17 new watch tests within186 frontend checks. [Independent UI](../2026-10-13-task-watch-ui-audit/report.md):20 production hook/callback/SSR scenarios plus14 voice regressions passed. The two parent [actual app-lifespan tests](worker-isolation-tests.log) confirm a failing watch worker does not stop rules and recovers, while disabled scheduler and legacy tick do not advance watches.

Root constructed ResponsibilityService after TaskService, mounted real owner/operation routes and added a separately isolated1second thread-offloaded worker. No new dependency, live connection or changes to original A1/DeviceApp/hardware adapters.

## Reproduced defects resolved

- Final private read/replay could survive hide→show: initial settings epoch now checked in a fresh final transaction
- Expiry left pending delivery without valid stop controls: dismiss and version retained pending review at expiry
- Per-definition failure after partial evaluation writes: savepoint rollback preserves review/budget/cursor consistency
- Inspect privacy denial/redaction failed to clear parent view: immediate shared fence and parent cleanup
- Task inspection omitted authoritative status; bilingual display added
- Old view callbacks could act after selection refresh; exact current-view check added
- Raw persisted daily usage was misleadingly labelled today; display exact nondecreasing UTC accounting day
- Context-changed read/mutation clears revoked private draft/retry authority; sent action may already be saved, so reopen current history rather than a blind new operation

## Scope limits and continuation

Protocol, local HTTP, SQLite, file-byte and hook/SSR evidence is not mounted-DOM, screenshot, browser-save, live model, voice or hardware acceptance. Existing isolated Mac task has a pending platform approval/blank-mount investigation on earlier4e50841; no new search/voice/watch actual-UI pass is asserted. No merge/deploy, paid calls, new credentials or security weakening.

Twenty definitions including terminal entries is a deliberate fixed retention bound, not unlimited use. Source/run/artifact quotas also require transparent capacity and safe lifecycle work; cancelling does not reclaim retained data. Public exact-URL capture/comparison is only a design proposal. Next work is truthful retained-capacity visibility and maintenance planning while actual UI gates are resolved.

Updated root product, README, architecture, decisions, focused design, capability plan, handoff and work log. Inherited186-document intake and focused reading supplements retained. Relative links and secret/asset publication scan precede upload; the generated runtime credentials reference is intentional and never uploaded.
