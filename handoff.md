# Group 2 Current Handoff

Updated: 15 October 2026. **Voice comparison now includes the owner's requirement for useful next-week calendar answers around5 seconds and within10 seconds. The latency contract and offline tool measurement are complete; live end-to-end latency and provider selection remain unverified.**

## Current state and evidence

- [Voice comparison](research/2026-10-15-voice-ai/voice-model-comparison.md) and [sources](research/2026-10-15-voice-ai/source-register.md): confirmed Grok Voice3.0/API on 14 October; Gemini4 Argon has audio input but no audio generation/Live; Gemini3.8 remains the Live family. Added Nova2.5, Eleven v4, Hume's 13 November API sunset, current component/open-model coverage, AA snapshots with confidence limits and current base-cost calculations.
- Engineering shortlist: Grok3.0 for quality/tool tasks, Gemini3.8 Live for daily conversation/value, Qwen Audio3.1 Plus for Mandarin/Cantonese. This supersedes earlier engineering candidate orders, not the owner's unmade provider/model/spend decision. Actual account eligibility and language quality are unverified.
- [Research QA](output/qa/2026-10-15-voice-model-refresh/verification.md) records inherited full-read evidence, exact-text supplements, source limits, arithmetic and document checks. Only documentation/QA changed; software providers remain disabled.
- Code from PRs #6-#14 is merged on main a663d83; the [independent review](output/qa/2026-10-15-grok-review-merge/verification.md) records 182 backend /17 frontend checks on code2c1e465, browser recovery and folder read-back. Those are dated code results, not voice tests.
- The A1 identity and intact2D direction remain on [PR #4](https://github.com/tantalum666/FYP/pull/4); separate kernel [PR #5](https://github.com/tantalum666/FYP/pull/5) remains unmerged. The original checkout/private runtime and school files are preserved.

- Research delivery is [draft PR15](https://github.com/tantalum666/FYP/pull/15) on codex/voice-model-comparison-20261015. It is not merged into main; no new provider is enabled.

- [Latency contract](planning/2026-10-15/voice-response-latency.md): measure actual playback of grounded information, not a generic preamble. The engineering target is p50<=3s / p95<=5s with10s timeout handling. A synthetic500-event Mac fixture measured local tool dispatch/query/serialization p95 at6.002ms; no model/network/audio/Pi measurement or application change. [Latency QA](output/qa/2026-10-15-voice-latency/verification.md).

## Remaining

Real provider/model and spend choice; Mandarin/English/Cantonese listening and tool acceptance; wake/AEC and Pi/iPhone evidence. Named real-application/remote-PC execution, full archive/business backup, consented posture labels and optics/RIG/cleaner validation also remain open. Public voice research did not authorize accounts, model spend or microphone capture.

## One next step

**Prepare the shared real-provider trial: choose available exact model/voice/reasoning configurations and a total spend cap, wire per-turn timestamps/timeout handling, then measure cold and ready-session grounded calendar replies against the5-second target with correct dates and independent results.**
