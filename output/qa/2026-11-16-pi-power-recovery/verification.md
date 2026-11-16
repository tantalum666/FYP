# Group 2 · Pi shutdown diagnosis and temporary mitigation

16 November 2026, dormitory Ethernet. The owner explicitly resumed power diagnosis and reported unplugging/reconnecting power before the present boot. This known manual power-cycle is separate from the earlier owner-observed spontaneous red LED. No paid models, CI, firmware upgrade, voltage/current override, warning suppression, stress load or filesystem repair.

## Fresh evidence

- Original pinned Pi SSH identity authenticated through the existing VPS. No network, card or relay configuration replacement.
- Kernel logged 13 undervoltage detections between uptime 10.08 and 667.39 seconds. Events continued after the app container was stopped at about 178 seconds; the 3D kiosk was not running. Snapshot `0x50000` records past undervoltage/throttling and does not mean the sampled instant was currently undervolted.
- Supply negotiation reports 3000 mA. Fresh fixed PDOs advertise 5 V/3 A, 9 V/3 A, 12 V/2.5 A and 15 V/2 A. Capability is not measured current draw. No USB overcurrent was reported; only USB root hubs enumerated, which cannot exclude accessories that only draw power.
- Temperature in the observed interval rose from 48.8 to about 67.5 degrees C. More than 7 GB memory was available; swap unused. No observed OOM, current kernel filesystem error, recorded power-key event or matching shutdown automation in the inspected cron/autostart/unit files. These limited negative findings cannot reconstruct the lost previous boot.
- The vendor journal configuration was `Storage=volatile`; previous-boot retrieval had no persistent journal. NTP corrected the wall clock after startup, so use boot ID and monotonic uptime for event ordering. Empty pstore did not provide a prior crash cause.

## Completed safeguards

- Backed up the live SQLite database using its backup API, plus vault/config/credentials and user unit files, to a private archive on the Mac. All 17 file hashes verified; independent SQLite quick_check passed, schema 3, 123 tables. No secrets or archive included in Git.
- Enabled persistent journals with a 64 MiB limit, 7-day retention, and 5-second sync. Restart/flush succeeded and actual system/user `.journal` files were read back. This improves future evidence; a sudden electrical loss can still drop the last unsynced records.
- With zero pending computer/agent jobs, stopped the application container. Its exit 143/failed state came from the intentional stop; it is not proof it crashed before diagnosis. Reset that failure after recording it. A dedicated hold/drop-in prevents a dependency from restarting it. The FYP autostart file was backed up and disabled with both the existing desktop flag and standard `Hidden=true`; unrelated desktop services remain.
- Briefly stopped the API/camera/voice/output services for the minimum application-load comparison. No new undervoltage was logged in that approximately four-minute phase, but the prior spike could have occurred between samples; long-term acceptance is not implied.
- Applied a reversible maximum CPU frequency of 1.5 GHz, a frequency already supported by this Pi. Original 2.4 GHz maximum and ondemand governor are saved privately. Governor, voltage, current limit and firmware unchanged. Restored the API and verified `/api/health` and build-info at the usual Pi preview port; container/3D display remain held.

## Completed bounded observations

The first streamed 8-minute observation completed with 97 samples, unchanged boot identity and SSH exit 0. Sampled input ranged 4.7905–4.96604 V; kernel events independently caught short undervoltage episodes. It includes the transition from API-running to API-stopped, so it is not a uniform workload benchmark.

The second trial completed **480 seconds, 97 samples, SSH exit 0**, with API running and maximum CPU frequency 1.5 GHz throughout. Sampled input was **4.92584–4.96738 V**. No new kernel undervoltage event occurred during the trial, boot ID remained unchanged, and the final database quick_check/schema and protected-file hashes still matched. No shutdown was observed during this connected trial. [Machine-readable summary](results.json).

Installed a reversible `desk-power-recovery.service` plus root-owned opt-in marker. It sets only `scaling_max_freq`, before the desk user's services; systemd unit verification, enabled/active state and actual 1500000 kHz readback passed. It does not change the governor, boot firmware, voltage/current limits or watchdog. **No reboot was performed to test next-boot behavior.** Restore instructions and exact held services are in [the maintenance notes](../../../desk-companion/docs/pi-power-recovery.md).

This is a reversible mitigation trial, not a proven permanent shutdown repair. The owner has no alternate 5.1 V/5 A supply available. A reliable supply/cable/minimum-accessory comparison and later full application-load acceptance remain necessary before claiming the physical issue solved.

## Sources and private evidence

Official [Pi power guidance](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#power-supply) and [USB Power Delivery on Pi 5](https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-009856-WP-1-USB%20Power%20delivery%20on%20Raspberry%20Pi%205.pdf) distinguish a recommended 5 A supply from supported 3 A operation with lower-power peripherals. A 3 A label alone does not prove a fault; repeated live undervoltage is the relevant finding here.

Private receipts/scripts and raw logs: `~/.config/desk-companion/pi-power-20261116/`. Pi reversible state: `~/.local/state/desk-companion/power-20261116/`, hold `~/.local/state/desk-companion/power-recovery-hold`, root diagnostics `/var/lib/desk-power-diagnostics/`. Only summarized nonsecret evidence belongs in this repository.

## Closeout

Updated AGENTS, product, decision log, handoff, continuation entry, Pi first-boot pointer, power maintenance notes, previous delivery QA and work log. Validation for this maintenance change consists of actual device/readback/backup/journal/unit checks and Markdown link/diff/secret-scope checks; no application code changed in this power slice, no new unit suite was run, and no CI was used. Git publication is distinct from the already installed source 2c31f430 and from physical stability acceptance.

Closeout checks: `git diff --check` passed; all 24 added local Markdown links resolved, and the selected 12 documentation/result files contained no credential-pattern matches. No GitHub workflow files are present or added. Private archives and raw logs are excluded.
