# Group 2 · Full performance restoration and RTC wake

17 November 2026 continuation of the owner's 16 November request. Owner rejects continued performance reduction and asks the Pi to restart after a powered red-LED shutdown. This supersedes the prior reduced-clock/display/container hold. No paid call or CI.

## Restored and checked

- Disabled the temporary recovery unit, removed its opt-in marker, and restored the supported CPU maximum to 2400000 kHz with ondemand retained. The first immediate sysfs read still showed the old value; a later write/read confirmed 2400000. A subsequent boot independently retained the restored maximum.
- Removed only the scoped app-container hold/drop-in, restored the backed-up autostart, restarted API/container and launched the kiosk. Returned service/config receipts establish that these were applied, not continued stability. Fresh undervoltage then reappeared and the relay was lost again.
- Persistent logs and private off-device backup remain. The previous boot ended after new undervoltage without a recorded orderly shutdown sequence in the retained tail. This is evidence of an abnormal interruption, not proof of one single electrical component's fault.
- New logs exposed `session.sh` lacking executable permission in the release. Corrected the source executable bit and the installed launcher; modified the regression to actually execute the preserved-permission copy rather than running it through an explicit shell. This affects restoration after boot, not the cause of undervoltage.

## RTC test and corrected interpretation

The Pi exposes its built-in `rpi-rtc`, and the initial wakealarm was empty. Hardware watchdog was already one minute; this is separate from powered-off RTC wake. Existing EEPROM has `POWER_OFF_ON_HALT=0`, boot version 2025-12-08 / 2226a853. No firmware change has been performed.

A one-off 120-second alarm was written and read back for **2026-11-16 16:04:43 UTC / 17 November 00:04:43 HKT**, followed by scheduled normal poweroff. Zero active computer/agent jobs were confirmed. A bounded 370-second connection check did not see automatic SSH return. The owner later manually power-cycled the Pi, so that reachable boot is not counted as automatic recovery.

The initial conclusion that the existing configuration could not wake was too strong. A later previous-boot tail records an **intermediate startup around 00:05 HKT**, before the later manual recovery request. Cloud-init reports 16:05:16 UTC at uptime 5.12 seconds, followed by kernel undervoltage at uptime 5.888 seconds while network interfaces still had no address. This timing is consistent with the RTC firing and startup then failing before remote access. It is not end-to-end automatic-recovery acceptance. A full boot-chain extraction subsequently failed when the relay dropped again; retain that limitation.

An EEPROM change was prepared but never applied: matching official 2 MiB image, verified Git blob, original/proposed configuration readback and only 41 changed bytes inside the config area. The installed firmware does not support A/B updates. **The proposed EEPROM approval was withdrawn after the intermediate boot was found.** Do not execute it even if a delayed reply accepts the old question. Keep the existing firmware and use the observed RTC capability.

## Optional RTC renewer

Added `scripts/pi/auto_wake.py` and two systemd units. The owner-opted-in service uses RTC time, refreshes a three-minute alarm every 30 seconds, and arms before the desk user/display services at boot. It does not reduce CPU/GPU limits or stop Alice. The hardware clock can fire after Linux stops; the systemd timer itself cannot run while the board is off.

Owned-alarm state is written atomically before hardware mutation, so interrupted renewal can recover. Another future alarm is never replaced or disarmed. Hardware readback mismatch fails rather than reporting success. Explicit disarm is available for intentionally staying off. Startup and continuing-operation failure before a fresh alarm is armed, and complete loss of RTC power, remain limitations; this does not repair undervoltage.

The first installation of the program/units passed real systemd verification but left the timer disabled for the one-off test. Final early-start/periodic activation is awaiting an authenticated connection; record its actual receipt below before claiming it enabled. The bounded in-turn activation watcher completed 18 failed attempts. The latest physical-status question is pending; no action watcher remains active. A future reachable boot must perform the prepared activation and read back the moving alarm, not assume it already happened.

## Validation and evidence

10 RTC cases cover renewal/disarm, unknown future alarms, an external replacement of our alarm, interrupted mutation, expired alarm, hardware readback failure and invalid delays. The direct-execution launcher regression also passed: **11 tests**, plus Ruff. No firmware binary, raw log, key or database enters Git. Private receipts/scripts are under `~/.config/desk-companion/pi-auto-wake-20261116/`.

Primary references: [official RTC guidance](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#real-time-clock-rtc), [EEPROM and A/B behavior](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-boot-eeprom), [A/B API](https://github.com/raspberrypi/utils/blob/master/rpieepromab/README.md). Official guidance describes supported mechanisms; actual target-device boot results are separately bounded above.

## Documentation/publication scope

Updated AGENTS, current product requirements, continuation entry/handoff, decisions, work log and power maintenance notes. Local `git diff --check` passed. All 13 added local links resolved; 16 selected code/test/document/result files had no credential-pattern matches. Matching firmware/recovery images and raw device logs remain private and are not committed. Persistent activation and a new full boot remain explicitly pending; publication does not upgrade that result.
