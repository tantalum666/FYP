# Group 2 · Passwordless Alice device work

6 November2026. Owner requests removing Sign in across web/phone/native/Pi and asks for Alice and voice on Pi. Active branch codex/passwordless-alice-device-20261105 is a separate checkout based on mainabf6387.

## Current implementation

Shared session.ts coalesces automatic owner-session bootstrap/recovery. Backend /api/session/connect grants ordinary expiring owner cookies only on the directly connected local workspace. Public/forwarded requests and paired-device privileges retain their boundaries. App/Phone/Device password forms and Sign out controls are removed. DeviceHome renders the existing Alice beside persistent ConversationWorkspace; calendar/tasks/settings reuse existing panels. No second voice/model/approval implementation.

Pi currently has no enumerated capture hardware, only HDMI playback. Existing model files are root-owned/read-only. WakeDetector now uses a temporary keyword file instead of modifying installed weights. The deployed core environment still needs audio extras and wake configuration. Mac browser media is a separate input/output path. Session launcher source now opens the active release kiosk instead of the credentials helper.

## Validation in progress

Full backend1789/frontend324, typecheck/build/Ruff passed. Web/device/phone browser checks passed, including drafts, local mic and own-media-dialog lifecycle. Fresh iPhone17Pro simulator build/first-screen succeeded; native touch/keyboard remains open. [Current QA](output/qa/2026-11-06-passwordless-device/verification.md). QA API8831/Vite5190 use separate providers-off state, not the owner's Pi service. Pi rollout and real cross-app acceptance are in progress. No paid model call.

## Existing Pi and backups

Last deployed Pi source is mainabf6387/schema3. Mac forwarding8891/5901 and original host pin are retained. Owner-private pi5-dorm-ethernet-20261104 contains pi_remote.py, importing the pinned relay helper from the preserved recovery checkout. Valid old schema1/current schema3 archives are on Mac. The second Pi-only pre-activation copy is invalid: do not use it. Low-voltage records remain; owner prioritizes software over repeated cabling questions. Network source is in [draftPR87](https://github.com/tantalum666/FYP/pull/87), unmerged; do not merge it as a side effect.

## Deferred — spontaneous red LED

Owner reports two spontaneous red-LED events before any unplugging. Their recovery method was removing/reconnecting power, not orderly button shutdown; previous normal-reboot claims must be corrected. Owner confirmed the label says5V/3A, then explicitly paused this investigation and prioritized Pi software, especially cross-application operations. The bounded power monitor has ended. Do not resume power diagnostics or ask further cabling questions. The Mac synthetic Alice clip created a detector but did not detect the keyword; do not claim wake accuracy or detection acceptance.

## Next

Complete Pi's rootless application runtime and a real Chromium/Calc/Writer/PDF continuation/recovery case, together with the backed-up passwordless/Alice rollout. Previous local suites1789/324 and native build/first-screen checks passed; no paid-model call. Record actual target results and update contracts/publication at closeout.
