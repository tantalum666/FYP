# Group 2 · Initiative finding → follow-up → revisitable status

25 November 2026. Grok Bot. Independent branch from public `main` `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d` (PR #157 workspace). Product tip still `be5cfaf3d11f24c3d566ac17d8c9689002bcdfe6` (unchanged this closeout). Notes tip after this document cites that product SHA and is not a fake suite re-run. Harness-only fixes landed on source PRs #158 and #159; #160 untouched; no feature stack onto #161. Prior trees `65eb854e` and `43b82c75` preserved.

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

Owned browser ports `5200`/`8840` (initiative UI), `5191`/`8832` (mail UI), `5190`/`8831` (owner-page UI), and `5192`/`8833` (task-recovery UI) are on the loopback allowlist.
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

## Prior four-way tree (preserved; not the closeout gate)

Worktree `/tmp/fyp-integrate-158-159-160-161` tip `43b82c75f6a84d071572d4ebde932f5ae575210f` (local only). Prior three-way `65eb854e` preserved. Retained failure log `/tmp/fourway-failure-preserve/backend-combined4.txt` (also copied under that folder).

| Exact nodeid | Assertion / request | Evidence |
|---|---|---|
| `tests/test_owner_page_ui.py::test_hold_card_on_desktop_and_narrow_screen` | `AssertionError: API did not start` | stderr `OSError: [Errno 98] ... bind ... ('127.0.0.1', 8831): address already in use`; backup `desk-20261125T074232Z.sqlite3`; uvicorn thread `SystemExit: 3` |
| `tests/test_task_recovery_ui.py::test_interrupted_task_explains_the_unknown_result_without_writing_again` | Playwright `TimeoutError` waiting for `get_by_role("button", name="Leave this one alone")` | HTTP journey reached reconcile `200`; after that **no** fresh `GET /api/tasks` — same-URL `?page=tasks` under a **foreign** Vite left the discuss overlay without a list remount |

Invariant violated: UI harnesses shared `5190`/`8831`, started Vite without process-group ownership (`task_recovery` used `terminate()` only → orphan `ppid=1` node still listening later), and proceeded without proving the listener belonged to the test. Isolated re-pass does **not** close the full gate. Calling that “contention” without naming the nodeids was incomplete.

Causal proof (retained under `/tmp/fourway-failure-preserve/causal/`):

1. Foreign Vite on `5190` → owner fails with page-server exit (same class as `combined-browser-uis.txt`).
2. Foreign holder on `8831` → owner fails `API did not start` / Errno 98 (same as full-suite owner failure).
3. Foreign Vite on `5190` → task-recovery fails exact `Leave this one alone` timeout (same as full-suite task-recovery failure).
4. Negative control: hold `5190`/`8831`, run fixed task-recovery on `5192`/`8833` → **passed**.
5. Fixed owner fail-fast when ports held; passes and releases ports when free; no orphan Vite after.

Independent `JOB_DEADLINE_EXCEEDED` on `test_managed_browser_auth[stale_form]`: job failed in ~375ms while deadline window was ~180s inside `pending()` before the form mutation. **Not** the same root as UI port ownership (managed-browser auth worker race under load). Isolated re-pass; not widened here.

## Harness fixes (source PRs; #161 product unchanged)

| PR | Tip | Change |
|---|---|---|
| #158 | `70accc16231d0323b9c92af25b2e4fba81659fd1` | Fail fast if `5190`/`8831` taken; require Vite ownership; `killpg` + wait until owned ports free |
| #159 | `1f760a41eac90734e496943937adcb42355f7eb0` | Dedicated `5192`/`8833`; process-group Vite; ownership readiness; fresh `?page=tasks&recovery=list` after discuss; allowlist those origins |
| #161 product | `be5cfaf3d11f24c3d566ac17d8c9689002bcdfe6` | **Unchanged** (`git diff be5cfaf3..notes -- desk-companion/backend desk-companion/frontend/src` empty of product edits) |
| #160 | `a4882b89697a4b8c47a6217e788161225761fdbd` | Untouched |

## Fresh four-way closeout tree (local only)

Worktree `/tmp/fyp-integrate-4way-final`, branch `local/integrate-4way-final-e853` (not pushed). Order: `main` → final #158 → final #159 → #160 → #161. Conflicts kept all features and stronger baseline asserts. Combined tip **`23d9f44a1aa33239db5b6d087a3e349e64fe6452`**.

Commands (sequential, ports confirmed free first): `git diff --check`; `ruff check backend tests`; `npx tsc --noEmit`; `npm run build`; `npm test`; `/tmp/desk-venv/bin/python -m pytest -q --tb=line`; then the four UI nodeids.

| Combined check on `23d9f44a` | Result |
|---|---|
| `git diff --check` / Ruff / tsc / build | clean / passed |
| Frontend `npm test` | **442 passed** |
| Full backend **one** run | **3080 passed, 1 skipped, 1 failed** in 1108.81s. Skip: existing PHP CLI shop basket |
| Failed nodeid | `tests/test_live_owner_page.py::test_dead_page_hidden_context_and_deadline_do_not_open_another_browser` — uncaught `DomainError('COMPUTER_CLEANUP_REQUIRED', 409)` at `computer_use.py:430` where the test expected screen `BROWSER_PAGE_LOST` after `_kill_chrome` (race: blocker present with `active_job is None`). Focused alone: **passed** in 3.65s. **Not** the prior UI port defect; not fixed by inventing coverage; not re-hunted with another full suite |
| Four browser UIs (initiative / mail / owner / task-recovery) | **4 passed** in 59.71s @1440+320; all eight owned ports free afterward; no orphan Vite |

**Gate verdict:** original two four-way UI failures are root-caused and harness-fixed on #158/#159; their nodeids are green in the fresh full suite and in the four-UI run. Full combined backend is **not** accepted green because of the remaining `test_live_owner_page` cleanup race under suite load. No GitHub merge.

## Distinction of evidence

| Kind | This gate |
|---|---|
| API / simulation | Adversarial pytest owner/stranger/paired/hide/revoke/stale/replay |
| Real controllable local browser | Chrome on owned isolated ports; abort→retry and mail/owner/task repros |
| Authorization | Owner session + in-transaction hide/session checks |
| External result | None claimed |

## Remaining gates

- Full combined backend green (open: live-owner cleanup race under load)
- GitHub merge / CI / deploy
- Live mailbox / paid model / provider / A3 / Pi
- Parent weekly-limit budget decision
- Codex review of open PRs #158–#161
