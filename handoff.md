# Group 2 Current Handoff

4 November 2026. **The owner resumed Pi work in the dorm.** Ethernet connects to the wall socket; power is the official Raspberry Pi 27W supply. There is no monitor. The owner chose safe shutdown and attaching the original SD card to the Mac. The original card has now been identified and inspected; a backed-up two-file recovery seed was verified and safely ejected. Owner confirmed reinsertion and power. No authenticated SSH result yet.

## Current Pi recovery

[QA](output/qa/2026-11-04-pi-dorm-ethernet/verification.md), [network contract](desk-companion/docs/pi-network-profiles.md), [relay/recovery contract](desk-companion/docs/pi-owner-relay.md). The first recovered boot was read back from the original card: wired DHCP, current trial/boot ID, exact owner /32 source rule and HK boot country all present. Direct SSH remained unavailable.

The optional owner VPS account/transport is validated from a Mac fixture, not yet from Pi. A later card capture showed empty relay files and cloud-init's write step already marked run, with no relay status/unit. Read-only ext4 inspection skipped pending journal recovery; do not diagnose physical SD failure from this alone. New verified bootcmd/runcmd recovery restores and reads back the complete managed payload before actual setup, resumes only this instance's command steps after interruption, and requires current result receipts before completion.62 local tests/Ruff pass.

The durable seed is currently prepared on the original card; all secret material/backups remain under `~/.config/desk-companion/pi5-dorm-ethernet-20261104/`. VPS changes are a dedicated restricted relay account/key and diagnostic-only HTTP logging; existing proxy/SSH/firewall/subscription routes are preserved. Unauthenticated nonce/stage hints supplement, not replace, pinned Pi SSH. Home Wi-Fi and classroom Wi-Fi/wired profiles remain; overseas relay availability is not a home-LAN requirement.

**Owner constraint:** no hotspot workaround or repeated blind SD/configuration trials. Finish the consolidated preparation/verification before the next physical boot. **Next:** boot the verified durable seed, observe actual stages, then authenticate the original Pi host identity before power/filesystem/app checks. Classroom wired, mainland return, full display and latest-app deployment remain unaccepted.

## Preserved hardware evidence

[PR73](https://github.com/tantalum666/FYP/pull/73), [31 October home QA](output/qa/2026-10-31-pi-home-resume/verification.md), [dedicated-device entry QA](output/qa/2026-10-31-pi-device-entry/verification.md). Home Wi-Fi, paired-key SSH, old app and Mac desktop passed then; those addresses/tunnels are not current observations. Classroom Wi-Fi is retained; Student/Halls autoconnect is disabled. Dorm wired acceptance remains open.

Pi-local Chromium previously caused undervoltage. The owner has now identified the official27W supply; fresh firmware/power/throttling readback and a bounded load test still remain. DeviceApp uses `?surface=device`; `?page=device` is management settings. Actual autostart last opened the welcome helper. Latest-main app/database migration, automatic kiosk and sustained touch/voice/arm acceptance remain unfinished.

## Unified software and preserved preview

PR74–77 and the Grok fixes are merged in main through PR83/85; [merge QA and receipt route](https://github.com/tantalum666/FYP/pull/85), [Grok review route](https://github.com/tantalum666/FYP/pull/83). Latest unified source is `/Users/tantalum/.codex/worktrees/grok-journey-compat-20261104/FYP` (main receipt abf6387). This recovery checkout is now on `codex/pi-dorm-network-recovery-20261104`, based on `codex/pi-home-resume-20261031`, and does not contain that latest app source.

The old preview/data/keys remain preserved in `/Users/tantalum/.codex/worktrees/personal-agent-20261031/FYP`; neither it nor Pi was upgraded by the merge. Normal OpenAI/Alice configuration and prior model evidence belong to that software handoff. All experiment budgets remain closed. No CI, model call or global Mac network change occurred. The narrowly scoped VPS additions are recorded above.
