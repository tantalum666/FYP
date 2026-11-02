# Group 2 · OpenAI and Alice wake verification

2 November 2026, Asia/Hong_Kong. Branch `codex/openai-alice-wake-20261102`, based on PR76 head17df074. Owner requested OpenAI testing and selected calling Alice to wake. A fresh USD1 short-test ceiling was announced; previous closed budgets were not reopened. Existing confirmed FYP credentials were reused without a new key or secret write.

## Implemented scope

Extracted the existing normalized realtime lifecycle into voice_protocols.py and added OpenAI GA session/event/image handling plus streaming16-to24k input conversion. VoiceService retains its existing ticket, context, tool, permission, cancellation and grounding authority. Exact OpenAI endpoint/model validation and a protected project-file loader keep keys backend-only. An explicit project file wins over an unrelated generic key.

WakeListening reuses the pinned local sherpa-onnx model with Alice/Chinese-name phone sequences. Its owner/session/origin checked, single-use-ticket channel accepts bounded local PCM and returns only a wake event; it has no provider or business-tool dispatch. WakeAudio/useAliceWake move between local waiting and the existing voice client. Quiet OpenAI calls close after30 seconds; the normal600-second cap remains. Error stops, manual off, suspension and late events cannot silently start repeated paid calls. Context expiry/provider changes clear stale resume handles while visible chat/drafts stay separate.

No new task/queue core, third-party account, native build, Pi operation, CI workflow, raw device recording or model-weight publication.

## Live OpenAI evidence, including failures

A free model-access GET returned200. The four explicit paid attempts used production VoiceService with an isolated synthetic calendar and Mandarin TTS, never real owner data or microphone capture. Actual speaker playback was not measured.

| Attempt | Configuration | Observed result |
|---|---|---|
|1|Mini2.1,512 output tokens|Input transcript correct; missing timezone tool arguments caused retries. Cap cut the next response; no usable audio delivered and one final usage receipt is incomplete.|
|2|Mini, explicit owner_clock/aware range|Tool reads correct;512-token output allowance truncated speech. Preserved failure.|
|3|Mini,1024 allowance/brief factual guidance|Completed audio but said10:30 instead of the actual09:30. Semantic failure despite transport completion.|
|4|Full2.1, exact start_local guidance|Clock -> calendar -> completed16.65 seconds of audio;3 meetings correctly stated at09:30/14:00/16:00.|

The prompt also changed before4. This is not a controlled model ranking or a reliability percentage. Current preview explicitly uses full2.1, the passing configuration. Mini remains a cheaper candidate requiring more evidence. Later cancellation configuration delegates interruption to the application instead of racing automatic VAD cancellation; its regression is offline, not a new live barge-in result. [Sanitized results](live-results.json).

The new test ledger is **closed**. Returned usage gives an uncached/ASR upper estimateUSD0.1692086; conservative accounting isUSD0.6499936, including the first incomplete receipt'sUSD0.50 reservation. Actual provider bill not reconciled. No additional paid calls were made for browser QA. [Budget](budget-summary.json).

## Local wake and browser evidence

- Verified the five pinned model files against the existing manifest and copied only into ignored runtime. No weights were committed. Existing optional audio dependencies were installed in this checkout's own frozen environment.
- Initial isolated word at stream time0 missed; retained calibration evidence. A0.4-second feature prefill fixes cold context without lowering the production0.35 threshold. Final English Alice and Mandarin name samples triggered; Alex, calendar and legacy Hey desk samples did not. These are five synthetic cases, not a human accuracy/false-wake rate. [Final inference](wake-final-inference.json), [initial](wake-inference.json), [calibration](wake-calibration.json).
- Actual local HTTP owner ticket -> WebSocket -> pinned detector returned Alice in1.288 seconds for synthetic PCM. Cloud active stayed false and the wake slot released. [Readback](local-wake-websocket.json).
- Actual Chrome checkbox reached Waiting for Alice with microphone capture and a cloud-disconnected caption. During this brief local-only QA, voice-ticket requests were blocked in that test tab to prevent an accidental extra paid call. The block was removed and the switch turned off afterwards. No viewport or user permission policy was changed. Existing Full mode was preserved. [Waiting screenshot](local-waiting.png).
- Current normal API reports openai_realtime/gpt-realtime-2.1, configured true, local wake available, both cloud and wake inactive after QA. [Runtime](runtime-check.json). This confirms ready configuration/local lifecycle, not a live human end-to-end result.

Actual human pronunciation, immediate speech after the keyword, noise/TV/AEC, sustained background/browser behavior, native phone use and first-useful-word latency remain open. Keyword spotting can activate on a similar phrase/name in background speech. Reload/close ends this Web opt-in; this is not an OS always-on daemon.

## Verification and operation

Local suite/build results are in [backend](backend-tests-final.txt), [focused lifecycle](final-focused-tests.txt), [frontend](frontend-tests.txt) and [build](build.txt). These distinguish full-suite runs from later focused checks; no CI. Known test-library deprecation and existing large-chunk build warnings are retained.

Vite5191 -> API8861 uses existing synthetic work-ui-01. API PID80987 at this checkpoint uses the active checkout's .venv, explicit full OpenAI model/marin, existing protected credential file, and verified ignored wake-model path. Scheduler/computer/background-text execution remains off for this preview. Startup is nonbillable; owner speech/text after activation is separate from the closed experiment.

Updated current product/entry/handoff, decisions/work log, [integration contract](../../../desk-companion/docs/openai-alice-wake.md), desktop/Omni/operator/maintenance/evaluation guidance. [Cost scenarios](cost-scenarios.json) use current official rates and state all exclusions. Publication is not a main merge, deployment or complete personal-agent acceptance.

Final checks: full1716 backend run passed, followed by16 focused checks including one new idle-close case (1717 distinct cases, not one combined command);314 frontend, type/build and Ruff pass. [Summary](validation-summary.json). Real provider experiments are closed. Browser QA used the actual local microphone only for standby, never a live provider call. Selected screenshot has no personal input/media.
