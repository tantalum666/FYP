# Group 2 · Current entry

4 November 2026: **the owner resumed Pi work in the dorm**, superseding the previous hardware pause. Ethernet is in the wall socket; official27W power is confirmed. No monitor or current Pi address. The original card was identity-verified, inspected read-only, given a backed-up two-file recovery seed and safely ejected. Owner has reinserted it and powered on; live connection is being checked.

Read [current handoff](handoff.md), [recovery QA](output/qa/2026-11-04-pi-dorm-ethernet/verification.md) and [network contract](desk-companion/docs/pi-network-profiles.md). Next is the new boot’s network discovery and pinned-key SSH, then journal-recovery and power readback. Keep the old saved lease separate from current proof. Do not reflash or delete the paired host identity.

This checkout preserves the Pi branch and earlier local document changes. Unified software PR74–77 plus Grok fixes are merged; [merge route](https://github.com/tantalum666/FYP/pull/85). Current source is `/Users/tantalum/.codex/worktrees/grok-journey-compat-20261104/FYP`. The preserved old preview and Pi installation were not upgraded by merging.

Pi has a dedicated `?surface=device` display; automatic kiosk and fresh power/load acceptance remain unfinished. All experiment budgets are closed; local checks only, no CI. Preserve original system/data and private credentials.
