# Pi temporary power recovery

17 November 2026. Owner explicitly rejects continued reduced performance and asks for powered-off automatic wake. Normal CPU maximum and app settings have been restored; the temporary hold below is historical. [Wake evidence](../../output/qa/2026-11-17-pi-auto-wake/verification.md) supersedes the prior reduced-load plan. [Earlier power evidence](../../output/qa/2026-11-16-pi-power-recovery/verification.md) remains valid within its recorded interval.

## 23 November 2026 readback failure

The installed helper cleared its previous deadline, wrote a replacement, then exited on the first differing read at 14:52:20 Hong Kong time. The previous boot’s last journal entry followed about 12 seconds later. The owner brought the Pi back at 15:16. The installed units then renewed the hardware deadline again. At 16:07 the approved helper update passed two normal timer firings on the original Pi, with matching Linux, PMIC and stored owner deadlines. See the [incident timeline, repair and deployment status](../../output/qa/2026-11-23-api-astra-team/pi-recovery/verification.md).

For an active owned alarm the revised helper uses Linux’s in-place wakealarm update. It retains the last verified future deadline during the operation, retries observation of a transient mismatch, and records the expected and observed values before reporting an error. It attempts to restore a still-valid earlier deadline only to an empty alarm slot. The period remains 30 seconds and the requested alarm lead remains 180 seconds. An explicit disarm clears the owned deadline. Unknown future deadlines remain with their owner.

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
