# Public-capture schema and explicit migration verification

13 October 2026. Synthetic cloud-workspace fixtures only. No user runtime, live URL,
provider, credentials, actual backup/restore operation, app deployment or Git publication
was changed by this implementation. The coordinator owns shared contracts and release.

## Implemented boundary

- Fresh Store initializes global schema 3 with both capture tables, CHECK/NOT NULL/
  unique/foreign-key constraints and two indexes. Capture intent/policy format remains 1
- Existing recognized schema 2 requires the separate strict-boolean
  `allow_public_capture_migration=True`. Default startup and the watch flag alone refuse
  before journal-mode, bootstrap, settings, credentials or version writes
- Existing schema 1 takes only its separately authorized watch migration and stops at 2.
  Public-capture opt-in on schema 1, including both flags together, is refused. Store
  exposes its actual `schema_version`; the coordinator's Runtime guard refuses an
  intermediate schema-2 Store before constructing application services
- Capture tables/indexes and user_version are committed in the same explicit transaction.
  Both existing version and structures are checked again under the write lock before DDL
- Schema 3 requires exact code-generated sqlite_master structures, including CHECK,
  defaults, uniqueness, FK and indexes, even with capture disabled. Missing/partial/
  substituted schema is never recreated. Schema 1/2 must have no capture structures
- Bounded scalar CASE projections check type/length before copying corrupt identities
  into Python. Invalid BLOB sentinels stay distinct from legitimate nullable fields.
  Identity/hash/control/receipt relationships fail closed; private JSON is not decoded
  during Store validation, so private-JSON corruption does not prevent hidden stop
- A separately named `scripts/migrate_public_capture.py` accepts only a private existing
  recognized v2/v3 store and explicit stop/backup acknowledgment. It never creates a
  runtime or credentials. The flag does not prove a backup exists or stop processes
- Independent review found a post-preflight path-swap gap. Both CLIs now pin the
  original root/database device, inode, mode, owner and link count, recheck private
  no-link identity around SQLite opens and before journal/transaction mutations,
  and repeat complete read-only schema verification before reporting success.
  These are bounded pathname rechecks, not an OS-level no-follow SQLite connection
  or immunity to hostile concurrent ABA swaps; the stopped-runtime prerequisite
  remains mandatory. No detection-after-write undo is attempted. Explicit migration
  preserves the accepted private file mode; it does not invalidate its own pinned
  identity with a post-commit chmod (both CLI branches are tested with mode 0700)
- The old watch CLI's narrowly coordinated adjustment verifies valid v2 read-only,
  migrates v1 only to 2, and refuses v3. It cannot covertly grant capture migration

## Code and fixtures

Exact owned code/test hashes are in `source-manifest.json`. Changes are limited to:

1. `desk-companion/backend/desk/store.py`
2. `desk-companion/backend/desk/public_capture_schema.py`
3. `desk-companion/scripts/migrate_public_capture.py`
4. `desk-companion/scripts/migrate_watch_retention.py`
5. `desk-companion/tests/test_public_capture_migration.py`
6. `desk-companion/tests/test_watch_retention_migration.py`
7. `desk-companion/tests/test_watch_migration_cli.py`

Existing watch fixtures now deliberately remove new capture tables when synthesizing
historical v1/v2 stores. Their historical watch migration still expects version 2;
fresh/current Store expects 3. The factory test now expects Runtime to refuse after a
watch-only v1→2 migration, pending the distinct capture migration. Parent-owned app.py
contains the actual current-version guard and explicit factory wiring.

## Executed evidence

- `tests.log`: 129 scoped migration/CLI tests passed, including ordinary/strict opt-in,
  both staged transitions, pre-journal refusal, malformed structures, quoted CHECK
  literal whitespace, NUL identities, safe-integer bounds, corrupt scalar projection,
  atomic rollback, CLI path/privacy/link/FIFO denial and no credential creation
- Five actual child-process exits after each uncommitted capture DDL/index/version
  statement leave recognized v2. An exit immediately after commit leaves complete v3.
  Restart/reopen never adopts a partially created ledger
- Two preflight→transaction races refuse changed version or missing owner instead of
  bootstrapping a damaged store. Twelve 1-MiB scalar corruption cases verify bounded
  projection for capture/operation fields, including non-integer control values
- Fifteen additional migration-boundary cases cover CLI symlink/replacement/
  permission swaps, same-inode current-schema corruption and before/after SQLite
  connection handoffs. Changed targets are refused before migration; unrelated
  synthetic databases remain unchanged
- `ruff.log`: scoped Ruff passed, including the standalone historical compatibility probe
- `historical-schema2-results.json`: exact archived cc1751a Store module (SHA256
  `14ab5ff8530a52acf4b076ebc97bc55f491359a96405069d6479702f8b32d0ee`) rejects
  synthetic schema 3 with either watch-flag value before database bytes change; the
  same historical module still accepts recognized v2. The coordinator supplied the
  source from the already-verified immutable published payload

The historical probe imports the actual archived Store module with unchanged relative
support modules; it is not a full historical application acceptance test. Older binaries
without the compatibility guard cannot be retroactively secured. Operators must continue
to prohibit old binaries from opening migrated stores and retain independently verified
coherent backups before a separately approved actual migration.

## Scope and remaining checks

The inherited 186-document intake and supplemental complete/segmented reads are recorded
in `reading.json`. Generated QA snapshots, dependencies, caches, third-party and build
outputs are not claimed as a new full intake. No broad source/lifecycle/UI/transport
changes were made by this worker. Shared product, operator, watch-compatibility, handoff,
decision and work-log updates belong to the coordinator; parent aggregate verification
and independent review remain separate. This record proves schema/CLI behavior on
synthetic fixtures, not capture network/lifecycle, mounted UI, user migration or deployment.

## Independent review closure

The [independent schema audit](../2026-10-13-public-capture-schema-audit/review.md)
completed after both review findings were fixed: 68 separate audit cases and the
129-test owner matrix passed. Its ten audited source hashes were stable across both
runs and matched all seven owner-manifest entries. The original path-swap probe now
refuses with the other database remaining v2; both private-mode migration branches
succeed without changing their preflighted mode. No further schema-audit findings
remain. This does not broaden the explicitly documented pathname/ABA limitation or
replace the coordinator's full capture/aggregate acceptance checks.
