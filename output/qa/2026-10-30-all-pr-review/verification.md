# Group 2 · Outstanding PR review and integration

30 October 2026. The owner explicitly requested reviewing all outstanding PRs, explaining the older unmerged work, and merging what passes. The frozen set is #4, #5, #15, #16, #19, #64–#69. [Original PR metadata](pr-inventory.json), [changed-path inventory](change-inventory.json) and [dispositions](dispositions.json) preserve exact heads and scope.

## Findings that prevent a direct old-kernel merge

### PR5: migration rejects legitimate SQLite sidecars on macOS

The original `_migration_path_identity` pins the directory's link count alongside inode, mode and owner. On this host, opening a WAL database changes that count when ordinary sidecar entries appear. The script then reports `MIGRATION_STORE_CHANGED` before the requested upgrade. A synthetic database created by the current application reproduces it; no user database was used. [Diagnostic](pr5-migration-diagnostic.json), [original migration result](pr5-fixture-migration-1.txt).

The original PR5 backend suite was run against its own archived source: **1,334 passed / 46 failed**. Forty-five failures concern migration paths; one concerns a missing explicit JSON-depth bound on Python 3.14. These are this Mac/environment's results, not a revision of historical Linux results. [Original run](pr5-original-tests.txt).

A change only in the ignored diagnostic copy retains the directory inode/mode/owner and the database file's single-link restriction, while excluding the mutable directory link count. **129 focused migration tests then pass.** [Diagnostic patch](pr5-diagnostic-migration-fix.patch), [test result](pr5-diagnostic-fixed-migration-tests.txt). This zero-context diagnostic diff was not installed into the production application or pushed onto PR5; it is evidence, not an automatic migration step.

### PR5: current owner memory is not migrated into its alternative model

After that isolated guard repair and both explicit schema upgrades, the old runtime can start. The synthetic current database still contains one `owner_memories` row, but PR5's `personal_memories` API shows zero. The data is physically retained but unavailable to the old assistant/UI. [Before](pr5-upgrade-before.json), [after diagnostic upgrade](pr5-memory-compatibility.json). A real integration needs an explicit model/API mapping preserving revisions, expiry, aliases, provenance and forgetting behavior; advancing `user_version` alone does not do it.

### PR5: overlapping execution and interface contracts

The old branch has a separate run/context/memory/browser/connector composition and a demo-record application adapter. The current `application_executor.py` is the real Calc/Writer staged-publication adapter. They are an add/add conflict with different meanings, not interchangeable implementations. The trial merge reports **49 conflict records** against the current baseline, including core runtime, assistant, memory, conversations and UI. [Compatibility inventory](merge-compatibility.json).

The old 20,000-level JSON fixture also passes through the parser on Python 3.14 instead of producing the documented structural error; its guard relies on `json.loads` raising `RecursionError`, which is not a portable depth limit. This is an additional bounded-parser regression, separate from database migration.

**Disposition:** PR5 does not meet the owner's “no problems” merge condition. Preserve it for a compatible port; do not replace the current core or revive its CI workflow. The six research reports are already retained through PR69. This review is not an exhaustive security sign-off on every old branch line.

## Superseded branches

- **PR4:** the historical intact-A1/presentation branch conflicts with current Alice and later mobile/UI work. The active default is Alice in `appearance.ts`; do not reintroduce an older default through a conflict resolution. Original artwork and provenance stay on the preserved branch.
- **PR16:** the former A1 study loads `/companion/a1-v2.glb`; current rendering uses the selected Alice VRM and newer scene/phone behavior. Its earlier UI simplification has evolved into the current shared assistant. It is a superseded candidate, not a reason to restore the rejected character.
- **PR15:** Qwen Omni and explicit media support were incorporated and extended in the later integration. Four original credential/media/setup helpers are byte-identical to the current baseline; voice, audio, UI and tests have later changes. [Exact helper comparison](pr15-incorporated-helpers.json). Reapplying the entire old branch would replay obsolete lifecycle/UI material.

Close these three PRs as superseded after the current integration is on main, retaining all branches and original commits. Do not label a superseded closure as a merge.

## Eligible integration

