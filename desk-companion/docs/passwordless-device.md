# Group 2 · Automatic connection and Alice on Pi

6 November2026. The owner requested removing Sign in across Web, phone, native
and Pi. This supersedes the password-form UI and calendar-first device home.

## Connection boundary

`POST /api/session/connect` creates the same eight-hour HttpOnly, SameSiteStrict
owner cookie as a normal local session. `DESK_AUTO_OWNER` defaults to1. The
request must arrive directly from loopback with a loopback URL host and absent
or trusted local HTTP Origin. Forwarded headers, public origin configuration and
non-local requests cannot acquire this authority. Setting the option to0 disables
automatic owner entry. Existing paired-device access remains separate.

Shared `session.ts` coalesces bootstrap calls. An expired session can reconnect
without replaying an interrupted write. Offline failures keep mounted content
and unsent input; an invalid identity clears private data. ConnectionView offers
retry, desk address and existing pairing instead of username/password fields.
All three app shells and native setup use this path. The legacy password API is
retained for compatibility/recovery, with no application sign-in form.

This policy deliberately trusts the directly connected local workspace. It is
not anonymous ownership on a public service, and it does not approve computer
jobs, change Full access or grant paired devices owner-management privileges.

## Device and media lifecycle

DeviceHome shows the existing licensed Alice and persistent ConversationWorkspace.
Calendar, tasks, reminders and settings stay accessible through existing panels.
One conversation/voice client serves the device; no hidden duplicate assistant
owns a second microphone or socket. The avatar pauses when obscured/backgrounded.
The conversation pauses for external panels, but its own Camera & microphone
dialog must remain usable. Phone shares the scene-activity hook.

The Pi graphical session resolves the active release and opens the actual kiosk
instead of showing a credentials helper. Ordinary owner-initiated voice keeps
the configured provider; a providers-off QA fixture is explicitly separate.
Local media checks and explicit frame sharing retain their existing lifecycle.

WakeDetector loads a temporary keyword file during recognizer construction, so
verified read-only model weights need no write permission. The audio extra now
declares numpy explicitly. Configured/available wake detection is distinct from
positive keyword, human noise/AEC and microphone/speaker acceptance.

## Evidence

[Current QA](../../output/qa/2026-11-06-passwordless-device/verification.md) separates
local suites, rendered Web/phone/device checks, native first-screen evidence,
Pi deployment and real application acceptance. It also records missing Pi capture
hardware and the unsuccessful standalone synthetic Alice sample. No paid test is
implied by installing audio dependencies or showing the voice controls.
