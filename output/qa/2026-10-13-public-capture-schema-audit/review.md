# Independent schema-3 and staged migration audit

13 October 2026. Independent QA only. Inherited the ongoing 186-document intake; relevant full contracts, plan/review, Store, schema helper, both CLIs, Runtime/app wiring and migration tests were read. Changes made by this auditor are confined to this QA directory. Fixtures and subprocesses use synthetic temporary local databases. No actual user database was migrated; no external network, credentials, Git publication, environment setting or application source was changed by this auditor.

## Result

The scoped schema/migration implementation is acceptable after two reproduced issues were fixed by its implementation owner and independently retested. Final frozen runs passed 68 independent cases and a rerun of 129 owner regression cases. All 10 audited source hashes were stable across those runs and the seven owner hashes matched the final manifest. The owner-suite rerun emitted one existing Starlette/httpx TestClient deprecation warning. Exact details are in the adjacent logs and freeze manifests. This is software evidence, not public-network, real-runtime migration, live UI or hardware acceptance.

## Reproduced issues and fixes

1. **Preflight filesystem identity was not carried into migration.** After private v2 preflight, replacing the approved database path with a symlink to a different synthetic v2 let the capture CLI migrate that other target to v3 and report success. `probe_path_race.py` is the standalone reproduction; `initial-path-race-result.json` records the pre-fix result. Both CLIs now carry pinned directory/database identity through full read-only verification and Store initialization. Same-owner, private-mode, regular-object, inode/device and link-count checks repeat around connection opens and before journal/bootstrap mutations. The fixed standalone probe returns failure, and the other target remains v2. Independent regressions cover both CLIs with symlinks, hardlinks, regular-file replacement, directory replacement and file/directory permission changes.
2. **Post-fix mode normalization could falsely report failure after commit.** An accepted private database with mode 0700 migrated successfully, then Store's unconditional chmod to 0600 invalidated its own pinned mode and made the CLI report failure. The owner changed explicit migration to preserve its preflighted private mode. Both watch 1→2 and capture 2→3 now return success and preserve 0700 in independent regression fixtures. Fresh-store creation retains its existing 0600 behavior.

The revised current-version read-only path also repeats full structural/identity validation rather than trusting only a second version read. Independent same-inode owner corruption after preflight fails without bootstrapping a replacement owner or creating credentials.

## Coverage

- Fresh schema 3, exact required capture table/index/default/type/CHECK/foreign-key/unique structures, quoted literal fidelity, absent/partial/damaged ledgers and extra triggers, including with capability disabled
- Explicit separate migration consent; strict actual booleans; schema 1 watch-only migration stops at 2; current Runtime rejects that handle; the next distinct capture migration reaches 3; watch CLI refuses 3
- Default old/future-version refusal before initialization, no credential creation on existing stores, prior data preservation and no opportunistic repair
- Bounded corrupt identity/control projections before Python; invalid nullable source identifiers cannot become legitimate NULL; private intent/acquisition JSON is neither parsed nor repaired by startup, including oversized synthetic corruption
- Lifetime capture bound, coherent existing read-handle snapshot across migration, unsupported versions and file/directory permission boundaries
- Process-exit and exception rollback windows across both capture tables, indexes and user_version; complete schema after commit; inside-BEGIN revalidation of changed version/structure
- Exact archived cc1751a Store module rejects schema 3 without changing database bytes. Archived SHA256: `14ab5ff8530a52acf4b076ebc97bc55f491359a96405069d6479702f8b32d0ee`. This is an exact historical Store module check with current compatible relative dependencies, not full historical application acceptance

Independent test scenarios overlap the implementation owner's regression scope. Do not sum their counts as unique coverage.

## Operational limits

Python sqlite3 still opens a pathname. Repeated lstat identity checks substantially narrow the checked race windows but do not establish atomic OS-level no-follow opening or immunity to hostile ABA path replacement between checks. Same-owner/private paths, stopped workers and an operator-controlled directory remain prerequisites. Neither CLI stops processes, creates a backup or verifies one; its acknowledgment flag does not prove those prerequisites. A separately verified coherent SQLite backup is still required. Old binaries must not access a migrated store; this code cannot retrofit guards into older software.

Actual user migration and backup verification remain unperformed. No live request was made. The capture feature remains off by default; this audit did not enable it. Parent owns shared product/handoff/work-log documentation and any separately authorized publication.
