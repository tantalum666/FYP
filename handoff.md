# Group 2 - Owner takeover on the same browser job

10 November 2026. Branch `cursor/owner-browser-takeover-c60c`, based on main. Offline only. No live JD or merchant login, no paid model call, no Pi or VPS change, and no CI. PR94 stays the merged browser baseline. Codex PRs #97, #94, #73, #87, #88 and the open Grok stack #95/#96/#99/#98 were not used as the base and were not modified.

## Done

An existing computer-use job that reaches a login, SMS/OTP, captcha, or payment-confirmation wall pauses in `owner_takeover`. Alice does not type or store a password, code, or card and does not submit payment. Only the owner session that admitted the job can take over and hand that same job back; paired devices and other logins get 403. Takeover and return use operation ids. A lost response is not success and retries the same id. Handing the job back restores its saved browser state and continues the same id. Success after a wall requires read-back plus evidence that the wall is gone. A job left in takeover past its deadline expires. Cancelling it stays cancelled.

Local fixture pages and a fake browser driver cover the wall. The job card has Take over and Hand back.

## Evidence

[QA](output/qa/2026-11-10-owner-takeover/verification.md). Contract: [computer use](desk-companion/docs/computer-use.md).

## Not done

This does not log into JD, pass a real captcha, pay, book, or send mail. The browser process is closed at the pause and restored from the saved state on return; it is not a live window left open on the Pi. Native Gmail and real merchant receipts remain separate.

## One next step

A live owner pass on the real JD verification page needs its own scoped session. Do not treat the offline fixture as that login.
