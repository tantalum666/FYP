# Group 2 · Replacement-adapter stability check

Continuation of the current Pi deployment/wake task; reuse the focused reading and verified release. Owner replaced the power adapter/charger (not just the wall socket), then confirmed a short button-on recovery. Read current handoff/power contract/recent decisions and existing private monitor_remote.py/monitor_local.py in full; reused those read-only monitors for121samples across600seconds. No code/performance/firmware setting changes, no intentional reboot, no model test or CI.

Criteria: same boot through the run, actual2.4GHz configured maximum, Alice kiosk/API/application services active, API health at each sample, no new active undervoltage/throttle flags, current-boot kernel events distinguished using monotonic uptime. Sticky history alone cannot fail the monitoring interval, but startup warnings on the replacement adapter are recorded separately. Board ADC is sampled, not a laboratory voltage measurement.
