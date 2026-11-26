# Pi temporary power recovery

17 November 2026. Owner explicitly rejects continued reduced performance and asks for powered-off automatic wake. Normal CPU maximum and app settings have been restored; the temporary hold below is historical. [Wake evidence](../../output/qa/2026-11-17-pi-auto-wake/verification.md) supersedes the prior reduced-load plan. [Earlier power evidence](../../output/qa/2026-11-16-pi-power-recovery/verification.md) remains valid within its recorded interval.

## 26 November 2026 · Dark status light

The original device still had its automatic wake timer active at 20:59 Hong Kong time. SoC temperature was 84.8 °C; an earlier boot had reached 85.35 °C with firmware throttling. The kiosk returned application data at 21:39:57. Later the owner reported that the red light had gone out and automatic return was absent. [Incident timeline and verification](../../output/qa/2026-11-26-pi-account-and-power/verification.md).

On Pi 5 the same indicator shows green in normal operation and red in ordinary powered standby. Record the screen and both LED colours before interpreting their absence. If the board has gone dark and has cooled, a single short press with the USB-C supply still connected distinguishes a responsive standby board from one requiring more investigation. On the next boot, correlate the previous journal’s last shutdown or alarm event with the PMIC reset information, voltage warnings, and whether someone used the button or restored power. Record a genuine unattended recovery only when the operator confirms there was no intervention. [Pi 5 LEDs](https://www.raspberrypi.com/documentation/computers/configuration.html#raspberry-pi-5-and-500-leds) · [Power button and RTC](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#real-time-clock-rtc).

The owner later restored the same power connection. The previous boot had nine kernel undervoltage warnings and a verified alarm deadline three minutes beyond its final renewal. The journal ended without an orderly shutdown. On return the bootloader reported 900 mA, and the Pi 5 device-tree property `/proc/device-tree/chosen/power/power_reset` read zero. After network time synchronized, the PMIC, Linux and the owner record agreed again. On this same new boot, an ordinary-load read reached 85.35 °C with active firmware throttling. No new kernel undervoltage warning had appeared by the 23:20 read. Use uptime to place the current boot when its early journal still carries the previous saved time. [Matched boots, power readings and scope](../../output/qa/2026-11-26-pi-return/verification.md).

## 23 November 2026 readback failure

The installed helper cleared its previous deadline, wrote a replacement, then exited on the first differing read at 14:52:20 Hong Kong time. The previous boot’s last journal entry followed about 12 seconds later. The owner brought the Pi back at 15:16. The installed units then renewed the hardware deadline again. At 16:07 the approved helper update passed two normal timer firings on the original Pi, with matching Linux, PMIC and stored owner deadlines. A new boot at the 21:12 independent read retained the installed helper and original rollback backup and again confirmed an enabled alarm 162 seconds ahead. See the [incident timeline, repair and deployment status](../../output/qa/2026-11-23-api-astra-team/pi-recovery/verification.md).

For an active owned alarm the revised helper uses Linux’s in-place wakealarm update. It retains the last verified future deadline during the operation, retries observation of a transient mismatch, and records the expected and observed values before reporting an error. It attempts to restore a still-valid earlier deadline only to an empty alarm slot. The period remains 30 seconds and the requested alarm lead remains 180 seconds. An explicit disarm clears the owned deadline. Unknown future deadlines remain with their owner.

The subsequent clock-epoch helper was separately approved, installed on the original Pi and independently read back after two normal timer firings. Loss of RTC calendar time invalidates prior-generation fallback dates. The helper restores only an owned deadline within the supported 900-second horizon and rejects a known backwards clock jump. Both successive installed helper hashes, distinct rollback copies, normal firings and offline clock-failure cases are recorded in the [cross-boot and differential evidence](../../output/qa/2026-11-23-api-astra-team/pi-recovery/verification.md#approved-clock-domain-helper-rollout).

## Current restore and wake state

The recovery CPU unit and container hold were removed in the previous recovery work. The 17 November boot check covered release `8c67ddbe`. On 18 November the normal application and autostart entry moved to `c607759e`. The device compositor showed Alice on the connected kiosk page. The software ceiling remained 2400000 kHz and the RTC timer stayed enabled and active with matching unit files. This application rollout supplies a single displayed frame. Long-run power and animation stability remain open. [Rollout readback](../../output/qa/2026-11-18-three-end-rollout/verification.md).

A one-off RTC test has evidence of an intermediate startup followed by undervoltage before the network came up. No EEPROM change was made. The prepared optional `desk-auto-wake.service`/timer renew an owned alarm every 30 seconds with a 180-second lead; early arming is ordered before user/display services. Persistent activation was subsequently confirmed17November: service/timer enabled, real moving alarm and timer recovery on a later boot. [Follow-up evidence](../../output/qa/2026-11-17-pi-mainline-wake/verification.md). The first trial cannot establish autonomous recovery because the owner cannot exclude manual intervention; startup undervoltage persists. The corrected early service/timer pair was subsequently installed and its hardware alarm/configuration read back; actual boot timing now shows the alarm finishing at4.680seconds, before sysinit6.454seconds. A later owner-reported self-start and corresponding alarm/boot chain establish delayed autonomous recovery; repeated undervoltage and loss of access still prevent a stable-recovery claim. An active RTC alarm can outlive Linux, whereas a timer cannot execute while the board is off.

After successful installation, intentionally staying off requires disabling both units and disarming the owned alarm with `sudo python3 /usr/local/lib/desk-companion/auto_wake.py disarm`, then removing `/var/lib/desk-auto-wake/enabled`. A foreign future RTC alarm is preserved. No voltage/current protection is disabled. If the board fails before a new alarm is armed, or loses RTC power, this feature cannot guarantee a restart. The EEPROM proposal is withdrawn; a delayed acceptance must not trigger it.

## Historical reduced-load state — removed at owner request

| Item | Read-back state |
|---|---|
| API | Source 2c31f430, active, health/build-info reachable through the existing relay |
| CPU | ondemand governor retained; maximum temporarily reduced from 2400000 to 1500000 kHz |
| Boot mitigation | `desk-power-recovery.service` enabled/active, unit verified; next reboot not tested |
| Pi-local Alice display | FYP autostart disabled, kiosk not running; installed release/profile preserved |
| Cross-application container | Inactive, gated by an explicit recovery hold; no in-flight job was interrupted |
| Camera/voice/output agent units | Inactive before/after the comparison; not enabled as part of recovery |
| Logs | Persistent, capped at 64 MiB, retention 7 days, sync 5 seconds |
| Data | Private off-device backup verified; current SQLite quick_check OK, schema 3, protected files unchanged |

The historical reduced-clock API trial passed eight minutes without new kernel undervoltage. It did not establish full-load, long-running or next-boot reliability. Owner has only the current supply. A 3 A supply can support a Pi 5 with lower-power peripherals; the amperage label alone is not a diagnosis.

## Historical mitigation configuration ownership

These are scoped maintenance changes on this owner's Pi, not defaults silently applied to every installation:

- `/etc/systemd/journald.conf.d/90-fyp-power-diagnostics.conf`; prior same-name file, if any, preserved under `/var/lib/desk-power-diagnostics/`.
- `/etc/systemd/system/desk-power-recovery.service`, guarded by `/var/lib/desk-power-diagnostics/cpu-limit-enabled`; the original CPU policy snapshot is `cpu-before.json` in that directory. The unit writes only the supported maximum frequency and checks the result.
- `/home/desk/.local/state/desk-companion/power-recovery-hold` and `~/.config/systemd/user/desk-applications.service.d/90-power-recovery.conf` prevent a backend dependency from automatically restarting the container.
- `~/.config/autostart/desk-companion.desktop` retains the current release path but has `X-GNOME-Autostart-enabled=false` and `Hidden=true`. Its original is saved at `~/.local/state/desk-companion/power-20261116/autostart.desktop`.

Network profiles, original SSH identity, VPS transport, API data, provider settings and A3 were not replaced. Do not expose private logs, vault/config backup or the SD image in Git.

## Restoration record and future comparison

The owner-directed restoration has been applied: CPU marker removed, recovery unit disabled, original maximum restored through cpufreq. Persistent logs remain. Confirm the actual live state after each new boot; do not reapply a performance limit merely because the historical unit file remains on disk.

The scoped container hold/drop-in was removed and the desk user manager reloaded; the saved autostart matched the current release. API/container/display restart receipts were recorded. Do not restart camera/output units merely because they exist, and do not silently restore the rejected performance limit after another voltage warning. Capture the new evidence and honor the current owner preference.

The previous power-off cause remains unresolved because the old logs were volatile. A future red LED must be distinguished from a dark screen or lost relay using persistent journal, boot ID and owner observation. A normal power-off/restart should be performed through the operating system when it is reachable; avoid using repeated abrupt unplugging as a diagnostic loop.

## Early service/timer ordering

Both units must opt out of default late boot dependencies. A timer is implicitly ordered before its target service; moving only the service before sysinit while leaving its timer after sysinit creates a cycle. The pair runs after local filesystems/remount, before sysinit/user/display, with explicit shutdown conflicts. The service is enabled under sysinit.target; the existing timer keeps its normal renewal cadence. Paired Linux verification and an intentionally restored old timer distinguish the corrected graph from the regression. The guarded installer restores both files on verification failure; no rejected graph remains installed.

The renewal service is a oneshot: inactive between successful runs is expected. Check the enabled/active timer, last successful alarm write, actual hardware deadline and ownership receipt together.

## Replacement adapter,17November

The owner replaced the charging head and requested a normal-performance check. The planned600s observation stopped on SSH timeout after485s/98samples.18samples contained active undervoltage/throttling0x50005; board ADC4.647–4.939V, temperature47.7–77.9°C. CPU maximum remained2.4GHz and all98local API probes succeeded before interruption. The current-boot kernel also has a new warning after the observation's monotonic start, not just sticky history. The replacement power path is not accepted as stable.3000mA is the reported available capability, not measured draw or proof of a specific defective component. [Detailed bounds](../../output/qa/2026-11-17-pi-supply-check/verification.md). No deliberate reboot or software configuration change occurred.
