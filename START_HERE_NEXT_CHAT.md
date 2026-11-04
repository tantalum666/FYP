# Group 2 · Current entry

5 November2026: Pi recovery remains active. The durable boot reported successful setup but direct VPS22 connectivity failed. The owner requires mainland homeWi-Fi, classroomWi-Fi+wired, dormwired, and rejects hotspot workarounds/repeated blind trials.

Read [handoff](handoff.md), [current443 QA](output/qa/2026-11-05-pi-443-transport/verification.md) and [contract](desk-companion/docs/pi-owner-relay.md). An isolated client forced to Mac en0 authenticated the pinned VPS through443 without changing existing proxies. The matching official ARM64 artifact and full offline package are verified;79 focused tests pass. The real card does not yet contain this443 package.

Next: after owner returns the original card, verify identity, write/read back the prepared package, safely eject, then verify actual boot stages and original Pi SSH. Do not restart the prior investigation or claim the Mac test is Pi acceptance. No hotspot, CI, paid-model request, key regeneration, system reflash or latest-main app migration.

Software PR74–77 and Grok fixes are merged in [PR85](https://github.com/tantalum666/FYP/pull/85); this Pi recovery branch remains separate. Preserve existing school/merge notes and all private material.
