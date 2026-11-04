# Group 2 · OpenAI realtime and Alice wake listening

2 November 2026, Asia/Hong_Kong. Owner requested OpenAI integration and selected calling Alice to wake. This replaces the earlier Qwen-only manual-preview choice for the current software session; Qwen, Gemini and other candidates remain available for comparison.

## Current interaction

The primary Web chat retains Alice, shared tasks, memories, permissions and action cards. Enable **Say Alice to wake** once and allow the microphone. While waiting, PCM goes only to the connected desk's local keyword detector. On this Mac preview both browser and detector are on the same machine. Calling Alice or its Mandarin pronunciation wakes the normal voice client; only then does it request an OpenAI session.

The call accepts successive spoken turns without another button. After30 seconds without conversation activity, OpenAI closes and local listening resumes. Existing600-second overall session bound remains. Errors stop automatic listening instead of looping paid retries. Turning off the switch, changing identity, leaving the relevant view or closing the page releases the appropriate capture/socket resources. Returning from a temporarily suspended view can resume an enabled local listener; page reload starts with listening off. This is not an OS-login/background daemon or a claim of native-phone background operation.

Typing a submitted message pauses wake mode and uses the existing realtime text path. Long-idle client context is cleared before reuse so a new wake does not depend on an expired30-minute server context. Provider changes end the old connection and clear its resume handle without rewriting visible messages or unsent input.

## Responsibilities

- `voice_protocols.py` holds the shared response/cancel/grouped-tool lifecycle and existing Qwen/Gemini formats. `openai_voice.py` adds the OpenAI GA format, event aliases and streaming16-to24k resampling. Existing browser/local-worker16k input and24k playback contracts remain intact.
- `VoiceService` retains authenticated tickets, session/task context, tool dispatch, independent authority, response grounding, cancellation and usage records. OpenAI uses the same business services; no second task/approval/queue system exists. Application-owned cancellation avoids double-cancelling through automatic server VAD.
- `WakeListening` owns only a short-lived owner/session/origin-checked local PCM channel and one detector slot. It cannot call a provider or execute business tools. Its tokens expire, are single-use, and audio rate/size are bounded.
- `WakeAudio` owns browser capture/local transport; `useAliceWake` coordinates local waiting and the existing cloud conversation. Local microphone state is not labelled microphone-off while the listener is armed.
- The pinned existing sherpa-onnx bilingual model uses fixed Alice phone sequences and a short silence prefill. Model files remain ignored runtime assets; raw audio is neither logged nor saved by this channel. Keyword-only activation can still misfire on similar words or background speech containing the name; human/noise/AEC validation remains open.

## Current runtime

Vite5191 proxies API8861 with synthetic `work-ui-01` data. API uses this worktree's frozen `.venv` with the existing audio extra. Explicit settings are `DESK_VOICE_PROVIDER=openai_realtime`, `DESK_VOICE_MODEL=gpt-realtime-2.1`, voice `marin`, `DESK_WAKE_ENABLED=1`, and an absolute DESK_WAKE_MODEL_DIR pointing to the verified ignored model cache. DESK_OPENAI_CREDENTIAL_FILE points to the previously confirmed private FYP env file. Explicit project-file selection takes precedence over a generic OPENAI_API_KEY; secrets stay backend-only and are not copied to this branch.

Standalone text/background providers, scheduler and computer execution remain off in this particular UI preview. Explicit realtime typed/voice requests still work through OpenAI. This is not a Pi deployment or unattended cross-application runtime. Keep the current service configuration when reopening the preview; do not silently revert to a providers-off environment.

## Evidence and model choice

The live smoke test uses synthetic Mandarin and an isolated real VoiceService/calendar fixture. Mini first exposed timezone-free tool arguments, then an output cap that truncated speech, then completed with an incorrect9:30->10:30 spoken time. Shared date descriptions, explicit owner-clock use, output allowance and factual instructions were improved. Full Realtime2.1 then returned3 meetings at9:30/14:00/16:00 correctly. The prompt also changed before the full-model check, so this is not a controlled ranking or an accuracy percentage. The current default preview uses the passing full configuration; Mini remains a lower-cost candidate requiring more evidence.

Local model inference, actual local WebSocket detection and browser waiting/stop checks are separate from the paid model result. No live human wake-to-speaker/AEC or long-running background success rate is claimed. [QA and failures](../../output/qa/2026-11-02-openai-alice-wake/verification.md).

## Costs and test authorization

Current [OpenAI pricing](https://developers.openai.com/api/docs/pricing) gives audio input/output per1M tokens of USD10/20 for Mini and32/64 for full2.1. The [cost guide](https://developers.openai.com/api/docs/guides/voice-latency-cost) describes10 input and20 output audio tokens/second, VAD filtering of empty audio, and no Realtime connection fee. New audio alone therefore costs approximately USD0.006/0.024 per input/output minute on Mini, or0.0192/0.0768 on full. History, text, tools and separate transcription add costs; caching is not guaranteed. These are not total-bill quotes.

For30 conversational minutes/day split evenly between human and assistant, new-audio estimates are Mini USD0.45/day or13.50/30days; full USD1.44/day or43.20/30days. GPT-Live1 is a different service, USD0.05 per active session minute including silence, plus backend work:8 connected hours/day would be USD24/day before backend costs. Local wake/idle closure also benefits Live; it is not inherently unsuitable for short, explicitly managed sessions.

This requested test round was limited to USD1 and is closed. Returned usage gives an uncached/ASR upper estimate0.1692086; conservative accounting is0.6499936 including an incomplete first-call receipt reservation. This is not a verified provider bill. [Budget receipt](../../output/qa/2026-11-02-openai-alice-wake/budget-summary.json). No more agent-paid checks follow from the closed round; ordinary owner-initiated use is separate. The earlier reported approximatelyUSD170 credit was not re-audited as a current balance.

The USD1 ceiling applies to this experiment controller, not to normal owner usage or an account-wide daily/monthly hard limit. No provider billing setting was changed.

## 4 November integration

This implementation is part of the unified PR74–77/main candidate. The described normal preview is the preserved Nov2 environment, not a newly deployed merged runtime. Local integration tests use a separate providers-off fixture. No new paid or human-media test is implied. [Merge QA](../../output/qa/2026-11-04-merge-74-77/verification.md).
