# Group 2 · Current entry

31 October 2026. **Pi work has resumed by explicit owner instruction.** The original card now has home Wi-Fi and portable wired/classroom networking prepared; it was verified and safely ejected. Actual home boot/SSH/app acceptance is still pending. Begin with [handoff](handoff.md), [network contract](desk-companion/docs/pi-network-profiles.md) and [current QA](output/qa/2026-10-31-pi-home-resume/verification.md).

The owner wants home Wi-Fi, classroom Wi-Fi plus Ethernet, dorm Ethernet. Keep credentials/private backups outside Git. Existing pairing/host keys and app data were preserved. A generic LAN launcher was copied to the local Pi download folder. Do not infer success from written configuration or revive the failed dorm Wi-Fi retry loop.

Merged software baseline remains `dac527b` after PR5 and its receipt PR72. Its1,686backend/300frontend checks are prior software results, not this Pi's acceptance. The Pi app was not upgraded in this networking step; [explicit migration rules](desk-companion/docs/pr5-integration.md) still apply. No CI, new model budget or automatic VPS/proxy change. Follow focused [AGENTS](AGENTS.md) recovery and the current one-step handoff.
