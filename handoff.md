# Group 2 Current Handoff

Updated: 17 October 2026. **Qwen3.8 Omni Flash Realtime is implemented and bounded live trials passed for synthetic speech/calendar and one generated image. Changes extend draft [PR #15](https://github.com/tantalum666/FYP/pull/15), not main. Default providers remain `none`; the private key stays outside Git.**

## Current state and evidence

- [Omni contract](desk-companion/docs/qwen-omni.md) / [local setup](desk-companion/docs/qwen-local-setup.md): independent nested-audio/VAD/image protocol; explicit private-file loading; function correlation, cancellation fences, grouped tool returns and usage. Reuses ToolDispatcher and JobService. Models cannot approve calendar writes, memory edits or computer jobs.
- Owner-only browser controls share a selected image or selected screen after starting voice. No camera opens. Frames are bounded JPEGs, at most1fps. Stop/end/disconnect release capture; already transmitted images remain in the provider conversation. Paired clients cannot use this sharing interface.
- [Integration QA](output/qa/2026-10-16-qwen-omni-integration/verification.md):215 backend /21 frontend checks, Ruff, type/build, desktop/mobile browser checks using synthetic media and a fake provider. No real microphone or screen capture. Existing notes/folder approval/read-back semantics remain intact.
- Live selected-key authentication succeeded. Two successful fictional next-week queries returned all three meetings. Synthetic last speech to grounded audio **receipt** was3.176s and2.619s on Mac, excluding browser playback and Pi. A generated blue JPEG was answered correctly. An earlier interrupted calendar attempt failed and remains recorded; cancellation/function lifecycle fixes have regression coverage. This is not a language-quality or5-second p95 acceptance result.
- Owner approved **CNY5 maximum for this synthetic trial only**. Five connections reserved CNY4.1 in the conservative trial ledger; known successful-response usage estimates total CNY0.106608, with missing failed/cancelled usage and no invoice confirmation. Trials are stopped. This is not a recurring budget or a production per-session spending switch.
- PRs #6–#14 are merged on main `a663d83`. Existing JobService handles bounded notes and one named folder. General GUI/remote-PC execution is unimplemented. [Prior merge QA](output/qa/2026-10-15-grok-review-merge/verification.md).
- A1 intact2D stays on [PR #4](https://github.com/tantalum666/FYP/pull/4); kernel [PR #5](https://github.com/tantalum666/FYP/pull/5) stays separate/unmerged. Original checkout/private runtime and school files are preserved.

## Remaining

The client target is Raspberry Pi/Linux; both Pi-local and another-computer operations are desired. Linux-first remains engineering advice, not a frozen owner scope. The Omni trials do not deliver general computer use. A target application/data scope, bounded GUI executor and independent execution read-back are still needed.

Real Mandarin/English/Cantonese conversation, microphone/speaker AEC, wake word, browser playback timing, cold-start capture, per-turn10-second timeout and target Pi/Wayland/ARM64/iPhone are unverified. Tina is an engineering default, not the final chosen character voice. Full business backup/archive, posture labels, optics/RIG/cleaner and physical stop remain separate gates. Comparison reports retain their dated research scope: [voice](research/2026-10-15-voice-ai/voice-model-comparison.md), [computer use](research/2026-10-15-voice-ai/computer-use-comparison.md), [latency acceptance](planning/2026-10-15/voice-response-latency.md).

## One next step

**On the actual Pi/Linux target, run the existing synthetic calendar fixture through browser playback and wire the per-turn timing/10-second timeout, then collect consented multilingual microphone/AEC samples within a separately defined operating budget.** Do not reopen a paid session merely because PR #15 exists; do not substitute this for the separate bounded GUI task.
