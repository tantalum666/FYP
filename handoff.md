# Group 2 Current Handoff

4 November 2026. **The owner resumed Pi work in the dorm.** Ethernet connects to the wall socket; power is the official Raspberry Pi 27W supply. There is no monitor. The owner chose safe shutdown and attaching the original SD card to the Mac. The original card has now been identified and inspected; a backed-up two-file recovery seed was verified and safely ejected. Owner confirmed reinsertion and power. No authenticated SSH result yet.

## Current Pi recovery

[Recovery QA and read scope](output/qa/2026-11-04-pi-dorm-ethernet/verification.md), [network contract](desk-companion/docs/pi-network-profiles.md), [Mac access](desk-companion/docs/pi5-usb-mac.md). Exact mDNS lookup and passive matching against known Pi MACs found no Pi. The old classroom Ethernet address routes through the Mac's VPN and was not probed. Do not infer DHCP failure or campus isolation from discovery failure.

The read-only Linux capture recovered a wired DHCP lease outside the Mac’s directly attached network. It is saved evidence, not a current IP guarantee. The old guard denied that routed source; new tested source admits only the explicitly selected Mac IPv4/32 on eth0 and retains paired-key SSH. Guard events now save fresh boot ID/address; countryHK and bounded600-second setup discovery are prepared.29 local network tests and Ruff passed; two seed files read back exactly; three unrelated boot files unchanged; FAT readonly check0 and safe eject passed.

Linux readonly e2fsck returned4 while explicitly skipping journal recovery; needs_recovery and allocation/checksum differences remain. No original-Linux writes or offline repair. Fresh post-boot health must be checked. Private capture/seed/backups/observer are under `~/.config/desk-companion/pi5-dorm-ethernet-20261104/`; credentials never enter Git.

**Next:** obtain the owner’s power/activity and Ethernet LED observation. The current boot sent no observed packet; a physical-interface-bound attempt to the saved lease candidate timed out without authentication. If it remains unreachable, inspect the new boot status before another configuration change. [DraftPR87](https://github.com/tantalum666/FYP/pull/87) preserves the tested recovery source; it is not merged or deployed as the latest app. VPS management is reachable through the existing Mac route, but a Pi outbound relay is not prepared or verified.

## Preserved hardware evidence

[PR73](https://github.com/tantalum666/FYP/pull/73), [31 October home QA](output/qa/2026-10-31-pi-home-resume/verification.md), [dedicated-device entry QA](output/qa/2026-10-31-pi-device-entry/verification.md). Home Wi-Fi, paired-key SSH, old app and Mac desktop passed then; those addresses/tunnels are not current observations. Classroom Wi-Fi is retained; Student/Halls autoconnect is disabled. Dorm wired acceptance remains open.

Pi-local Chromium previously caused undervoltage. The owner has now identified the official27W supply; fresh firmware/power/throttling readback and a bounded load test still remain. DeviceApp uses `?surface=device`; `?page=device` is management settings. Actual autostart last opened the welcome helper. Latest-main app/database migration, automatic kiosk and sustained touch/voice/arm acceptance remain unfinished.

## Unified software and preserved preview

PR74–77 and the Grok fixes are merged in main through PR83/85; [merge QA and receipt route](https://github.com/tantalum666/FYP/pull/85), [Grok review route](https://github.com/tantalum666/FYP/pull/83). Latest unified source is `/Users/tantalum/.codex/worktrees/grok-journey-compat-20261104/FYP` (main receipt abf6387). This recovery checkout is now on `codex/pi-dorm-network-recovery-20261104`, based on `codex/pi-home-resume-20261031`, and does not contain that latest app source.

The old preview/data/keys remain preserved in `/Users/tantalum/.codex/worktrees/personal-agent-20261031/FYP`; neither it nor Pi was upgraded by the merge. Normal OpenAI/Alice configuration and prior model evidence belong to that software handoff. All experiment budgets remain closed. No CI, model call, global Mac network change or VPS change occurred in this recovery.
