# Group 2 · Official execution mainline verification

17 November2026. Owner-requested switch from optional/off to the primary official browser route. Active source branch codex/official-agent-mainline-20261117 on PR126 beeace55. No CI; no dependency installation; existing FYP credentials remain private and unchanged.

## Implemented and checked

Current API/form/conversation default managed, legacy/default-local bytes retained; explicit opt-out and no silent fallback. Empty202 support, one root turn/final-answer verification, two bounded stream reconnections with canonical items and no task/approval replay. Registered sign-in within the same job uses a RAM-only owner form, explicit account-read consent, session/version/nonce/task/privacy/provider/deadline checks and one-time consumption. No credentials in SQLite/WAL, reports, operation receipts or browser storage. Account-scoped evidence is labeled separately. Active45/owner-wait90/cleanup12 seconds remain bounded.

Full backend: **2,428 passed in516.86seconds**. Frontend: **391 passed**, TypeScript/build passed. Focused backend88cases include new auth/default/recovery boundaries. Ruff, diff checks and the source secret/material scope scan passed; private runtimes/assets were excluded. The initial new auth test used an obsolete settings-column assumption; corrected to the real versioned SettingsInput before the full pass. Initial typecheck exposed a missing managed capability type; fixed before build.

## Actual browser journey

Browser plugin not available; used installed Chrome via existing PythonPlaywright. Isolated API8832/frontend5191, desktop1440×1000 and phone393×852. App identity/content, no framework overlay, no horizontal overflow and no page exception passed. Dark input/button contrast inspected. One public-task draft→owner sharing→official-engine job→registered sign-in→account-read consent→same-job result→follow-up report. Both sessions deliberately lost an SSE subscription; phone also lost the auth POST reply. Each still created one session, sent one user input and one form submission, and deleted/read back the session. Independently compared stored receipt/evidence hashes.

Expected console entries: deliberate phone ERR_FAILED and software-WebGL ReadPixels screenshot warnings. No unexplained app exception. A first QA collector used a route behind the production catch-all; corrected to a private file receipt and the full journey reran successfully. Raw scripts/screenshots/logs/runtime remain in ~/.config/desk-companion/official-mainline-20261117, outside source. Checked statistics are in results.json.

## Delivery and paid trial

Source **8c67ddbe1559eea975aa355bef970a8e98a9edcc** is activated as immutable release20261117-8c67ddbe on normal Mac8831.367manifest files verified, checked database backup, schema3/124tables retained, unchanged A3 voice version9/app-grant versions/protected-file hashes. Fresh backend readback reports default_browser_engine=managed, managed enabled/configured=true. Actual production desktop/phone render, build-info and index hash match. Frontend remains the same checked bundle430d996a.

Native iPhone17Pro/iOS26.5 build/install/launch succeeded, process99821 at acceptance; bundled build-info/index match the Mac release and the actual screenshot was inspected. Process-only origin points at Mac8831; saved origin was not overwritten. Initial native build needed the already installed vendor clone at the Xcode-relative root path; corrected without dependency installation. No full native sign-in interaction is claimed from browser-phone testing.

Pi authenticated relay attempts twice returned stdio-forwarding failure. It was not reachable and received no activation, performance change, reboot or firmware modification. A verified final delta from its prior2c31f430 baseline is prepared privately,31changed files/455,974bytes, SHA25679409be4873b2e1cca6c2ef9580de155a563814746ccd245ef33886d5e8c0d32. Do not apply the Mac's small intermediate delta to the older Pi base.

The full2,428backend pass preceded a final two-line scope-receipt correction: an owner grant is recorded before submission, so a lost provider acknowledgement cannot mislabel possible account access as public. After this correction,54focused managed/auth/conversation checks and Ruff passed, including a new lost-provider-reply case. The final source was then reactivated and native bundle/readback repeated; no frontend behavior changed after its391tests/build/browser QA.

A new US$1 / at most2sessions /90total active seconds budget question remains unanswered. Prepared live_check.py refuses execution without a fresh authorization file; no such file exists and this round made **zero paid/model calls**. All old budgets remain closed. A prepared script is not real official or merchant acceptance. No real login, email send, purchase/payment/ticket occurred.

Publication: [PR127](https://github.com/tantalum666/FYP/pull/127), draft/open, stacked on126→124. Source push/remote HEAD and final docs push are verified separately. No merge or GitHub CI. Preparation initially invoked system Python3.9, which lacks tarfile's data filter; the empty staging directory was removed and the trusted source archive was re-extracted with project Python3.14 before any activation.

## Remaining boundary

Public comparison and registered supported forms are the current scope. QR/passkeys/CAPTCHA, general remote desktop takeover, cross-job account retention and restart reattachment are not implemented. Provider report integrity is not independent truth of every page assertion or a transaction receipt. Pi's last recorded power/network instability remains separate from this software task.
