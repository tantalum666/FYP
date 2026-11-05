# Group 2 · Current entry

5 November2026: dorm Pi access is restored through the fixed443 relay, and unified mainabf6387 is actually deployed. Original host identity, real schema1→3 migration,32-table data preservation, reboot persistence and Mac-side HTTP/VNC checks passed. The owner requires mainland homeWi-Fi, classroomWi-Fi+wired, dormwired, and rejects hotspots/repeated blind card trials.

Read [handoff](handoff.md), [network QA](output/qa/2026-11-05-pi-443-transport/verification.md), [runtime update QA](output/qa/2026-11-05-pi-runtime-upgrade/verification.md) and [relay contract](desk-companion/docs/pi-owner-relay.md).92 focused local checks passed. A later stale relay was handled with dedicated-account liveness and a retrying Mac connector; owner confirmed normal restart and the original Pi/new app were authenticated again. Current access is usable; do not restart SD preparation. Keys/backups remain private.

Next: exercise the deployed Pi's ordinary conversation-to-supported-application workflow and recovery using offline inputs first. Paid voice, microphone/camera/arm and Pi-local kiosk load remain separate gates. The latest boot still recorded undervoltage; preserve the evidence, do not suppress warnings or force current limits, and do not keep interrupting software progress with cabling questions. Classroom wired/mainland field acceptance remains separate. No CI or reopened model budget.

Software PR74–77 and Grok fixes are merged in [PR85](https://github.com/tantalum666/FYP/pull/85); this Pi recovery branch remains separate. Preserve existing school/merge notes and all private material.
