# Group 2 · Current handoff

16 November 2026. Active checkout `/Users/tantalum/.codex/worktrees/agent-runtime-20261116/FYP`, branch `codex/agent-runtime-20261116`. Preserve other recovery checkouts, original data and private backups. Latest owner priority is frequent Pi automatic shutdown, on dormitory Ethernet; earlier deferral is revoked.

## Power investigation and present operation

After the owner unplugged/reconnected power, original pinned SSH identity authenticated through the existing VPS. Fresh kernel recorded 13 undervoltage episodes in the first 667 seconds, including after stopping the app container. No 3D kiosk was running. Previous-boot logs were absent because the vendor journal was volatile; the precise cause of earlier spontaneous red LEDs remains unproved. Supply negotiation is 5 V/3 A, and the owner has no spare 5.1 V/5 A supply. Do not label every relay failure as a shutdown.

A private off-device SQLite/config/vault backup is verified (17 files, 123 tables, schema 3). Persistent journal is now enabled with 64 MiB/7-day/5-second bounds. Temporary 1.5 GHz maximum CPU frequency retains the ondemand governor and voltage/current protection. With API restored, a bounded 480-second/97-sample trial passed without a new kernel undervoltage event or lost boot/SSH; sampled voltage 4.92584–4.96738 V. The recovery unit is enabled and read back, but next-boot/full-load/long-term acceptance is not claimed.

Pi API remains active at source 2c31f430. Pi-local Alice 3D autostart and cross-application container are held; camera/voice/output agents remain inactive. Mac/native operation was not changed by these power measures. Original autostart, CPU policy and rollback steps are retained. Do not re-enable heavy load before checking fresh power evidence.

Read [power QA](output/qa/2026-11-16-pi-power-recovery/verification.md), [machine summary](output/qa/2026-11-16-pi-power-recovery/results.json) and [maintenance/restoration notes](desk-companion/docs/pi-power-recovery.md). Private evidence: `~/.config/desk-companion/pi-power-20261116/`. Both bounded monitors finished; no new unattended diagnostic watcher was left running. The ordinary reconnecting owner relay remains available.

## Delivered software and accounts

PR #123 merged as 7d7ab9fa. Latest application source **2c31f430** was activated/read back on Mac 8831, Pi 8891 and the iPhone 17 Pro/iOS 26.5 Simulator, with matching frontend index/build-info. A3/version 9, protected files, original stores and Google connection versions retained. Native is a Simulator installation with a process-only Mac 8831 origin; no physical-iPhone claim. Pi display rendering remains unaccepted and is now deliberately held for power diagnosis.

[PR #124](https://github.com/tantalum666/FYP/pull/124) remains open/draft for managed browser execution, daily weather/speech/proactive/local-camera work and the deployment records. Managed browser stays disabled by default. Daily code adds the forecast tool, speech-only formatting hints, buffering, one compact task/posture cue and locally processed camera landmarks. Camera still needs first consent and personal calibration. See [daily QA](output/qa/2026-11-16-alice-daily-presence/verification.md) and [capability map](desk-companion/docs/personal-agent-status.md).

Mac and Pi independently completed Gmail/Calendar consent and actual bounded provider reads. Tokens were not copied. Microsoft personal-account human verification still prevents FYP registration/Graph consent; do not bypass CAPTCHA or reuse the expired device code.

## Validation and cost boundaries

Daily backend 2370 passed; later Live changes 30 focused checks, final follow-up scope 35, kiosk profile 2. Frontend 389/types/build/Ruff and actual desktop/phone flows passed. Local-model synthetic-camera lifecycle and 15 physical Mac observations passed without storing/sending frames; posture accuracy and long-term operation remain unaccepted. No CI.

Both paid rounds are CLOSED. Managed public-browser trial: one session, 51.731 seconds, independently matched prices, DELETE/GET404; usage absent, full US$1 reservation retained. Voice: fresh US$0.20/60 seconds, total 58.493 seconds, conservative cache-aware estimate US$0.11280236; task/HKO/A3 verified, but complete final weather speech was cut short. No additional paid calls authorized. Real owner browser takeover, merchant payment/ticketing, ongoing inbox tracking and full voice-quality acceptance remain open.

**One next step:** establish a reliable supply/cable/minimum-accessory comparison, then check new persistent power evidence before restoring normal frequency and the Pi display/container one at a time. Current mitigation is temporary; no permanent shutdown-fix claim.
