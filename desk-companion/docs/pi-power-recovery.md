# Pi temporary power recovery

17 November 2026. Owner explicitly rejects continued reduced performance and asks for powered-off automatic wake. Normal CPU maximum and app settings have been restored; the temporary hold below is historical. [Wake evidence](../../output/qa/2026-11-17-pi-auto-wake/verification.md) supersedes the prior reduced-load plan. [Earlier power evidence](../../output/qa/2026-11-16-pi-power-recovery/verification.md) remains valid within its recorded interval.

## Current restore and wake state

The recovery CPU unit is disabled, its marker removed and the supported maximum is 2400000 kHz. The container hold/drop-in is removed and original autostart restored. The launcher is now executable. API/container/kiosk restart receipts were obtained, but the Pi subsequently lost remote access again; do not claim present physical rendering or sustained normal-load stability.

A one-off RTC test has evidence of an intermediate startup followed by undervoltage before the network came up. No EEPROM change was made. The prepared optional `desk-auto-wake.service`/timer renew an owned alarm every 30 seconds with a 180-second lead; early arming is ordered before user/display services. Persistent activation is not yet confirmed. An active RTC alarm can outlive Linux, whereas a timer cannot execute while the board is off.

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
