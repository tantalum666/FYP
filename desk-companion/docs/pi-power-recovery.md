# Pi temporary power recovery

16 November 2026. Owner resumed automatic shutdown diagnosis on dormitory Ethernet. [Fresh evidence and limits](../../output/qa/2026-11-16-pi-power-recovery/verification.md) supersede older instructions deferring this work. Do not restore high load simply because SSH returns.

## Active device state

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

The restored API passed an eight-minute reduced-clock observation without new kernel undervoltage. This does not establish full-load, long-running or next-boot reliability. Owner has only the current supply; negotiated 3000 mA and repeated undervoltage make a reliable supply/cable/minimal-accessory comparison the next physical step. A 3 A supply can support a Pi 5 with lower-power peripherals; the amperage label alone is not a diagnosis.

## Configuration ownership

These are scoped maintenance changes on this owner's Pi, not defaults silently applied to every installation:

- `/etc/systemd/journald.conf.d/90-fyp-power-diagnostics.conf`; prior same-name file, if any, preserved under `/var/lib/desk-power-diagnostics/`.
- `/etc/systemd/system/desk-power-recovery.service`, guarded by `/var/lib/desk-power-diagnostics/cpu-limit-enabled`; the original CPU policy snapshot is `cpu-before.json` in that directory. The unit writes only the supported maximum frequency and checks the result.
- `/home/desk/.local/state/desk-companion/power-recovery-hold` and `~/.config/systemd/user/desk-applications.service.d/90-power-recovery.conf` prevent a backend dependency from automatically restarting the container.
- `~/.config/autostart/desk-companion.desktop` retains the current release path but has `X-GNOME-Autostart-enabled=false` and `Hidden=true`. Its original is saved at `~/.local/state/desk-companion/power-20261116/autostart.desktop`.

Network profiles, original SSH identity, VPS transport, API data, provider settings and A3 were not replaced. Do not expose private logs, vault/config backup or the SD image in Git.

## Restoration after stable-power verification

First read current boot/kernel evidence and preserve the existing backup. A future operator should confirm the intended original maximum against the saved snapshot and actual supported CPU range. Remove the CPU marker, disable the recovery unit, then restore the recorded maximum through cpufreq; do not invent a voltage/current override. Keep persistent logging for the subsequent acceptance check.

Remove only the recovery container hold/drop-in and reload the desk user's systemd manager. Restore the saved FYP autostart only if its current release still matches the intended deployment. Start the API, then the container, then the Pi-local display individually, checking for new kernel undervoltage after each. Do not restart camera/output units merely because they exist. If any new undervoltage appears, return to the recorded reduced-load configuration and stop increasing load.

The previous power-off cause remains unresolved because the old logs were volatile. A future red LED must be distinguished from a dark screen or lost relay using persistent journal, boot ID and owner observation. A normal power-off/restart should be performed through the operating system when it is reachable; avoid using repeated abrupt unplugging as a diagnostic loop.
