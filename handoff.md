# Group 2 Current Handoff

Updated: 15 October 2026. **The comparison now covers natural speech, useful calendar answers around5 seconds, and screenshot-driven cross-application computer use. Public research is complete; provider selection and live voice/GUI acceptance remain unverified.**

## Current state and evidence

- [Voice comparison](research/2026-10-15-voice-ai/voice-model-comparison.md) and [sources](research/2026-10-15-voice-ai/source-register.md): Grok Voice3.0, Gemini3.8 Live and Qwen Audio3.1 Plus are engineering speech candidates. Gemini4 Argon has audio input but no audio generation/Live. [Research QA](output/qa/2026-10-15-voice-model-refresh/verification.md).
- [Computer-use comparison](research/2026-10-15-voice-ai/computer-use-comparison.md): proposed everyday GUI baseline Sonnet5.5 versus GPT-6.1 Sol; harder-task comparisons Opus5.5/Astra; Gemini3.8 Flash/4 Argon also support desktop tools. Models, executors and Grok Bot's finished product are separate. Vendor OSWorld partial scores across versions/subsets are not one completion-rate ranking. [QA](output/qa/2026-10-15-computer-use-comparison/verification.md).
- [Latency contract](planning/2026-10-15/voice-response-latency.md): last speech to playback of grounded information, not a preamble. Engineering p50<=3s / p95<=5s with10s timeout handling. Synthetic500-event Mac tool dispatch/query/serialization p95=6.002ms; no model/network/audio/Pi result. [Latency QA](output/qa/2026-10-15-voice-latency/verification.md).
- PRs #6-#14 are merged on main a663d83; [review QA](output/qa/2026-10-15-grok-review-merge/verification.md) records182 backend /17 frontend checks on code2c1e465, browser recovery and folder read-back. These are dated code results, not voice/GUI tests. Existing JobService handles bounded notes and one named folder; general GUI/remote-PC control is unimplemented.
- A1 intact2D remains on [PR #4](https://github.com/tantalum666/FYP/pull/4); separate kernel [PR #5](https://github.com/tantalum666/FYP/pull/5) remains unmerged. The original checkout/private runtime and school files are preserved.
- Research extends [draft PR15](https://github.com/tantalum666/FYP/pull/15), branch codex/voice-model-comparison-20261015. It is not merged into main; no new provider is enabled.

## Remaining

Exact provider/model/voice/reasoning and spend choice; account eligibility; target computer/apps/data scope; bounded GUI executor and recovery. Live Mandarin/English/Cantonese, per-turn timing/timeout wiring, wake/AEC and Pi/iPhone remain unverified. Full archive/business backup, consented posture labels and optics/RIG/cleaner evidence also remain open. Informational comparisons do not authorize spend, installs, computer permissions or capture.

## One next step

**Specify one bounded cross-application task, target OS/apps and allowed data, then prepare the existing JobService/executor trial comparing Sonnet5.5 with GPT-6.1 Sol after exact available configurations and a spend cap are chosen; keep simple calendar queries on the direct-tool path and measure grounded spoken replies against the5-second target separately.**
