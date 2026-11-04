# Integration acceptance harness

3 November 2026. Regression suite for the 28 October Codex integration review. Base is main `dac527b386c268caa96d9388d0c11d206b4f6856` (“Merge PR #72: record verified PR5 publication”). Branch `cursor/integration-acceptance-harness-dcc2`. No production behaviour change was required; the contracts already hold on this tip.

## Reading (this task, not the whole Markdown library)

- `AGENTS.md` (full, prior turn).
- `product.md` current requirements and the 2026-10-28 integration rules (prior turn, relevant sections).
- `handoff.md` (full, 21 lines).
- `decision-log.md` latest PR5 entry only (prior turn). Not appended: no new product decision.
- `work-log.md` tail through the 2026-10-31 PR5 closeout.
- `desk-companion/docs/pr5-integration.md` (opening composition/memory sections, prior turn).
- `desk-companion/docs/software-maintenance.md` “Integrated review invariants” (about lines 55–62). Not edited.
- `output/qa/2026-10-28-grok-review-merge/verification.md` opening and the reviewed-behaviour table (the Codex lesson source).
- Production modules inspected in the prior turn to confirm the contracts: tool policy, capabilities, exchange and routes, jobs and job routes, computer folder accept, assistant decide/calendar draft, assistant routes, goals, text AI stream, reply/stream contract, conversation, app owner dependency, schemas, store. Frontend `api.ts`, `replyStream.ts`, and `frontend/tests/module-paths.test.ts` / `reply-stream.test.ts`.
- This turn: the new test module, the stream-recovery fixture, and the handoff/work-log tails above.

## What the suite locks

| Lesson | Test |
| --- | --- |
| Deleted facts must not return from a tool cache or another login | `test_deleted_facts_do_not_return_from_tool_cache_or_another_login` |
| Paired device cannot apply a backup or confirm a goal, including replay of the owner operation | `test_paired_principal_cannot_apply_backup_or_confirm_goal` |
| Incomplete backups and rebound folder fingerprints fail; a good restore is visible on `GET /api/computer/jobs` | `test_restored_jobs_round_trip_through_list_and_reject_bad_backups` |
| Omitted calendar notes, location, and reminders survive `execute_tool` then HTTP confirm | `test_shared_tool_validation_preserves_omitted_schedule_fields` |
| Interrupted SSE is not complete; recovery is SSE and the real client retries the stream path once | `test_interrupted_assistant_stream_recovers_once_through_sse` |
| Case-insensitive paths and direct runtime service callers stay resolvable | `test_macos_paths_and_service_callers_stay_resolvable` |
| The removed-method detector itself flags a missing call | `test_removed_method_detector_flags_a_missing_call` |

Lesson 7 (tests that wrote SQL or called a private helper) is the method of lessons 3 and 4, not a separate case. The client check lives in `tests/fixtures/stream_recovery_check.mjs` and is started by pytest, because `npm test` uses `--experimental-strip-types` and cannot import `api.ts`.

## Commands and results

From `desk-companion/`, after `uv sync --frozen` (CPython 3.12.3, uv 0.13.7) and an existing `npm ci --ignore-scripts`:

```sh
uv run --no-sync ruff check tests/test_integration_acceptance.py tests/fixtures
uv run --no-sync pytest tests/test_integration_acceptance.py -q
```

First ruff run reported one unused import (`AssistantMessage`). Removed. After the doc edits, ruff reported all checks passed and pytest reported **7 passed** in 4.09s, plus the existing Starlette/httpx test-client deprecation. No GitHub Actions. No paid provider call.

## Gaps

- Full backend (1,686) and frontend (300) suites from the PR5 closeout were not re-run. Acceptance for this change is the focused module.
- No macOS bundle build. Path collisions are detected by the source scan.
- Task-row full replace on omitted fields was left alone. The reviewed failure was the calendar tool path.
- Open Codex drafts #73–#77 and the mailbox journey were not edited. `handoff.md` and `work-log.md` are the only shared docs; expect a text overlap if those branches also append them. No mailbox, Pi, Alice wake, desktop chat, or Work UI source was touched.
