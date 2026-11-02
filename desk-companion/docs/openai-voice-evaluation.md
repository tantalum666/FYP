# OpenAI real-time voice evaluation · Group 2

2 November2026 update: the [production Realtime adapter and Alice wake path](openai-alice-wake.md) now have separate current evidence. The29October evaluation, prices/reservations and results below retain their original scope; they are not new runs.

29 October 2026. The owner requested cost-conscious tests of both real-time voice routes. This is an **isolated evaluation harness**, not a completed production-provider adapter. Existing Qwen integration and normal application provider selection remain separate.

## Tested routes

| Route | Model / architecture | Current evidence |
|---|---|---|
| Realtime | `gpt-realtime-2.1`, speech-to-speech with direct function calls | English, Mandarin and Cantonese calendar requests; pending-memory draft; synthetic interruption |
| GPT-Live | `gpt-live-1` conversation + `gpt-6-luna` Responses delegation | Same five scenarios; Live and backend usage tracked independently |
| Lower-cost reference | `gpt-realtime-2.1-mini` | One controlled English calendar scenario, plus initial calibration; other languages not yet measured here |

The informal “GPT voice” request maps to the Realtime speech-to-speech API. There is no separate `gpt-voice` ID in the project's returned model list. [Official Realtime](https://developers.openai.com/api/docs/guides/realtime) and [GPT-Live](https://developers.openai.com/api/docs/guides/live) describe these two architectures.

## Reproducible local design

`scripts/openai_voice_eval.py` is an explicitly invoked runner. `voice_eval/budget.py` owns durable reservations and usage estimation; `fixtures.py` owns synthetic input and disposable FYP services; `session.py` owns the two wire protocols and bounded lifecycle. It reuses the existing `TOOLS` and `execute_tool()` validation/deduplication rather than adding business operations or another job queue.

Only fixture calendar reads and memory-draft tools are advertised. No confirmation, arbitrary file/shell, hosted search/container or physical output tool is exposed. Each run has a fresh local Runtime/Store, a fixed fictional business date and three meetings. Memory requests produce a pending proposal with zero active facts. The normal owner database is never opened by the runner.

Synthetic inputs are generated with installed macOS voices and streamed at their recorded speed, mono PCM16/24kHz, in50ms chunks. No microphone is opened. Both output routes use Marin. The output WAV and transcript are real provider results. First non-silent network audio uses RMS100 and includes acknowledgment speech; it is not a DAC/playback measurement, first useful word or human-conversation SLO.

Realtime uses GA events, server VAD and bounded output tokens. Live uses `session.start`, nested `response.event` function items, explicit function-result/`response.create` continuation, and `session.close` → `session.closed`. The backend completion event is not spoken-answer completion. Live waits for audio after backend completion and a quiet interval of both transcript and audio; the initial premature-close trial remains in QA.

## Spending and secrets

- The user reported USD170 in credit. This round used a smaller **USD5 operating ceiling**; the account balance itself was not independently reconciled.
- A dedicated key was securely created in the user-selected Platform project and saved to the explicitly approved `desk-companion/.env.local`, mode0600, ignored by Git. No key is in frontend code, reports or tool logs.
- Each paid run requires `--allow-paid` and a unique ID. Persistent reservations are atomic. Unknown/incomplete usage retains its reservation, even after restart. Output/response/session limits and no automatic reconnect bound an attempt. These are local experiment controls, not an OpenAI organization-wide billing limit.
- Prices are taken from [the official pricing page](https://developers.openai.com/api/docs/pricing). Realtime/Mini estimates conservatively count cached input at ordinary rates. Live duration snapshots are cumulative; final duration requires `session.closed`. Delegated Luna tokens include conservative12-hour cache-write pricing when TTL is absent. This is an estimate, not an invoice.
- **This round is closed.** All16 sessions have returned usage; the ledger estimate including calibration and iterations is **USD0.3035168833**. Further reservations in this round are rejected with `EXPERIMENT_CLOSED`. The key remains available locally for a later explicitly scoped round; no paid service is left running.

## Results and decisions

The final controlled set has11 trials:5 Realtime,5 Live and1 Mini. The two primary routes read the three expected meeting times correctly, produced pending-only memory drafts and changed to “ready” after synthetic interruption. Five earlier calibration/iteration records remain: one initial Mini reference, two English→Chinese language-following failures, one premature Live close and one ambiguous Live memory acknowledgment.

Explicit selected-language instructions are needed in both the Live conversation and its backend. Live's initial “我记下来” acknowledgment could imply persistence before approval; a focused prompt refinement and real retest now describe preparing a draft and still needing screen approval. This is a concrete tested case, not a proof against all misleading wording.

Mini is the lowest-cost English reference in this small set. Live's separate backend fits the existing permission/business-service boundary, but full-duplex context, playback and interrupted backend work require additional application integration. Realtime has the more direct function-call integration. No final provider choice or broad naturalness ranking is made from these samples.

Full [QA, per-run receipts and audio](../../output/qa/2026-10-29-openai-realtime/verification.md) and [test plan](../../planning/2026-10-29/openai-realtime-evaluation.md) retain failures and limits. Local checks:504 backend tests,15 focused evaluation tests, Ruff and formatting. Frontend and native source were not changed in this evaluation. Native input, real human Cantonese/English naturalness, microphone/AEC/noise, weak networks and long sessions remain separate gates. No CI, Qwen charge or Pi/Luwu work.

## Updated next acceptance target —30October

The owner requested a harder real application task. The next main gate is the [complex demo-preparation workflow](../../planning/2026-10-30/complex-application-acceptance.md), whose source fixtures and offline reference are ready. The bounded adapters, durable stages and scripted real-app/restart path now have [actual evidence](../../output/qa/2026-10-30-application-execution/verification.md). A resumable model-driven task loop and production provider wiring remain necessary before a meaningful voice-to-app comparison. The earlier voice/API results remain valid within their scope; no new model calls or reopening of this closed spending round occurred while preparing the challenge.
