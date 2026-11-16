# Group 2 · Current handoff

16 November 2026. Active checkout `/Users/tantalum/.codex/worktrees/agent-runtime-20261116/FYP`, branch `codex/agent-runtime-20261116`. Preserve other recovery checkouts, original data and private backups. Latest owner priority is frequent Pi automatic shutdown, on dormitory Ethernet; earlier deferral is revoked.

## Current owner direction and Pi state

17 November: owner rejected continued 1.5 GHz/display/container reduction. Normal maximum 2400000 kHz and original autostart/container settings were restored; recovery limit/marker/hold removed. Subsequent boot independently retained 2.4 GHz. Persistent diagnostic logs and private off-device backup remain. Restoring normal demand produced new undervoltage and loss of access again.

Found and fixed session.sh lacking executable permission: source metadata and installed launcher now executable, and regression directly invokes the preserved-permission script. Service/config restart receipts exist, but present physical rendering and sustained normal-load stability are not accepted.

A one-off RTC alarm for 17 November 00:04:43 HKT was written/read back, then normal poweroff was scheduled with no active jobs. A 370-second watch saw no automatic SSH return. The owner later unplugged/reconnected power. Crucially, the saved prior-boot tail shows an intermediate startup around 00:05, before that later manual recovery, with undervoltage at 5.888 seconds while the network was still down. This supports RTC wake followed by failed startup; it is not end-to-end recovery acceptance. Original EEPROM remains POWER_OFF_ON_HALT=0 / 2025-12-08. The proposed EEPROM rewrite/approval is withdrawn; a delayed acceptance must not trigger any flash.

The optional owned RTC renewer and service/timer are prepared and locally checked. The initial program/units were installed with the timer disabled for testing. Final early-start/30-second renewal activation has NOT been confirmed: the 18-attempt in-turn watcher ended without access, and the latest physical boot/state question is pending. No diagnostic/action watcher remains active; only the ordinary owner relay retries. Do not claim persistent automatic wake is enabled. No more planned poweroff or firmware changes.

Read [wake QA](output/qa/2026-11-17-pi-auto-wake/verification.md), [maintenance notes](desk-companion/docs/pi-power-recovery.md) and historical [power QA](output/qa/2026-11-16-pi-power-recovery/verification.md). Private scripts/receipts are in `~/.config/desk-companion/pi-auto-wake-20261116/` and the earlier `pi-power-20261116/`. The prepared `activate_auto_wake.py` is owner-authorized for the next reachable Pi: it leaves firmware/clocks/app performance unchanged, installs only the optional alarm renewer, verifies units and reads back a future alarm. Then verify renewal after 30 seconds and service/app state. Another future RTC alarm must not be overwritten.

## Delivered software and accounts

PR #123 merged as 7d7ab9fa. Latest application source **2c31f430** was activated/read back on Mac 8831, Pi 8891 and the iPhone 17 Pro/iOS 26.5 Simulator, with matching frontend index/build-info. A3/version 9, protected files, original stores and Google connection versions retained. Native is a Simulator installation with a process-only Mac 8831 origin; no physical-iPhone claim. Pi display rendering remains unaccepted; the owner-directed normal startup settings are restored.

[PR #124](https://github.com/tantalum666/FYP/pull/124) remains open/draft for managed browser execution, daily weather/speech/proactive/local-camera work and the deployment records. Managed browser stays disabled by default. Daily code adds the forecast tool, speech-only formatting hints, buffering, one compact task/posture cue and locally processed camera landmarks. Camera still needs first consent and personal calibration. See [daily QA](output/qa/2026-11-16-alice-daily-presence/verification.md) and [capability map](desk-companion/docs/personal-agent-status.md).

Mac and Pi independently completed Gmail/Calendar consent and actual bounded provider reads. Tokens were not copied. Microsoft personal-account human verification still prevents FYP registration/Graph consent; do not bypass CAPTCHA or reuse the expired device code.

## Validation and cost boundaries

Daily backend 2370 passed; later Live changes 30 focused checks, final follow-up scope 35, kiosk profile 2. Frontend 389/types/build/Ruff and actual desktop/phone flows passed. Local-model synthetic-camera lifecycle and 15 physical Mac observations passed without storing/sending frames; posture accuracy and long-term operation remain unaccepted. No CI.

Both paid rounds are CLOSED. Managed public-browser trial: one session, 51.731 seconds, independently matched prices, DELETE/GET404; usage absent, full US$1 reservation retained. Voice: fresh US$0.20/60 seconds, total 58.493 seconds, conservative cache-aware estimate US$0.11280236; task/HKO/A3 verified, but complete final weather speech was cut short. No additional paid calls authorized. Real owner browser takeover, merchant payment/ticketing, ongoing inbox tracking and full voice-quality acceptance remain open.

**One next step:** on the next confirmed reachable Pi boot, activate the prepared RTC renewal and independently read back the alarm advancing, timer/service state and normal CPU/app configuration. Preserve the full-performance preference. Automatic wake cannot guarantee successful boot during a supply collapse.
