# One reminder after a followed thread receives a reply

25 November 2026. Grok Bot. Source baseline `main` `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d` (PR #157). This branch was cut from that commit. The tested product and tests are `3b2881a38a1355e53e600e4ce98f65df61d2e890`. A later commit only removes an intermediate debug screenshot. Pull requests #158 and #159 were not checked out, stacked, or modified.

## What was read

- `AGENTS.md`, `product.md` (current sections), `handoff.md`, the latest decision-log and work-log entries.
- `research/2026-11-18-always-on-personal-agent.md` (the named journey), `desk-companion/docs/official-text-sessions.md` (session and function boundaries), `proactive-research.md`, `mail-thread-followup.md`, `mailbox-journey.md`, `reply-owed.md`, `assistant-permissions.md`, `ui-copy.md`, and `personal-agent-status.md`.
- `output/qa/2026-11-24-continuity/verification.md` (inbox assistance and local mail cues) and the mail-related closeout in `output/qa/2026-11-11-grok-review/verification.md`.
- Current follow-up, inbox, quiet-hours, draft, and permission code on this tip, including the workspace navigation from PR #157.

The existing poll already stored one notice and task evidence. Chat and the task did not let the owner open that reply and choose a draft. No second scheduler or model loop was added. Official Agents Automations remain the documented place for a future scheduled model run. This slice does not call one.

## Implemented

On a thread the owner has chosen to follow, one new incoming reply raises one reminder on that same task. Chat and the task show it. Inbox can open the task. Quiet hours hold publication until they end. The owner can reread the original message. That text is not stored as a memory, in task evidence, or in the read receipt. Draft a reply appears only after the owner asks. Saving the draft does not send. Check again does not send, including when an earlier send is unknown. Dismissing one reminder leaves another. A failed read is not a confirmed new reply. A message from another thread is refused.

The owner can complete this on Work & tools with the local mail sample. The sample is labeled “Not a live mailbox.” A synthetic Gmail provider uses the same reminder and returns a snippet only for an explicit read. Neither is live-mailbox acceptance. Models stay GPT-6.2 Sol, GPT-Live 1.1, and A3 v9. Nothing was deployed. No GitHub Actions run was started.

## Locally verified

Focused backend, from `desk-companion` with `PYTHONPATH=backend` and `/tmp/desk-venv/bin/python -m pytest`:

- `tests/test_mail_reply_reminder.py` and `tests/test_mail_followups.py`: 46 passed.
- `tests/test_mail_reply_reminder.py` and `tests/test_mail_reply_ui.py` after the final card copy: 13 passed.

Browser, headless Chrome, `tests/test_mail_reply_ui.py`: the Tasks page followed the local venue sample, showed one reminder, read “Friday after 3 still works for me.”, offered the draft editor only after Draft a reply, and saved a draft that says nothing was sent. The card’s horizontal overflow was 0 at 1440×1000 and 320×740.

![Desktop task card](desktop-1440.png)

![Narrow task card](narrow-320.png)

Frontend `npm test`: 438 passed, 2 failed. The failures are not from this slice:

- `tests/browser-workflow.test.ts` expects `.includes(path) ? 75000 : 12000`. `api.ts` already had extra conditions between `includes(path)` and the timeout. This diff adds four error strings only.
- `tests/moments.test.ts` expects `<MomentCard` in `App.tsx`. `App.tsx` was not edited.

`npx tsc --noEmit` passed. `npm run build` passed (Vite 8.3.5; existing chunk-size warning). Ruff on the edited Python files passed.

Full backend, same interpreter, `PYTHONPATH=backend /tmp/desk-venv/bin/python -m pytest -q --tb=line -p no:cacheprovider`: **3059 passed, 9 failed, 1 skipped**, 1016.16 seconds. The 9 failures were reproduced on unmodified `main` `fc3b8d2` in this environment and were not changed here:

- `test_chat_attachments.py` office fingerprint mismatch
- `test_conversation_flight_booking.py` missing `flight_booking`
- `test_google_refresh_chat.py` `useHomeTranscript` is not a function under Node 22
- `test_managed_browser.py` state `unknown` instead of `failed`
- `test_omni_conversation.py` forget response also includes `home_archived`

The skipped test is the suite’s existing skip, not this slice.

## Not claimed

Not merged. Not deployed. Not a live Gmail or Outlook acceptance. Not a sent message. Not shopping, booking, or automatic execution. Paid reasoning was not used. The Pi update is a separate device step.
