# Terminal watch retention backend verification

2026-10-13. Continuing parent implementation task, inheriting the 186-document
intake. Focused reading is recorded in `reading.json`. This worker changed only
watch lifecycle/backend accounting/Store compatibility, focused tests, the small
legacy-column capacity test fixture, this QA directory and
[the focused contract](../../../desk-companion/docs/watch-retention.md).
Parent owns shared product/architecture/README/handoff, app-factory integration,
one-time migration CLI and publication; the interface worker owns UI.

## Result

Implemented terminal-only Trash, Restore history and explicitly confirmed
permanent removal, with bounded owner/session/settings/personal-epoch previews,
atomic SQLite body removal plus hash-only receipts/tombstones, original-key
recovery and no resurrection. Existing capacity-v1 keys remain exact; Trash
stays charged and only a validated completed purge releases a body slot.

Fresh Store initializes schema2 with all four core watch tables. Supported legacy
stores require explicit operator opt-in before any bootstrap mutation. Core
ownership/schema checks reject unrecognized stores instead of creating new
credentials. Migration uses individual SQL statements under one write
transaction, preserves legacy bodies/IDs/history and replaces known triggers.
New forward-version refusal does not protect against already-shipped old binaries.
Stopped processes and a separately verified coherent protected backup remain
operator requirements; no real migration was performed.

## Final checks

- **78 new focused tests passed**: 50 lifecycle/authority/accounting/rollback/HTTP
  cases and 28 schema/opt-in/migration/rollback/backup cases. Exact post-freeze
  output: `focused-results.txt`
- **194 combined tests passed** before final recording: the 78 new tests plus
  116 existing responsibility/capacity regressions. This is a focused backend
  integration result, not the parent full-suite aggregate
- **Parent integration suite: 15 CLI/app-factory tests passed**, separately owned
  and reported by the parent; not added to the worker's 194 total. These cases
  are also included in the independent 211 regression rerun below, so those
  results must not be summed as distinct tests
- **Ruff passed** on the four owned backend files and three relevant test files:
  `ruff.txt`
- **Eight owned source/test/spec files unchanged across final checks**:
  `source-manifest.json`, `source-stability.json`
- Local contract links checked: `links.json`
- [Independent runtime audit](../2026-10-13-terminal-watch-runtime-audit/review.md):
  91 independent QA tests plus 211 implementation/original regressions passed;
  25 migration and six purge child-process-exit windows, coherent committed-WAL
  backup readback, actual local HTTP identity/origin/hidden-stop checks and
  model/voice tool denial. Fifteen audit-pinned files were unchanged across its
  runs. Exact independent logs and source hashes remain in that audit directory

The Starlette/httpx test-client deprecation warning is non-failing. No dependency
was installed or changed in response to it.

## Issues caught and repaired before freeze

1. A new purge at corrupted existing receipt totals 259/260 was initially
   admitted. Preview and mutation now require at most 258 existing receipts;
   the final total stays at most 259. Original-key recovery remains available
2. Corrupt 1MiB lifecycle strings initially crossed SQLite as full Python values.
   SQL now returns only bounded enum/integer/timestamp projections or fixed
   invalid sentinels; malformed values never become fake null/available usage
3. Aggregate metadata excess could incorrectly label the twenty-body count as
   over-limit. Capacity-v1 now says unavailable for metadata-only excess; actual
   body overflow remains over-limit
4. Unconditional private-body decoding initially blocked hidden stop controls
   on malformed/oversized watch JSON. Hidden listing and pause/cancel now use
   metadata-only projections and never load/decode that private body; visible
   content remains honestly unavailable
5. Existing malformed Store ownership/state could have caused bootstrap to
   create a new credential. Early recognized-schema/singleton checks now reject
   before bootstrap; read-only inspection and journal connections close explicitly

These findings were checked independently and have no remaining audit blocker.

## Evidence and authority boundary

Every database, task, watch, history-removal operation, backup and intentional
rollback in these tests was synthetic and isolated in pytest temporary paths.
No current user runtime store was opened/migrated, no actual user history was
removed and no watched task or independent Work/file/voice data was removed.
No real provider/network/credentials/account/installation/Git operation was
performed by this worker. Permanent removal is an app feature gated by the
owner's separate final confirmation, not authorization to delete current data.

No mounted browser/device, live model/voice, hardware, filesystem reclamation,
forensic erasure or deployment acceptance is claimed. The parent owns aggregate
validation, shared status changes and any authorized publication. The
[retained-work design](../../../planning/2026-10-13/retained-work-recovery-design.md)
continues to defer broader Work/file retention and dependency/crash protocols.
