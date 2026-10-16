# Group 2 Current Handoff

Updated: 16 October 2026. **Owner selected Qwen3.8 Omni Flash Realtime and provided the Qianwen platform gateway docs. The key is staged locally outside Git at0600 with providers disabled. Omni integration, live authentication and voice/GUI acceptance remain unfinished.**

**Latest owner clarification:** The client runs on Raspberry Pi/Linux. Both Pi-local apps and control of another computer are desired; the owner is considering a Linux-only first scope, not yet freezing it. A single speech/vision/tool model is an option, so a second planning LLM is optional rather than mandatory.

## Current state and evidence

- [Voice comparison](research/2026-10-15-voice-ai/voice-model-comparison.md) and [sources](research/2026-10-15-voice-ai/source-register.md): Grok Voice3.0, Gemini3.8 Live and Qwen Audio3.1 Plus are engineering speech candidates. Gemini4 Argon has audio input but no audio generation/Live. [Research QA](output/qa/2026-10-15-voice-model-refresh/verification.md).
- [Computer-use comparison](research/2026-10-15-voice-ai/computer-use-comparison.md): proposed everyday GUI baseline Sonnet5.5 versus GPT-6.1 Sol; harder-task comparisons Opus5.5/Astra; Gemini3.8 Flash/4 Argon also support desktop tools. Models, executors and Grok Bot's finished product are separate. Vendor OSWorld partial scores across versions/subsets are not one completion-rate ranking. [QA](output/qa/2026-10-15-computer-use-comparison/verification.md).
- [Latency contract](planning/2026-10-15/voice-response-latency.md): last speech to playback of grounded information, not a preamble. Engineering p50<=3s / p95<=5s with10s timeout handling. Synthetic500-event Mac tool dispatch/query/serialization p95=6.002ms; no model/network/audio/Pi result. [Latency QA](output/qa/2026-10-15-voice-latency/verification.md).
- PRs #6-#14 are merged on main a663d83; [review QA](output/qa/2026-10-15-grok-review-merge/verification.md) records182 backend /17 frontend checks on code2c1e465, browser recovery and folder read-back. These are dated code results, not voice/GUI tests. Existing JobService handles bounded notes and one named folder; general GUI/remote-PC control is unimplemented.
- A1 intact2D remains on [PR #4](https://github.com/tantalum666/FYP/pull/4); separate kernel [PR #5](https://github.com/tantalum666/FYP/pull/5) remains unmerged. The original checkout/private runtime and school files are preserved.
- Research and local credential staging extend [draft PR15](https://github.com/tantalum666/FYP/pull/15), branch codex/voice-model-comparison-20261015. It is not merged into main; no provider is enabled.
- [Pi/single-model supplement](research/2026-10-15-voice-ai/computer-use-comparison.md#树莓派linux网络与单模型补充): retain both local/remote goals; Linux-first remains advice. The15 October Singapore trial suggestion is superseded by the owner's domestic-platform Omni choice. Pi Wayland/ARM64 and general GUI remain untested. Other speech/planner alternatives remain dated research. [Earlier QA](output/qa/2026-10-15-pi-voice-computer/verification.md).

- [Qwen local setup](desk-companion/docs/qwen-local-setup.md): hidden native input saved `~/.config/desk-companion/qwen.env`, owner-only directory/file, no network call or automatic loading. Separate official Chat base and Omni Realtime gateway are recorded. Existing text host validation and Audio protocol are not Qianwen Omni integration.7 dedicated checks and Ruff passed. [QA](output/qa/2026-10-16-qwen-key-setup/verification.md).

## Remaining

Model choice is now Qwen3.8 Omni. Spend cap, voice, actual Key/model authorization, Omni adapter, target computer/apps/data scope and bounded GUI executor remain open. Live Mandarin/English/Cantonese, per-turn timing/timeout wiring, wake/AEC and Pi/iPhone are unverified. Full archive/business backup, posture labels and optics/RIG/cleaner evidence remain open. Key setup did not authorize spend or capture.

## One next step

**Implement the selected Qwen Omni protocol on the existing voice/JobService boundaries and validate with mocks; only after the owner sets a spend cap, load the staged key for a bounded live authentication/voice trial and measure grounded calendar replies against the5-second target.**
