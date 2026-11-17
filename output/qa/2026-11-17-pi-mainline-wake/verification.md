# Group 2 · Pi release and RTC wake follow-up

17 November2026. Owner explicitly requests the latest Pi deployment and reports automatic restart still failing. Pinned original-device SSH via the existing VPS succeeded at uptime90.5seconds. No CI, model calls or firmware update. Preserve original Alice performance.

## Pi deployment accepted

The checked31-file delta from2c31f430 was transferred and hashed, applied to a separate immutable8c67ddbe release and all367manifest files reopened. Pi Python3.13.5 and executable session launcher checked. Zero active jobs/voice before activation. Private database/config backup verified; schema3/123tables, A3version9, connected-app grant versions and protected-file hashes unchanged. API health/build-info/index readback and default_browser_engine=managed with enabled/configured=true passed. Autostart now names the same release. Mac/native already run the same application source.

After the trial a different Pi boot again returned8c67ddbe, CPU maximum2400000kHz and an enabled/active RTC timer. This confirms deployment survives boot. A physical framebuffer capture failed after another relay loss; no new physical Alice animation or voice acceptance is inferred from API status.

## Why wake renewal was not working

Fresh device readback: desk-auto-wake.timer disabled/inactive, service static/inactive, no opt-in marker, empty hardware wakealarm. Only a historical one-shot alarm ownership record existed. Thus prior prepared source was not a continuously enabled recovery mechanism.

Installed the already reviewed program/units and opt-in marker; actual systemd verification passed. Service and timer enabled; initial alarm180seconds ahead. A later same-boot sample had advanced91seconds with167seconds remaining, proving actual periodic renewal. CPU maximum remained2.4GHz, original API/container/autostart retained. No software performance cap or EEPROM modification.

## Controlled shutdown and evidence limit

At17:49:12HKT, after checking no active computer/agent/voice work and a healthy SQLite store, temporarily stopped only the periodic timer (kept boot enablement), armed a90-second hardware alarm for17:50:42, synchronized storage and scheduled normal poweroff five seconds later.

Persistent logs show the original boot ended17:49:20. An intermediate boot begins17:50:53 and its retained log stops17:50:56 with undervoltage before network readiness. Another boot begins17:54:10; pinned SSH/API returned around17:55:07, with the new software and restored periodic timer. Its wake logs show renewal from17:54:14 onward. Later the relay failed again; current boot also repeatedly logged undervoltage. Missing complete journal tails prevent proving every intermediate action.

The owner answered that they were unsure whether they pressed/replugged power during17:49–17:55. Therefore **full autonomous recovery is not accepted**. Record alarm-following startup and later remote return separately; do not relabel manual/uncertain recovery as a passed automatic test. The earlier observer's provisional automatic flag was corrected in its saved result. The owner later confirmed the requested button-on recovery and no further intervention for the next five minutes; that later answer does not retrospectively validate the first trial.

## Earlier boot protection prepared

An intermediate failure can occur before the ordinary service phase. Updated the owned service to DefaultDependencies=no, After local-fs/remount, Before sysinit/user/display, with explicit shutdown conflict/order and WantedBy=sysinit.target. The existing timer continues30-second renewal with180-second lead. No planner, app settings or frequency limits change.

The first early-service-only change passed standalone verification but the actual paired Pi check caught an ordering cycle: timers implicitly order before their target service, while the old timer waited for sysinit. The guarded installer restored the original units; original periodic renewal remained active. The initial bounded watcher repeated this semantic failure; it is now corrected to retry transport failures only and stop on validation errors.

Both service and timer now opt out of default late ordering and explicitly run after local filesystems/before sysinit, retaining clean shutdown conflicts. Actual Linux paired verification returned0, and deliberately restoring the old timer recreated the exact cycle. Added Linux graph regression tests; Mac ran11RTC/launcher cases and skipped2Linux-only graph cases, with actual paired/mutated verification run on the owned VPS. No VPS unit was enabled. Guarded installation verifies both files together and rolls both back on failure. The corrected pair was later installed on Pi and read back at18:22:13HKT,180-second alarm lead, both DefaultDependencies=no, both enabled, timer active and CPU maximum2.4GHz. Unit hashes match source. The owner subsequently confirmed a manual button-on recovery and agreed not to touch power/buttons for the next five minutes. A second controlled trial was scheduled18:27:39 for normal poweroff around18:27:44 and hardware wake18:29:09. The220-second observer saw no return, so its bounded result remains a failure. Later the owner independently reported that the Pi had started by itself. Fresh pinned SSH then confirmed boot738c3f6a,8c67ddbe, active/enabled timer, matching paired unit hashes and2.4GHz maximum.

The later retained chain has multiple boot IDs. It includes a renewal at uptime4.179seconds even in a short interrupted boot, and another boot's last recorded alarm at18:36:18. The successful current boot start, inferred from its synchronized online UTC minus uptime, is approximately18:36:28. Its first alarm write completes4.680seconds after boot, before sysinit at6.454seconds. This verifies the earlier ordering on an actual boot and supports delayed autonomous recovery after repeated starts. It does not establish reliable single-attempt recovery or resolve the repeated undervoltage.

Some journal wall-clock labels precede network time synchronization and shift within a boot. Treat the listed raw first-entry timestamps as journal labels, not precise physical power-on instants. Use boot IDs/monotonic order and the synchronized uptime anchor for the stronger conclusions. The first trial's owner-uncertain attribution remains unaccepted; it is not retrospectively promoted by the later report. Physical screenshot retrieval again timed out at the relay; current physical avatar rendering remains unverified in this turn.

## Sources and artifacts

[Official RTC guidance](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#real-time-clock-rtc) describes alarms and low-power configuration. This target retains its original POWER_OFF_ON_HALT=0 and firmware2226a853; no withdrawn EEPROM proposal is revived. [systemd dependencies](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html) and [boot order](https://www.freedesktop.org/software/systemd/man/latest/bootup.html) support the explicit early-service ordering. Software wake cannot guarantee startup through inadequate/unstable power or a failure before a new alarm is armed.

Raw device/VPS journals, backups, transfer/activation scripts and observers: ~/.config/desk-companion/pi-mainline-wake-20261117. Runtime credentials, source bundles and firmware images are excluded from Git. Application release remains8c67ddbe; the OS-owned early-unit change is tracked separately. No background observer is to remain after closeout.

## Final result and next boundary

Latest application deployed and boot-persistent; periodic and early RTC renewal installed and boot timing verified; a delayed self-start is supported by the owner's report plus the alarm/boot chain. Stable recovery is still not accepted: kernel undervoltage recurs, later relay reachability is intermittent, and the intended short observation window failed. The normal policy leaves approximately150–180seconds until the next alarm after an unexpected halt, plus boot/network time; another interrupted boot can add another interval. No new shutdown trial is scheduled. All in-turn observers ended; no off-turn watcher/automation was created.
