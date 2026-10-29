# Group 2 · OpenAI real-time voice results

29 October 2026, Asia/Hong_Kong. The owner authorized cost-conscious OpenAI testing, clarified both requested routes are real-time voice, selected the Platform project, and explicitly approved the local key destination. The USD170 balance is owner-reported; this experiment used a smaller USD5 operating ceiling.

**Completed:16 short real API sessions,11 final controlled trials, USD0.3035168833 conservative usage estimate including calibration/iterations. All usage is reconciled from returned receipts; the round is now closed.** This is not a confirmed Platform invoice. [Budget ledger export](budget.json), [all trials](summary.json) / [CSV](summary.csv) and each run's JSON preserve the evidence.

## Controlled comparison

Both routes use the same cached synthetic input WAV,24kHz mono PCM, Marin output, fixed fictional29October clock and actual existing FYP tool service over a fresh isolated database. Tomorrow's meetings are Design review09:30, Project check-in14:00 and Software demo16:00. Each row is **one sample**, not a percentile or a long-run success rate.

| Model | Input | First non-silent network audio after input ends | Estimated USD | Result |
|---|---|---:|---:|---|
| Realtime2.1 | English | 2.0794s | 0.026704 | Three meetings and all start times correct |
| Live1 + Luna | English | 1.9226s | 0.018918 | Same actual tool result, correct spoken answer |
| Realtime2.1 | Mandarin | 1.2412s | 0.030460 | Three meetings and times correct |
| Live1 + Luna | Mandarin | 2.1310s | 0.018080 | Three meetings and times correct |
| Realtime2.1 | Cantonese | 1.1620s | 0.030464 | Correct facts; Cantonese answer transcript |
| Live1 + Luna | Cantonese | 1.4400s | 0.015591 | Correct facts; Cantonese answer transcript |
| Realtime2.1-mini | English reference | See [receipt](mini-en-02.json) | 0.007850 | Three meetings and times correct; other languages not tested for Mini |

**Timing includes acknowledgment speech**, such as “let me check”. It does not establish time to the first useful fact or actual speaker playback. Live can speak while backend work proceeds, so backend completion is not voice completion. Its duration charges also include idle/waiting time; the shorter Realtime network generation lifecycle is not an equivalent playback-duration measurement. These samples do not establish that one route is generally faster, cheaper or more natural.

## Business authority and interruption

| Scenario | Realtime2.1 | Live1 + Luna |
|---|---|---|
| “Please remember my fictional project codename” | `memory_save_draft` produced1 pending proposal,0 active facts; spoken answer clearly requests screen approval | Same business state. Initial ambiguous acknowledgment was refined and retested; latest answer says it is preparing a draft and still needs screen approval |
| Inject “Stop. Just say ready” while speaking | Initial response was cancelled with `reason=turn_detected`, followed by “ready” | Speech changed from the study-plan answer to “Ready”; no backend effect was running in this scenario |

Readbacks: [Realtime memory](realtime-memory-01.json), [Live memory retest](live-memory-02.json), [Realtime interruption](realtime-interrupt-01.json), [Live interruption](live-interrupt-01.json). Realtime cancellation here confirms model generation stopped; actual device audio-queue clearing and AEC still need application testing. The real task/memory services enforce the boundary; this is not a mocked claim that a draft was saved. No user fact, private calendar, file executor or physical device was involved.

## Retained failures and calibration

- [live-en-01](live-en-01.json): the first harness treated a pause after acknowledgment as completion and closed before the full answer. Excluded from quality comparison, but its duration/backend charge remains counted. A regression now requires audio after backend completion and quiet transcript/audio before closing.
- [realtime-en-01](realtime-en-01.json) and [live-en-02](live-en-02.json): English input returned Chinese answers despite correct calendar facts. Selected-language instructions were added to Realtime and both Live layers, then the final English/Mandarin/Cantonese checks were run.
- [live-memory-01](live-memory-01.json): “我记下来” could sound like a completed save before the final draft explanation. No fact was saved. A narrow voice-prompt refinement produced the clearer [retest](live-memory-02.json).
- [mini-en-01](mini-en-01.json): useful initial low-cost calibration, kept separate from the controlled selected-language English reference.

The initial harness also needed ordinary lint/test-fixture corrections before its first network run. Those local failures incurred no model usage. No API errors or retries were hidden; paid attempts always have unique run IDs.

## Listen to real output

These are AI-generated provider outputs from the fictional fixtures, not recordings of a person. They contain both acknowledgment and final answer; Live audio includes silence from its continuous stream.

- Mandarin: [Realtime2.1 audio](realtime-zh-01.wav), [GPT-Live audio](live-zh-01.wav).
- Cantonese: [Realtime2.1 audio](realtime-yue-01.wav), [GPT-Live audio](live-yue-01.wav).
- English: [Realtime2.1 audio](realtime-en-02.wav), [GPT-Live audio](live-en-03.wav), [Mini audio](mini-en-02.wav).

Human listening is still needed to judge accent, pronunciation, warmth and conversational naturalness. Matching transcripts and returned PCM do not prove good real microphone/AEC behavior.

## Verification and remaining scope

- [504 backend tests](backend-tests.txt), [15 focused tests](focused-tests.txt), [Ruff](lint.txt), [formatting](format.txt) pass. The backend suite retains one existing Starlette/httpx deprecation warning.
- Offline regressions cover atomic/concurrent budget reservations, duplicate IDs, unknown usage after restart, higher observed costs, closure, modality/cache-write pricing, real pending-only fixture writes, disallowed tools, nested Live function metadata, cumulative usage and the premature-close reproduction.
- [Input manifest](input-manifest.json) records the exact shared synthetic WAV hashes; inputs stay in the private local runtime. Output WAV files and fictional receipts are the published evaluation artifacts. The key, runtime databases and private-key material are excluded from Git.
- This is the separate [evaluation harness](../../../desk-companion/docs/openai-voice-evaluation.md); normal web/App provider integration was not changed. Existing frontend/native checks are not rerun or relabeled as OpenAI acceptance. All16 paid connections ended; the actual ledger rejects a new reservation after closing.
- No CI, human microphone/camera capture, hosted search/container, other-provider budget, external account workflow, school submission or Pi/Luwu run occurred.

Next: connect a bounded OpenAI candidate to the existing application voice/session boundary and perform a short user-controlled A/B listening session, then test real interruption/playback/context recovery. Keep the current APIs and business permissions shared; do not introduce another persistent transcript or job queue. Any later paid round needs its own explicit scope and limit.

## Sources and provenance

[Realtime documentation](https://developers.openai.com/api/docs/guides/realtime), [Live documentation](https://developers.openai.com/api/docs/guides/live), [official prices](https://developers.openai.com/api/docs/pricing), [Live delegation](https://developers.openai.com/api/docs/guides/live-delegation), [Live lifecycle](https://developers.openai.com/api/docs/guides/live-conversations). Pricing was read29October; cached input is conservatively priced as uncached, and Luna cache writes use the higher published TTL rate when unspecified.

[Reading record](reading-record.json) and [plan](../../../planning/2026-10-29/openai-realtime-evaluation.md) distinguish current sources from historical Qwen results. Work is on `codex/openai-realtime-evaluation-20261029`, based on PR65 head `61db1c2c2fc592887bdf78170ef7fc9e28cba33c`. Published as draft[PR66](https://github.com/tantalum666/FYP/pull/66), source`f5b9417cfda62e6f8400c7b5ac85ec3a49be3b2a` verified against GitHub and git remote. [Publication receipt](publication.json); PR64/65/66 remain open/unmerged. Neither source push nor this evaluation is deployment.
