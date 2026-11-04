# Group 2 Current Handoff

4 November 2026. **The owner resumed Pi work in the dorm.** Ethernet connects to the wall socket; power is the official Raspberry Pi 27W supply. There is no monitor. The owner chose safe shutdown and attaching the original SD card to the Mac. The original card has now been identified and inspected; a backed-up two-file recovery seed was verified and safely ejected. Earlier seeds were powered; the latest consolidated durable seed is now safely ejected and awaiting a new reinsertion/power confirmation. No authenticated SSH result yet.

## Current Pi recovery

[Current443 transport QA](output/qa/2026-11-05-pi-443-transport/verification.md), [earlier recovery](output/qa/2026-11-04-pi-dorm-ethernet/verification.md), [contract](desk-companion/docs/pi-owner-relay.md). Owner confirmed the durable boot. Matching hints reached setup_completed but reported direct VPS TCP unreachable; original Pi SSH is still unverified. The earlier empty-file recovery is no longer merely awaiting owner power confirmation.

The real Mac/VPS test had used the existing encrypted route, which was not equivalent to plain Pi→VPS22. A separate non-TUN client, forced to en0, now successfully authenticated the pinned VPS through443. Its only local forward targets the VPS SSH endpoint. Existing Mac proxy/DNS/TUN, original VPS proxy/SSH/firewall, and home/classroom/dorm profiles were retained.

The optional Linux ARM64 transport is pinned to the verified official v1.19.32 archive and binary hash.79 local checks/Ruff and a private actual-artifact package rehearsal passed. It adds one offline archive to the two seed files; real-card deployment has not occurred yet. Private material remains under `~/.config/desk-companion/pi5-dorm-ethernet-20261104/relay-transport/` and the associated protected bundle.

**Owner constraint:** no hotspot and no repeated blind configuration trials. **Next:** after the requested original-card return, identity-verify and write the already-tested443 package, then verify actual stages and the original Pi SSH identity. No claim of latest-app deployment, sustained power/desktop acceptance or classroom wired acceptance.

## Preserved hardware evidence

[PR73](https://github.com/tantalum666/FYP/pull/73), [31 October home QA](output/qa/2026-10-31-pi-home-resume/verification.md), [dedicated-device entry QA](output/qa/2026-10-31-pi-device-entry/verification.md). Home Wi-Fi, paired-key SSH, old app and Mac desktop passed then; those addresses/tunnels are not current observations. Classroom Wi-Fi is retained; Student/Halls autoconnect is disabled. Dorm wired acceptance remains open.

Pi-local Chromium previously caused undervoltage. The owner has now identified the official27W supply; fresh firmware/power/throttling readback and a bounded load test still remain. DeviceApp uses `?surface=device`; `?page=device` is management settings. Actual autostart last opened the welcome helper. Latest-main app/database migration, automatic kiosk and sustained touch/voice/arm acceptance remain unfinished.

## Unified software and preserved preview

PR74–77 and the Grok fixes are merged in main through PR83/85; [merge QA and receipt route](https://github.com/tantalum666/FYP/pull/85), [Grok review route](https://github.com/tantalum666/FYP/pull/83). Latest unified source is `/Users/tantalum/.codex/worktrees/grok-journey-compat-20261104/FYP` (main receipt abf6387). This recovery checkout is now on `codex/pi-dorm-network-recovery-20261104`, based on `codex/pi-home-resume-20261031`, and does not contain that latest app source.

The old preview/data/keys remain preserved in `/Users/tantalum/.codex/worktrees/personal-agent-20261031/FYP`; neither it nor Pi was upgraded by the merge. Normal OpenAI/Alice configuration and prior model evidence belong to that software handoff. All experiment budgets remain closed. No CI, model call or global Mac network change occurred. The narrowly scoped VPS additions are recorded above.
