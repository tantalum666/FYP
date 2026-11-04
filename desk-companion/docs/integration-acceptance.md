# Integration acceptance

3 November 2026. Lasting checks for the 28 October Codex integration review. The behaviours were already repaired on main; this file maps each lesson to a test that fails if a later slice brings it back. Production paths only. No paid model calls.

Run from `desk-companion/`:

```sh
uv run --no-sync ruff check tests/test_integration_acceptance.py
uv run --no-sync pytest tests/test_integration_acceptance.py -q
```

The client recovery step is inside the pytest module. It loads `frontend/src/api.ts` with Node's TypeScript transform and a small extension resolver. It is not part of `npm test`, which uses `--experimental-strip-types` and cannot load that module.

| Codex lesson | Fails when | Test |
| --- | --- | --- |
| Global mapping ignored login and transaction isolation, so a tool cache returned facts after delete and retry | A second runtime with the same effect scope still sees a deleted fact, or another login/task replays the first transcript | `test_deleted_facts_do_not_return_from_tool_cache_or_another_login` |
| Final apply of a backup preview and goal/draft confirm skipped the owner check | A paired device applies a backup, confirms a goal, or replays the owner's operation id | `test_paired_principal_cannot_apply_backup_or_confirm_goal` |
| Backup and restore validation left incomplete job rows and remapped a directory fingerprint | An incomplete job is listed, or a restored folder is accepted when its fingerprint no longer matches | `test_restored_jobs_round_trip_through_list_and_reject_bad_backups` |
| Tool validation filled defaults and cleared notes, location, and reminders when a field was omitted | `execute_tool` calendar update then HTTP confirm drops an omitted schedule field | `test_shared_tool_validation_preserves_omitted_schedule_fields` |
| Stream interruption counted as complete, and recovery read SSE as JSON, duplicating drafts | Closing the stream early completes it, the recovery body parses as JSON, a second recovery adds a draft, or the real client retries off the SSE path | `test_interrupted_assistant_stream_recovers_once_through_sse` and `tests/fixtures/stream_recovery_check.mjs` |
| Callers of a removed method remained, and macOS treated a helper and a component as the same file | A direct runtime service call names a missing method, or two source paths collide when compared case-insensitively or without a `.ts`/`.tsx` suffix | `test_macos_paths_and_service_callers_stay_resolvable`, `test_removed_method_detector_flags_a_missing_call` |
| Tests wrote the database and never called list/restore, or checked schedule fields by a private call | Lessons 3 and 4 above are the guard: they use `GET /api/computer/jobs`, backup apply, and `execute_tool` | same tests as lessons 3 and 4 |

`test_removed_method_detector_flags_a_missing_call` locks the scanner itself. The production tree is scanned by `test_macos_paths_and_service_callers_stay_resolvable`. The scanner counts `runtime.<service>.<method>()`, `services.<service>.<method>()`, and `self.<service>.<method>()` only inside `class Runtime`. Broader name matching collides with unrelated attributes such as `voice.conversations` and `tasks.BaseOptions`.

Older checks in `tests/test_integration_boundaries.py` still cover parts of the same review. This module is the checklist future agents should extend. Do not delete the older file to make this one the only copy.

## Gaps

- No macOS build. The path scan is the case-collision guard; it does not compile an Apple bundle.
- Task updates that omit fields and replace the whole row are outside this checklist. The reviewed failure was calendar notes, location, and reminders through shared tool validation.
- No hardware, Pi, Alice wake, desktop chat, or mailbox journey files. Those slices stay on their own branches.
