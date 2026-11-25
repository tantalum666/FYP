# Group 2 · Managed-browser FastClient active-budget reliability

25 November 2026. Grok Bot. Independent branch from public `main` `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d`. Does **not** stack #158–#161. No merge, CI, deploy, Pi, live account, paid model, or provider/A3 change.

## Reading / scope

Read: `AGENTS.md`, `product.md`, `handoff.md`, recent `decision-log.md` / `work-log.md`, `desk-companion/docs/managed-browser.md`, `managed_browser_client.py` deadline loop, `tests/test_managed_browser*.py`. Ancillary #160 whitespace hygiene first (separate tip).

## Ancillary hygiene (#160)

| Item | Value |
|---|---|
| Command | `git diff --check origin/main...HEAD` |
| Tip before | `a4882b8969` — **exit 2** |
| Exact hit | `output/qa/2026-11-25-followed-reply/verification.md:102` trailing two spaces |
| Distinction | `a4882b89` removed EOF blank line in `mail_reply_reminder.py`; it did **not** clear this tip-file whitespace. Failure is on the final tree file, not a historical range-only artifact. |
| Fix tip | `d8aad9fbba` on `cursor/followed-reply-reminder-e853` |
| After | same command **exit 0** |

## Reported intermittent failure

| Field | Value |
|---|---|
| Nodeid | `tests/test_managed_browser_auth.py::test_auth_input_is_fenced_before_credentials_reach_provider[stale_form]` |
| Symptom | Worker finished with `JOB_DEADLINE_EXCEEDED` in ~375ms while `pending()` waited for `owner_input`, before stale-nonce mutation |
| Prior note | Recorded on #161 verification as independent of UI harness / chrome-kill; isolated re-pass |

## Attack the Premise

**Premise P:** ~375ms `JOB_DEADLINE_EXCEEDED` means the product falsely expired a fresh job against the nominal **180s** wall/job deadline (clock/global-state bug). Isolated pass ⇒ flaky load only.

**If P false:** controlled pre-auth delay without foreign ports can still produce `JOB_DEADLINE_EXCEEDED` when FastClient’s short **active** budget burns before `auth_wait` credits start.

Premise P is **false**.

## Causal proof

Product loop (`managed_browser_client.py`): while `waiting` (owner auth form), time accrues to `auth_wait` (max `auth_seconds`); otherwise it burns `active_seconds`. Origin approval does **not** set `waiting`. Offline fixture `FastClient` had `active_seconds=0.25`, `auth_seconds=1`. Production remains 90/90.

| Probe | Pre-auth session-GET delay | `active_seconds` | Result |
|---|---|---|---|
| A baseline | 0 | 0.25 | owner_input OK |
| **B** | **0.30s** | **0.25** | **`JOB_DEADLINE_EXCEEDED` ~0.38s** (matches ~375ms) |
| C | 0.30s | 2.0 | owner_input OK; stale nonce 409 |
| D | 0.30s | 90 | owner_input OK |
| Old-control after fix | 0.30s | subclass 0.25 | still `JOB_DEADLINE_EXCEEDED` ~0.39s |

Artifacts: `/tmp/deadline-race/causal-probe.json`, `old-active-control.txt`, `attack-the-premise.md`.

Not a 180s job-deadline / store.clock bug. Not Vite contention. Paid model never called (offline MockTransport). Genuinely abandoned auth still expires via `auth_seconds` and deletes the session. `CLEANUP_REQUIRED` uncertain-cleanup tests still pass. No same-page hold / privacy / revocation change.

## Fix (fixture only; new PR from main)

`FastClient.active_seconds`: **0.25 → 2.0** with comment. Still ≪ production 90s. `auth_seconds=1` unchanged for abandoned-form coverage.

Regression: `test_pre_auth_delay_still_reaches_stale_form_fence` — 300ms pre-auth stall must still reach stale-nonce 409, no credential submit, session deleted.

## Verification

Interpreter `/tmp/desk-venv/bin/python`. Parent `fc3b8d2`.

| Check | Result |
|---|---|
| Focused auth + idle + uncertain + approve/cancel | **25 passed** |
| Preceding order (uncertain cleanup → idle → stale_form → regression → abandoned) | **5 passed** |
| Full `test_managed_browser.py` + auth with known main failure deselected | **32 passed, 2 deselected** |
| Ruff / `git diff --check` | clean |
| Old active=0.25 + 300ms delay control | still `JOB_DEADLINE_EXCEEDED` |
| Chrome UI | unchanged product UI — not re-run |

### Known out-of-scope on current main

`test_unadmitted_origin_and_auth_are_never_auto_approved[origin|authentication]` asserts `failed` / `COMPUTER_MANAGED_OWNER_REQUIRED` but this environment returns `unknown` on **pristine main** `fc3b8d2` with original `active_seconds=0.25` as well. Not introduced by this fixture change; not widened here.

## Remaining gates

- Codex review of this PR
- Parent weekly-limit budget
- GitHub merge / CI / deploy / Pi / live / paid — not authorized
- Separate investigation of pristine-main `unadmitted` → `unknown` if authorized
