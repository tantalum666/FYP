# Terminal watch retention: independent runtime audit

2026-10-13. Isolated synthetic SQLite and real local API requests only. This reviewer changed only this QA directory. No application edits, Git actions, package installation, provider request, user-runtime inspection, live migration or user-data removal.

## Findings and fixes checked

1. **Receipt ceiling:** reproduced fresh purge preview accepting corrupted preexisting totals 259/260. Fixed by refusing a new purge above 258; original-key recovery still precedes this gate. Independent tests cover 254→Trash255→Restore256 and ordinary 256→Pause257→Cancel258→Purge259.
2. **Bounded capacity metadata:** reproduced a 1,048,576-byte corrupt timestamp leaving SQLite as a fully materialized Python scalar before returning unavailable. Fixed with SQL enum/type/byte guards and invalid sentinels. Independent tests cover all five lifecycle scalar columns; corrupt data yields unknown usage without payload materialization. Invalid purged shells never provide free capacity.
3. **Hidden stop regression:** reproduced actual HTTP hidden listing returning 409 for broken JSON, missing private fields and oversized private bodies, preventing stop access. Fixed to separate safe hidden metadata from private-body decoding. Independent HTTP tests require hidden listing and pause/cancel to succeed, omit titles/task IDs, and leave visible reads honestly unavailable. A forbidden-decode hook verifies hidden list and both stop actions do not parse private bodies. This does not claim every database query everywhere avoids all private metadata.
4. **Startup recognition:** independently checked parent's missing owner/settings/state finding after repair. Existing malformed stores refuse before credential creation or bootstrap. New supported binaries require explicit migration opt-in and refuse unsupported schema versions. Forward refusal is not protection against historical binaries.
5. **Capacity semantics:** metadata-only receipt excess must return unavailable in the unchanged capacity-v1 body-count dimension, not falsely label a <=20 body count as over-limit. Independently tested after implementer correction.

## Coverage

- Twenty retained definitions: Trash remains charged; Restore keeps the same terminal identity; purge releases exactly one slot; eight concurrent matching retries create one receipt; replacement enrollment consumes the released slot
- Strict irreversible confirmation booleans; terminal-only admission; hidden maintenance refusal; actual request/Origin guards; current disposition responses and no-store headers
- Exact original create/purge keys survive preview restart/expiry and removed task dependency; changed body or target conflicts; no resurrection or second receipt
- Preview wall and monotonic clocks, backward wall time, five-minute boundary, session replacement, settings hide/show epoch, personal epoch, changed inventory, restart and 32-entry eviction; denied mutations have zero database writes
- Postcommit personal-epoch denial followed by same-key recovery; normal/Trash count consistency; 256 lifetime identity admission; malformed purged shells and 259/260 receipt corruption
- Lifecycle-aware trigger/worker exclusion, including corrupt active status on already trashed/purged identities; independent task/nonwatch table snapshots remain unchanged by maintenance
- Migration process exit after each of 23 schema/index/trigger statements, after version write before commit, and immediately after commit: 25 windows. Precommit schema/version/data fully roll back; postcommit schema is coherent
- Purge process exit after source removal, review removal, shell update, receipt insertion, revision bump and commit: 6 windows. No body removal can commit without its barrier/receipt
- Supported SQLite backup includes committed WAL content, integrity-checks cleanly, and remains independently readable as the pre-migration state. A separate post-backup change demonstrates that intentional backup rollback loses subsequent changes; nothing automatically restores history
- Missing-runtime CLI paths with and without opt-in never create a directory, database, credentials or application. Root CLI/app regression suite also exercises unsafe paths, closed read handles, malformed stores and explicit app factory opt-in
- Four forged maintenance tool names supplied with an otherwise valid preview and strict confirmation fail run-tool validation, Assistant.tool and actual asynchronous voice ToolDispatcher, with zero database writes

## Source and evidence boundary

`test_independent.py` is independently authored QA; `results.txt` records its final run. `regression-results.txt` records separately rerun implementation/original watch, worker, capacity, migration and parent CLI/app tests. `source-hashes.json` pins runtime sources, relevant implementation tests and this probe; `hash-stability.json` checks those bytes across the final runs. Exact final counts and readiness are recorded below after completion.

The earlier design audit's old-binary downgrade probe belongs to source 4c41dbaa3caec7c5bec0a73f807a80de4890776e (Store unchanged at dd3ab24). Its recorded result is historical evidence, not a current-source test. Re-running that old probe while importing the new Store would not reproduce the historical implementation. The operational requirement remains: stop all processes, verify a coherent protected backup, migrate with the supported binary and prevent older binaries from opening it. No automatic downgrade safeguard against already-shipped binaries is claimed.

Actual mounted browser acceptance is separately owned by interface/desktop audits. This report does not prove actual device rendering, live provider behavior, real account identity, hardware, deployment, disk-full resilience or forensic erasure. Work/files/voice retention mechanisms remain outside this watch-only implementation. The existing Starlette/httpx test-client deprecation warning is non-failing; no dependency was installed or changed.

## Final result

At 2026-10-13 08:58 UTC: **91 independent tests passed** and **211 focused/original regression tests passed**, with no failures. The latter includes the parent's CLI/app migration tests. All **15 pinned files remained unchanged** across these final runs. The repaired hidden-stop subset separately passed **5 tests**; its prior **3 failures** remain recorded in `hidden-stop-before.txt` and the repair evidence in `hidden-stop-after.txt`.

No open runtime/API/migration blocker remains in the tested watch-only slice. Parent owns product/handoff/decision/work-log updates, full integration freeze and any authorized publication; this reviewer made no such changes. Frontend audit and mounted acceptance are separate evidence, not implied by these results.

Reproduction from repository root, using only existing dependencies:

```sh
PYTHONPATH=desk-companion/backend desk-companion/.venv/bin/python -m pytest -q output/qa/2026-10-13-terminal-watch-runtime-audit/test_independent.py
PYTHONPATH=desk-companion/backend desk-companion/.venv/bin/python -m pytest -q desk-companion/tests/test_watch_retention.py desk-companion/tests/test_watch_retention_migration.py desk-companion/tests/test_watch_migration_cli.py desk-companion/tests/test_responsibilities.py desk-companion/tests/test_responsibility_worker.py desk-companion/tests/test_work_capacity.py desk-companion/tests/test_work_capacity_admission.py
```
