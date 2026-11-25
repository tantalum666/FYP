# Group 2 · Local page handoff

25 November 2026. Integrated branch `cursor/owner-page-handoff-f7ae`.

`origin/main` moved to `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d` (2026-11-25 01:23:38 +0800, merge of PR #157). That tip was merged into this same branch with a normal merge. No rebase and no force push. The pull request is not merged.

Status: local Chrome fixture verified on the integrated branch. Not merged, not deployed, and not acceptance of a merchant or a live account.

## What changed on main

PR #157 is the 25 November workspace redesign. Navigation is Chat, Today, Tasks, Calendar, Inbox, Saved memories, Assistant style, Records, Settings, and Diagnostics. The installed Mac Web and Simulator application named by that release is `b759950c`. An untouched trip rehearsal can close without a draft prompt. The only open pull request after the fetch was #158, this branch. Its recorded base was `fc3b8d2` and its head was still `1d729c29`, so GitHub reported it dirty.

The merge conflicted only in `decision-log.md`, `handoff.md`, and `work-log.md`. Both the workspace redesign and this page handoff stay. The Pi next step now points at `b759950c` rather than the older installed application.

## What this slice does

The local computer-use worker keeps the Chromium context open when a password, OTP, captcha, or payment control is present. The admitting owner clicks and types on that same page from the Computer actions card, then hands it back. Hand back reads that document once. The original goal continues only when `classify_owner_wall` is clear on that snapshot. `wall-evidence.json` records the URL and screenshot hash, and both must match the final observation. A different URL is not treated as cleared. A payment page stays paused: handing it back is not payment or submit approval.

A dead page, a failed read, hiding private context, expiry of the admitting session, the 180-second deadline, or replacement of the live page becomes `unknown` and closes the page. No second browser starts, and no model call runs during the hold. A screen read with no live page returns page-lost and does not send the previous image. An owner-input operation id binds the job, version, action, and a hash of any typed text. The text is not stored. If that input was sent and the result is unknown, the same id does not send it again.

Leaving Computer actions refreshes the conversation card, so a closed page is not still offered as Take over. The 25 November workspace navigation stays in force.

This is app-mediated control of the Playwright page already opened for the job. It is not a headed operating-system window, not the hosted OpenAI desktop, and not a merchant or account sign-in. Model defaults stay `gpt-6.2-sol`, `gpt-live-1.1`, and A3 v9.

## Reading for this continuation

Re-read `AGENTS.md`, `handoff.md`, `product.md` current sections, the latest decision-log entries, `desk-companion/docs/computer-use.md`, and the code this merge touches: `ComputerSupervisor` / `LiveOwnerPage`, `computer_use_worker.py`, the job screen and handoff routes, `JobActionCard`, and `AssistantPanel` jobs view. The earlier full-file investigation list is unchanged and was not repeated.

## Checks on the integrated branch

| Check | Result |
|---|---|
| `tests/test_live_owner_page.py` | Passed. Local Chrome. Password page stays open. A Sign-in navigation link does not pause. Payment stays paused and is not resumed. Hiding private context closes the page. Clearing `live_page` makes the screen read page-lost, and `run_one` does not launch another browser. Typed text is absent from the database and the model transcript. |
| `tests/test_owner_takeover.py` | Passed. The synthetic driver still covers the API fences, including URL and screenshot-hash evidence. |
| `tests/test_owner_page_ui.py` | Passed. Installed Chrome at 1440×1000 and 320×740. The visible Computer actions card offers Take over, then typing and Hand back, without horizontal overflow. Killing Chrome shows the closed-page error and Check result. Back to chat shows the same closed page and does not offer Take over or typing. Tasks and Work & tools still open. |
| Repaired expectations | Passed individually before the full suite: attachment fingerprint stability, ambiguous flight reprice phrase, unadmitted managed origin, ordinary Google composer, and forget-context `home_archived`. |
| Full backend `pytest` | 3059 passed, 1 skipped, 0 failed, 1058 seconds. Python 3.12, `/tmp/desk-venv`. The previous 9 failures on `cc8350c5` and on this branch are included in the pass count. |
| Frontend `npm test` | 439 passed, 0 failed. `npx tsc --noEmit` passed. `npm run build` passed. |
| Ruff on the edited Python files | Passed. `git diff --check` passed. |

No GitHub Actions run, dependency change, model or provider switch, paid call, live account call, or deployment was used.

## Causes of the previous failures

These failed on this branch and on unmodified `main` at `fc3b8d2` unless noted. None were skipped.

- Office attachment fingerprint. `_fingerprint` drops empty flight and shopping review fields. The test hashed a hand-built copy that still contained them. The test now checks that the same message is stable, that the memory flag and the text change the hash, and that the office bytes still validate.
- Flight reprice phrase. Bare `同意新总价` does not select the stale card. The route returns `acted: false`, `kind: clarify`, and no `flight_booking`. The booking stays `reprice`. The test now asserts that refusal instead of expecting the card to change.
- Managed unadmitted origin. The fixture set `origin` to the unadmitted host before session create, so the create allowlist assertion threw and the job became `unknown`. `session_origin` stays `https://books.toscrape.com` for create. The approval request still uses the unadmitted origin, and the owner-required result is unchanged.
- Google composer renderer. Under this Node transform the fixture’s `require` returned an empty module for `useHomeTranscript`, and the collapsed home line is `HomeCaption` rather than a raw `assistant-latest` node. The fixture now supplies those two modules and checks that the summary appears once in the expanded conversation.
- Forget context. The route returns `{cleared: true, home_archived: false}`. The test now asserts both.
- Browser read timeout. The assertion was a one-line source regex. The timeout expression was already split across lines. The test loads `requestDeadline` and checks that `request()` arms 75 seconds for a browser observation and 12 seconds for an ordinary path.
- Today suggestion source string. The workspace redesign renders `MomentCard` from `TodayView`, not from `App`. `momentView` now decides one suggestion, a paused reason, or a reset, and the test checks that behavior. Today still mounts the card once.

## Screenshots

Desktop and 320px captures of the held rehearsal card, with no typed secret:

- `/opt/cursor/artifacts/owner-hold-desktop.png`
- `/opt/cursor/artifacts/owner-hold-narrow.png`
- `output/qa/2026-11-24-owner-page-handoff/desktop-hold.png`
- `output/qa/2026-11-24-owner-page-handoff/narrow-hold.png`

## Omissions

The synthetic `VerificationDriver` remains for API fences. There is no headed operating-system window, no hosted OpenAI desktop, no ordinary browser profile, and no merchant or live-account sign-in. The Pi update is not applied. The pull request is not merged and nothing is deployed.

## Closeout of the combined hold-card failure

`59547453` changes only `tests/test_owner_page_ui.py` and the two hold screenshots. Product files are unchanged from `32066b8b`. The combined failure on `8f580c83` happened because a Vite process from the other checkout was still listening on port 5190. The card that loaded had Hand back and the non-owner screen, and it did not mount the held typing control. The test now requires that listener to belong to the server it started, waits until Type on this page is visible, and opens Work & tools without reloading the connected page. Three consecutive runs passed in 27.81s, 27.77s, and 27.66s. The local rehearsal `cefe84e0` includes this test and passed 3061 backend tests with 1 skipped. This note is not part of that rehearsal.

**Next step** — The parent evaluates whether this pull request and the interrupted-task pull request are accepted. The Pi update from `92acac8e` to `b759950c` stays a separate device step. This pull request stays open.
