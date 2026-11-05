# Group 2 Current Handoff

5 November2026. **Dorm Pi is reachable and runs unified mainabf6387.** Actual schema1→3 migration preserved all original rows across32 business tables. After a later relay interruption, added dedicated-account liveness and a retrying Mac connector. Owner confirmed normal restart; a new boot ID, original Pi identity, persisted new service/schema, HTTP owner login/core APIs and VNC protocol all passed. Device-page rendering and management-panel open/close passed at1280×720 without console errors/warnings.

## Current Pi recovery

[Current443 transport QA](output/qa/2026-11-05-pi-443-transport/verification.md), [earlier recovery](output/qa/2026-11-04-pi-dorm-ethernet/verification.md), [contract](desk-companion/docs/pi-owner-relay.md). Owner confirmed the443 seed boot. Authenticated readback verified current-trial setup_completed and the pinned binary. Earlier direct22 failures are historical; the new path is verified. Home and classroom profiles remain; classroom wired still needs field acceptance.

The earlier Mac/VPS fixture used an encrypted route and did not prove plain Pi→VPS22. The fixed443 transport now passed actual Pi authentication. It serves only the owner's SSH destination. Existing Mac proxy/DNS/TUN, VPS proxy/firewall and local three-place profiles remain. The only later sshd change is20/3 client liveness for fyp-pi-relay; root's full effective configuration was checked unchanged. A verified stale session was stopped without touching other accounts.

The optional Linux ARM64 transport is pinned to the verified official v1.19.32 archive and binary hash.79 local checks/Ruff and a private actual-artifact package rehearsal passed. Real-card preparation changed only the two seed files and one offline archive. Ten managed payloads, three setup steps, original Pi fingerprint, unchanged home/wired profiles and three unrelated boot files passed independent readback; FAT check returned0. The changed Mac lease was re-read and its exact management /32 refreshed. Private material remains under `~/.config/desk-companion/pi5-dorm-ethernet-20261104/`; the active seed is `443-seed/current.json`.

**Owner constraint:** no hotspot, no repeated blind card trials, and continue software progress instead of repeated cabling questions. The private-config Mac relay launcher in Downloads/Desk-Companion-Pi5 retries every10seconds, recovered after the owner restart, and passed a SIGTERM cleanup check for both local forwarding ports. Original LAN/USB launchers remain.13 client boundary checks plus79 network/transport checks pass. A final launcher is running with local8891/5901; do not launch a duplicate or redo SD preparation.

## Preserved hardware evidence

[PR73](https://github.com/tantalum666/FYP/pull/73), [31 October home QA](output/qa/2026-10-31-pi-home-resume/verification.md), [dedicated-device entry QA](output/qa/2026-10-31-pi-device-entry/verification.md). Home Wi-Fi and classroom Wi-Fi passed on their original dates; fresh mainland/classroom field acceptance remains separate. Student/Halls autoconnect stays disabled. Dorm wired plus the443 management route now passed.

The first boot logged3 undervoltage episodes; the post-restart inspected interval logged11, all followed by normalization. Latest snapshot0x50000 has no active flags; firmware reported3000mA, an earlier EXT5V measurement was about4.81V. Owner confirms direct official27W power plus other devices and asks to prioritize software. Cause remains unconfirmed. No forced current override, warning suppression or heavy kiosk load. Root filesystem rw/SQLite quick_checkok; no I/O corruption seen in inspected kernel lines. DeviceApp is `?surface=device`; automatic kiosk, sustained power/touch/voice/arm acceptance remain open.

## Deployed software and rollback

Unified application tree matches mainabf6387 (remote rechecked). Frontend type/build and ARM64 isolated login/read/create/idempotent retry passed. Coherent backup was made on Pi and copied to Mac with matching SHA. Actual data migrated1→2→3 after successful rehearsals;32-table comparison passed. API service points to `/opt/desk-companion-releases/20261105-abf6387`, with30 offline hash-verified core wheels; current runtime remains `/home/desk/.local/share/desk-companion`. Reboot preserved the new service, schema and exact frontend. Old `/opt/desk-companion` and coherent backups remain; rollback requires restoring the old runtime and unit together, not starting old code against schema3. [Upgrade QA](output/qa/2026-11-05-pi-runtime-upgrade/verification.md). Browser verified the locked device display/management panel and primary sign-in route; authenticated API checks were separate. No paid voice or Pi-local Chromium was started.

**Backup warning:** the second Pi-only `20261105-before-activate-main-abf6387` copy has empty files after reboot and is not a rollback source. The first `20261105-before-main-abf6387` snapshot is verified on Pi/Mac and passed an actual old-app login/read rehearsal on a separate copy. A fresh schema3 stopped archive was synced, transferred and validated on Mac. Live identity/config bytes match the original Mac snapshot. Post-reboot full integrity passed274 source/frontend files and2,159 dependency files. Private `443-backup-final-verification.json` records the accepted copies; preserve the invalid copy only for diagnosis.

**One next step:** exercise ordinary conversation-to-supported-application execution/recovery on this deployed Pi with offline inputs. Keep paid speech, real camera/microphone/arm and heavy kiosk acceptance separate; closed model budgets stay closed.

## Unified software and preserved preview

PR74–77 and the Grok fixes are merged in main through PR83/85; [merge QA and receipt route](https://github.com/tantalum666/FYP/pull/85), [Grok review route](https://github.com/tantalum666/FYP/pull/83). Latest unified source is `/Users/tantalum/.codex/worktrees/grok-journey-compat-20261104/FYP` (main receipt abf6387). This recovery checkout is now on `codex/pi-dorm-network-recovery-20261104`, based on `codex/pi-home-resume-20261031`, and does not contain that latest app source.

The normal Mac preview/data/keys remain preserved in `/Users/tantalum/.codex/worktrees/personal-agent-20261031/FYP`; this Pi rollout did not switch that preview. Its OpenAI/Alice configuration and prior model evidence belong to the software handoff. No CI, model test or global Mac network change occurred. Private artifacts remain under the existing owner-private Pi recovery root and must not enter Git.