PR64–69 form the current sequential software/research stack. Review covered memory/replay validity, owner policy and revocation, business-receipt recovery, task scope, registered application operations, staged writes, dependency/source versions, immutable results, limited evaluation tools and closed-budget behavior, shared UI/navigation and documentation scope. [Reading scope](reading-record.json) distinguishes current checks from prior unchanged implementation reading.

PR19 adds the dated hardware teacher-review package. All five PDF pages were rendered and inspected; text/photos/tables/blank approval fields are legible, with no clipping. A PDF binary attribute prevents Git treating its ASCII85 streams as source whitespace; no PDF bytes are normalized. The original PDF remains **9,537,272 bytes**, SHA-256 `6cca77bdef39ba0ac0bf6cda73350f99f627f0a339cb8d041000ac32843fa149`. Eight priced entries total CNY 1,053.12 / HKD 1,158.43 at the explicitly dated budget rate; thirteen required items remain unpriced. [Artifact/arithmetic check](pr19-artifact-check.json). This is document integration, not procurement, approval, deployment or hardware acceptance.

The local candidate retains the latest root product/decision/handoff/work-log wording in PR19's five conflicts and adds links/history for the dated hardware package. Application source stays on the current stack, except for one reviewed cancellation-message repair: a staged application action cancelled before publication now reports that fact instead of claiming execution never began. The regression verifies the recovered assistant reply after actual staging cancellation. [Focused result](cancellation-regression.txt).

## Local validation

| Check | Result | Evidence |
|---|---|---|
| Current full backend before review fix | 524 passed | [Baseline](current-backend-baseline.txt) |
| Final full backend after repair | 524 passed | [Final](final-backend.txt) |
| Cancellation/permission regression | 36 passed | [Focused tests](cancellation-regression.txt) |
| Frontend suite | 89 passed | [Frontend](current-frontend-baseline.txt) |
| TypeScript/Vite | Passed; existing chunk-size advisory | [Build](current-build-baseline.txt) |
| Ruff | Passed | [Lint](current-ruff.txt) |
| Original PR5 backend | 1,334 passed / 46 failed | [Original](pr5-original-tests.txt) |
| Isolated PR5 guard diagnosis | 129 focused passed; current-memory mapping still fails | [Diagnosis](pr5-diagnostic-fixed-migration-tests.txt) |
| PR19 PDF | Five pages inspected; source bytes preserved | [Pages](pr19-pages), [hash/totals](pr19-artifact-check.json) |

One existing Starlette/httpx deprecation warning is retained. No CI or paid model execution was used. Original PR5 includes an Actions workflow; it was neither restored nor run. Existing preview data, keys, databases and worktrees were not used as test fixtures.

## Actual web/phone checks

Isolated fixture at `http://localhost:8832`, current built assets, local preview, providers none. The old `127.0.0.1:5191` preview/runtime was preserved. Browser control used CUA's in-app browser; a stale numeric browser ID was rejected and the documented IAB alias acquired the current surface. No shell/alternate-browser UI automation was used.

- A 42-fact memory list finds the oldest jasmine-tea preference; it is outside the recent 40 prompt window. [Web evidence](web-old-memory.jpg).
- Task → Continue with Alice → note request → exact content review: independent storage showed zero files before approval. Allow once produced one 48-byte file whose SHA matched the receipt and exact fictional content. [Before](ui-before-approval.json), [after](ui-after-approval.json), [UI](web-approved-file.jpg).
- At a measured 393 × 852 viewport, document width is 393. Alice renders after asset loading. Phone Plan → Tasks shows the same task/file result. Changing section or returning while a progress note is dirty preserves it and offers continue/discard. [Alice](phone-alice.jpg), [draft guard](phone-draft-guard.jpg).
- Relevant console errors/warnings were absent in the completed web/phone checks. Temporary viewports/tabs were cleared; fixture input was cleared. Native Simulator touch/keyboard and live voice/provider behavior were not rerun.

## Publication boundary

At this report's preparation, the integration is locally validated and no remote merge has yet occurred. The final publication receipt records the reviewed candidate, actual main merge and individual original PR states. Safe merges, superseded closures and blocked PR5 are separate outcomes. Remote main/head and a clean local checkout must be read back before the final answer.
