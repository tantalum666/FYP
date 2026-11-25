# Attack the Premise — managed-browser stale_form JOB_DEADLINE_EXCEEDED

## Reported observation
Nodeid: `tests/test_managed_browser_auth.py::test_auth_input_is_fenced_before_credentials_reach_provider[stale_form]`
Under full-suite load (e.g. #161 tip first run): worker finished with `JOB_DEADLINE_EXCEEDED` in ~375ms while `pending()` waited for `owner_input`, before the stale-nonce mutation. Isolated re-run passed. Nominal product auth window is 90s; overall job deadline 180s. Fixture uses `FastClient` with `active_seconds=0.25`, `auth_seconds=1`.

## Shared premise of unsuccessful explanations
**Premise P:** The ~375ms `JOB_DEADLINE_EXCEEDED` means the product falsely expired a fresh managed job against the 180s wall/job deadline (clock/global-state bug). Isolated pass proves flaky load only; no determinate deadline/handshake defect.

## Observation if P is false
A controlled repro without foreign ports/load can still produce `JOB_DEADLINE_EXCEEDED` (or a false early stop) when:
- the FastClient auth budget (`auth_seconds=1`) or active budget (`0.25`) is exhausted before `owner_input` is published / before the test posts, OR
- `auth_wait` accounting starts before the form is actually pending for the owner, OR
- setup/active/auth budgets are conflated so initial request is treated as expired, OR
- wall clock vs monotonic mismatch, OR
- fixture `pending()` 2s wait races a correctly short fixture auth window under scheduling delay.

## Hypotheses (prove, not prescribe)
H1: FastClient `auth_seconds=1` correctly expires abandoned auth; under load `pending()` fails to observe `owner_input` before that 1s window → worker stops with JOB_DEADLINE → pytest.fail. Product 90s intact; fixture race / insufficient publish-before-wait barrier.
H2: `auth_wait` accumulates during setup/origin approval before auth form is shown → false early expiry even when owner reacts immediately.
H3: Outer `wait_for(setup+active+auth)` or inner active check (`now - active_started - auth_wait > active_seconds`) burns the 0.25s active budget while blocked on auth, falsely expiring.
H4: Shared global clock/state across tests; negative control with fresh world should not fail if H4 true alone.
H5: Genuine product bug on main with production timings (90/90/45) — must prove without FastClient shortening.

## Contract checks required
- Execution deadline starts and budget handshake per managed-browser.md
- Initial request not falsely expired
- Genuinely expired job rejects/cleanup, no redispatch, unknown no claim/effect, no paid model
- Preserve CLEANUP_REQUIRED on unconfirmed cleanup; same-page hold deadlines untouched

## Verdict

Premise P is **false**. First bad transition: FastClient `active_seconds=0.25` exhausted during pre-auth (origin) work before `waiting=True` starts `auth_wait` credit. Suite scheduling delay >250ms yields ~375ms `JOB_DEADLINE_EXCEEDED` inside `pending()` before stale_form mutation. Production 90s active unaffected. Fix: fixture `active_seconds=2.0` + regression with 300ms pre-auth delay.
