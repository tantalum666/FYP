# Group 2 · Initiative finding → follow-up → revisitable status

25 November 2026. Grok Bot. Independent branch from public `main` `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d` (PR #157 workspace). Adversarial + four-way gate product tip `be5cfaf3d11f24c3d566ac17d8c9689002bcdfe6`. Notes tip after this document cites that product SHA and is not a fake suite re-run. Pull requests #158, #159 and #160 were not checked out for editing, restacked, or feature-imported. Prior three-way throwaway `65eb854ecd99dd5e9998161b57aab4a451340eac` is preserved and was not used as a build base.

## Chosen gap (current main)

On `main` after #157, Conversation already shows proactive findings with Sources and Got it. The owner could dismiss a finding, but could not explicitly open a bound private follow-up task from that finding and later reread accurate status on the same card. Mail-thread follow-up and memory follow-up are different journeys. This slice closes only that suggestion → sources → owner-chosen follow-up → revisitable status path inside existing Alice Conversation / Tasks.

## Adversarial review (transaction / permission)

Reviewed actual write semantics, not only the happy card.

| Case | Finding | Fix / evidence |
|---|---|---|
| Same-key replay + second key | One task; second key returns `already_following` | Covered in `test_followup_replay_and_second_key_bind_one_task` |
| Nested status read in write txn | `_followup_status` opened a second SQLite connection inside `apply` | Reuse the write `conn` |
| Withdrawn / changed sources | Follow-up could still create a task for a finding no longer matched by `sources.matches` | Refuse with `INITIATIVE_STALE` (409) before insert |
| Got it | Dismissals never create `initiative_followup` evidence | Covered |
| Paired display Bearer | Owner cookie required; paired 403 | Covered |
| hide_private between preview and commit | `require_owner_transaction` → `PRIVATE_CONTEXT_HIDDEN` | Covered |
| Revoked session | Logout then POST → 403 | Covered |
| Deleted bound task | Status `missing`; later POST keeps same task id, no second task | Covered |
| Edited title + same-title decoy | Live title from bound id; decoy ignored | Covered |
| Cancelled / completed | Live status; dismiss does not send or overwrite | Covered |
| Notices | Titles stay generic (`Alice noticed something` / `Alice has N updates`) | Asserted no finding wording in notice JSON |
| Failed write after unknown | Abort keeps exact operation id; Retry reconciles original | UI uses abort-then-continue |

Broader gap (not fixed here): no hard-delete task API; missing status uses row absence. No accidental follow-up from opening Sources (details only).

## Implemented journey

1. Owner expands Conversation and opens Sources on a pending finding.
2. Owner chooses Follow up on this. Alice creates one private task bound by task id to that finding. Nothing is sent.
3. The finding card shows live status (open / waiting / completed / cancelled / missing).
4. Tasks lists the follow-up. Hide-private fences display; id binding remains.
5. Unknown/aborted write keeps Retry the same request; success does not invent a second task.
6. Got it still dismisses without sending.
7. Stale/withdrawn evidence refuses a new follow-up without creating a task.

Local fake initiative + fixture login only. Not live mailbox, not paid model, not live external acceptance.

## Origin ports

Owned browser ports `5200` (Vite) and `8840` (API) remain on the loopback allowlist beside `5190`/`8831`/`5191`/`8832`.

## Independent local checks (product `be5cfaf3`)

Interpreter `/tmp/desk-venv/bin/python`. Chrome `/usr/local/bin/google-chrome`.

| Check | Result |
|---|---|
| Focused initiative API + adversarial + UI | **28 passed** (`test_initiative.py` 27 + `test_initiative_followup_ui.py` 1) |
| Full backend (clean re-run after one flake) | **3062 passed, 1 skipped, 0 failed**, 1044.82s. Skip: existing PHP CLI shop basket |
| First full run on this tip | 3061 passed / 1 failed: `test_managed_browser_auth[stale_form]` `JOB_DEADLINE_EXCEEDED` (unrelated timing). Isolated re-run of that case **passed**; clean full re-run green above |
| Frontend `npm test` | **438 passed, 0 failed** |
| `npx tsc --noEmit` / `npm run build` | passed (existing chunk-size warning) |
| Ruff on edited Python / `git diff --check` | clean |
| Chrome 1440 / 320 | abort → Retry → Follow-up open. Nothing was sent. → Tasks |

## Four-way throwaway integration (local only)

Worktree `/tmp/fyp-integrate-158-159-160-161`, branch `local/integrate-158-159-160-161-e853` (not pushed). Order: `main` → #158 → #159 → #160 → #161.

| Head | SHA |
|---|---|
| main | `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d` |
| #158 | `c2cac2d8f95da625a3b08ee6a8699bc27aa34692` |
| #159 | `90275bf08272bb49b9d50216b2e7e1f9d7246588` |
| #160 | `a4882b89697a4b8c47a6217e788161225761fdbd` |
| #161 product | `be5cfaf3d11f24c3d566ac17d8c9689002bcdfe6` |
| Combined resolved tree | `43b82c75f6a84d071572d4ebde932f5ae575210f` |
| Prior three-way preserved | `65eb854ecd99dd5e9998161b57aab4a451340eac` |

Conflict policy: keep all four feature sets; keep stronger baseline asserts (`requestDeadline` path checks, full `momentView` suite, fingerprint/reprice/`session_origin`/forget/composer mocks); docs sections kept together. No feature-branch restack onto GitHub.

| Combined check | Result |
|---|---|
| Full backend | **3079 passed, 1 skipped, 2 failed** in 1208.56s. Failures: `test_owner_page_ui` (API did not start) and `test_task_recovery_ui` (click timeout) under interleaved full-suite port contention on 5190/8831 |
| Those two alone after killing Vite/API | **2 passed** |
| Four browser UIs sequential (initiative / mail reply / owner hold / interrupted-task) | **4 passed** at 1440 and 320 |
| Focused non-UI interactions (initiative+mail+owner/live/takeover) | **90 passed** |
| Frontend | **442 passed**; tsc/build/ruff/`git diff --check` clean |

Independent suites do **not** substitute the four-way result. The two full-suite UI failures were port contention, not product regressions; sequential owned-port re-runs passed.

## Distinction of evidence

| Kind | This gate |
|---|---|
| API / simulation | Adversarial pytest owner/stranger/paired/hide/revoke/stale/replay |
| Real controllable local browser | Chrome on owned ports; abort→retry and mail/owner/task repros |
| Authorization | Owner session + in-transaction hide/session checks |
| External result | None claimed |

## Remaining gates

- GitHub merge / CI / deploy
- Live mailbox / paid model / provider / A3 / Pi
- Parent weekly-limit budget decision
- Codex review of open PRs #158–#161
