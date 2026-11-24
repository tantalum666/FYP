# Group 2 · Local page handoff

24 November 2026. Source baseline `cc8350c5e59c8a51474d8225cbb4e1124131d0ee` (`origin/main`, 2026-11-24 23:05:47 +0800). No open pull requests. Branch `cursor/owner-page-handoff-f7ae`.

Status: implemented and locally verified. Not merged, not deployed, and not accepted against a live merchant or account.

## What this is

The local computer-use worker keeps the Chromium context open when a password, OTP, captcha, or payment control is present. The admitting owner clicks and types on that same page from the job card, then hands it back. Hand back reads that document once. The original goal continues only when `classify_owner_wall` is clear, and `wall-evidence.json` is written from that snapshot. A remaining wall stays paused. A dead page or failed read becomes `unknown` with no second browser and no model call during the hold.

This is app-mediated control of the Playwright page already opened for the job. It is not a headed operating-system window, not the hosted OpenAI desktop, and not a merchant or account sign-in. Model defaults stay `gpt-6.2-sol`, `gpt-live-1.1`, and A3 v9. The Pi update in the handoff is unchanged.

## Reading for this run

Read in full at the start of the investigation, then re-checked the contracts this change touches: `AGENTS.md`, `handoff.md`, `product.md`, `desk-companion/docs/computer-use.md`, `managed-browser.md`, `personal-agent-status.md`. Code read around `ComputerSupervisor`, `computer_use_worker.py`, `jobs.py` takeover/hand-back, and `JobActionCard`.

## Checks

| Check | Result |
|---|---|
| `tests/test_live_owner_page.py` | Passed. Local Chrome. Password fixture pauses and offers Take over. A Sign-in navigation link does not pause. Owner typing is absent from the database and the response. The card screenshot changes after Continue. Hand back stays on the rehearsal page, succeeds only with matching wall evidence, and a second Hand back with the same operation id returns the stored result. A stale version conflicts. Hidden private context, another owner session, and a revoked session get no screen and no handoff. Killing Chrome makes the next read `unknown` with no second launch. Deadline expiry closes the page and does not continue. No model call during the hold. |
| `tests/test_owner_page_ui.py` | Passed. Installed Chrome at 1440×1000 and 320×740. Home shows To do and the composer without horizontal overflow. The job card offers Take over, then typing and Hand back, without card overflow. After the browser is killed, the card shows the closed-page error and Check result. Work & tools still opens. |
| `tests/test_owner_takeover.py` | Passed. The synthetic driver still covers the API fences. |
| Full backend `pytest` | 3047 passed, 9 failed, 1 skipped, about 17.5 minutes. Python 3.12. The 9 failures also fail on unmodified `main` at `cc8350c5`: office attachment fingerprints, flight reprice readback, managed unadmitted-origin cleanup, the ordinary Google composer renderer (`useHomeTranscript` under this Node transform), and the forget-context equality that now includes `home_archived`. They are outside this slice. |
| Frontend `npm test` | Two failures also present in the current source outside this slice: `browser-workflow.test.ts` expects a single-line timeout expression that `api.ts` already splits, and `knowledge.test.ts` expects a Web Push sentence in a file this slice does not edit. `npx tsc --noEmit` passed. |
| Ruff on the edited Python files | Passed. |

No paid model call, hosted Agents session, credential form, ordinary browser profile, CI workflow, Pi change, or deployment was used.
