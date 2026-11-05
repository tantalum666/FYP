# Group 2 · Current work

6 November2026. Owner requests no Sign in on every app surface, and Alice/voice on Pi. Work in codex/passwordless-alice-device-20261105, based on mainabf6387. This supersedes manual-login UI and the calendar-first Pi default.

Read [handoff](handoff.md), [current QA](output/qa/2026-11-06-passwordless-device/verification.md) and latest user instructions. Pi runs mainabf6387 through the restored443 relay; network/backup evidence is in [PR87](https://github.com/tantalum666/FYP/pull/87). Do not redo SD recovery or overwrite its private snapshots.

Implemented in source: shared automatic local-owner connection, removed password forms/Sign out controls, Alice DeviceHome using the existing conversation/voice client, and a read-only-model wake fix. Local backend1782/frontend324, Web/device/phone browser checks and a fresh native first-screen build have passed; application-transport regression checks36passed. Target rollout and Pi cross-app acceptance are in progress. Only the spontaneous red-LED investigation is deferred at the owner’s request; Pi software continues. No CI or reopened model budget.
