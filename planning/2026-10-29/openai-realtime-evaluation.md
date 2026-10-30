# Group 2 · OpenAI real-time voice evaluation

29 October 2026. The owner reports USD170 in API credit and explicitly asks to test both voice routes with restrained spending. They clarified both tests mean real-time voice. This round uses a **USD5 operating ceiling**, stated before setup, rather than treating the whole balance as available experiment spend. Qwen's previous budgets remain closed and Pi remains paused.

## Scope

Compare `gpt-realtime-2.1` with `gpt-live-1` + `gpt-6-luna` Responses backend. Add `gpt-realtime-2.1-mini` as the lower-cost check. These are official API model names available in the selected project's model listing. The informal “GPT voice” request is mapped to the speech-to-speech Realtime family; no separate `gpt-voice` ID is listed. API listing, successful session creation and completed task trials are recorded separately.

Use synthetic English, Mandarin and Cantonese speech generated locally, paced at24kHz/mono/PCM16, and the same fictional29October business clock with three30October meetings. No microphone, camera, screen, external calendar or personal fact is read. Existing FYP tool schemas and execute_tool/Runtime/Store are reused in disposable isolated directories. No production provider is switched and no second agent is inserted into the application.

## Execution and budget

- One persistent ledger under the ignored experiment runtime; reserve before each paid connection, no retries/reconnects. Unknown usage retains its reservation after restart.
- Current per-run reservations: Realtime1.50USD, Mini0.50USD, Live0.25USD. Session capped45seconds plus bounded connection/close time; up to6 backend/model responses,512 Realtime output tokens or768 Live backend output tokens per response. Hosted tools are absent. Failed/incomplete trials remain in the record.
- Provider token and duration usage is converted at29October published standard prices. Cached tokens are conservatively priced as uncached; Luna cache writes use the larger12hour write rate because the receipt does not specify TTL. Duration updates are cumulative, not summed. Final session.closed is required for confirmed Live duration; each backend response has its own usage.
- Estimates are not an account invoice. The owner-reported USD170 balance has not been independently reconciled with Platform billing. Keep the unused balance for later work and close every test session.

## Planned checks and evidence boundaries

1. Three meetings: voice request → actual calendar_query → correct count/start times in speech, using the same input audio for each route.
2. Explicit language following for English, Mandarin and Cantonese. Preserve initial automatic-language failures instead of replacing them with only passing examples.
3. Remember request produces a reviewable pending draft and zero active facts before owner approval. The model must not claim it already saved the fact.
4. Interruption while speaking: inject a short “Stop, just say ready”; inspect the new reply and cancelled/continued work separately. This is paced synthetic barge-in, not a human echo-cancellation test.
5. Network audio receipt and actual playback are distinct. Report first non-silent received audio, including acknowledgment speech; do not call it first useful word or a human5second SLO. Small samples do not establish p95.

Initial calibration found automatic language switching from English to Chinese and a harness closing Live between its acknowledgment and full backend answer. The completion condition now waits for audio after backend completion and a quiet transcript/audio interval. Explicit selected-language instructions are applied to both Live and backend. Calibration failures remain recorded and are not part of the final controlled comparison.

## Primary sources

- [Realtime overview](https://developers.openai.com/api/docs/guides/realtime)
- [GPT-Live overview](https://developers.openai.com/api/docs/guides/live)
- [Prices](https://developers.openai.com/api/docs/pricing): Realtime audio32/64USD per million input/output tokens; Mini10/20; Live0.05USD per minute plus backend; Luna0.10/0.50USD per million ordinary input/output tokens.
- [WebSocket transport](https://developers.openai.com/api/docs/guides/voice-websockets?api=live)
- [Delegation and tool continuation](https://developers.openai.com/api/docs/guides/live-delegation)
- [Live finalization and usage](https://developers.openai.com/api/docs/guides/live-conversations)

Final trials, raw usage, synthetic output samples and conclusions belong in [QA](../../output/qa/2026-10-29-openai-realtime/verification.md). This plan is not a claim that every check has passed.

## Completed round

16 real sessions finished, including5 calibration/iteration attempts retained and11 final controlled checks.504 backend/15 focused tests, lint and formatting pass. Total returned-usage estimate isUSD0.3035168833; all session usage is finalized and the ledger is closed. Corrected Live memory acknowledgments were retested. Details, samples and limits are in[QA](../../output/qa/2026-10-29-openai-realtime/verification.md). No future paid run or production-provider switch is automatically authorized by this completed experiment.
