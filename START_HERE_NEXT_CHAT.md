# Group 2 · Current entry

4 November: Pi recovery is active, with official27W power and dorm wall Ethernet. The owner requires homeWi-Fi, classroomWi-Fi+wired, dormwired, and explicitly rejects a hotspot workaround and further blind trials.

Read [handoff](handoff.md), [current QA](output/qa/2026-11-04-pi-dorm-ethernet/verification.md), [network contract](desk-companion/docs/pi-network-profiles.md) and [relay/recovery contract](desk-companion/docs/pi-owner-relay.md). Card readback proved the first new wired lease/source policy. Later readback showed an incomplete relay installation; verified bootcmd/runcmd recovery and an optional pinned VPS transport are now prepared.62 local checks pass; real Pi SSH does not yet.

Next is the consolidated verified-card boot, stage observation and original Pi host-key authentication. Do not ask for a hotspot, reflash, remove pairing identities, or equate a receipt/port/banner with full acceptance. Current VPS changes are only the dedicated restricted relay account/key and conditional stage logging.

Unified software PR74–77 plus Grok fixes are merged in [PR85](https://github.com/tantalum666/FYP/pull/85). This recovery branch is separate; Pi and the preserved preview were not upgraded to latest main. All experimental model budgets are closed; no CI. Preserve original data and unrelated local school/merge notes.
