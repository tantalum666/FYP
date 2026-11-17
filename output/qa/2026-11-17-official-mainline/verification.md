# Group 2 · Official execution mainline verification

17 November2026. Owner-requested switch from optional/off to the primary official browser route. Active source branch codex/official-agent-mainline-20261117 on PR126 beeace55. No CI; no dependency installation; existing FYP credentials remain private and unchanged.

## Implemented and checked

Current API/form/conversation default managed, legacy/default-local bytes retained; explicit opt-out and no silent fallback. Empty202 support, one root turn/final-answer verification, two bounded stream reconnections with canonical items and no task/approval replay. Registered sign-in within the same job uses a RAM-only owner form, explicit account-read consent, session/version/nonce/task/privacy/provider/deadline checks and one-time consumption. No credentials in SQLite/WAL, reports, operation receipts or browser storage. Account-scoped evidence is labeled separately. Active45/owner-wait90/cleanup12 seconds remain bounded.

Full backend: **2,428 passed in516.86seconds**. Frontend: **391 passed**, TypeScript/build passed. Focused backend88cases include new auth/default/recovery boundaries. Ruff and final diff/secret checks are recorded at closeout. The initial new auth test used an obsolete settings-column assumption; corrected to the real versioned SettingsInput before the full pass. Initial typecheck exposed a missing managed capability type; fixed before build.

## Actual browser journey

Browser plugin not available; used installed Chrome via existing PythonPlaywright. Isolated API8832/frontend5191, desktop1440×1000 and phone393×852. App identity/content, no framework overlay, no horizontal overflow and no page exception passed. Dark input/button contrast inspected. One public-task draft→owner sharing→official-engine job→registered sign-in→account-read consent→same-job result→follow-up report. Both sessions deliberately lost an SSE subscription; phone also lost the auth POST reply. Each still created one session, sent one user input and one form submission, and deleted/read back the session. Independently compared stored receipt/evidence hashes.

Expected console entries: deliberate phone ERR_FAILED and software-WebGL ReadPixels screenshot warnings. No unexplained app exception. A first QA collector used a route behind the production catch-all; corrected to a private file receipt and the full journey reran successfully. Raw scripts/screenshots/logs/runtime remain in ~/.config/desk-companion/official-mainline-20261117, outside source. Checked statistics are in results.json.

## Delivery and paid trial

Source implementation is complete; immutable release activation and new authorized live-provider acceptance are still being prepared. Ordinary prior release2c31f430 remains the baseline until actual readback is recorded below. A new bounded paid-trial script is ready but awaits the owner's new budget; old rounds remain closed. No real merchant login, email send, purchase/payment/ticket or Pi power changes are claimed.

## Remaining boundary

Public comparison and registered supported forms are the current scope. QR/passkeys/CAPTCHA, general remote desktop takeover, cross-job account retention and restart reattachment are not implemented. Provider report integrity is not independent truth of every page assertion or a transaction receipt. Pi's last recorded power/network instability remains separate from this software task.
