# Group 2 · OpenAI voice and Alice wake listening

## 8 November evening: verified voice selection and review delivery

A fresh owner-approved USD1 round is closed at conservativeUSD0.346456, with all five sessions finalized. Original, Gleam and the new Alice · Bright samples each returned actual Mandarin/English/Cantonese text and audio; provider echoes matched the requested voice. Bright is selected for the normal Mac runtime and its real sample is cached. This supersedes the earlier lack of a successful audition for the original voice; the earlier failed ledger remains closed and separate.

The successful full-browser run used the then-current29-tool catalog, three delegated responses and49providerseconds. First audible output after three inputs was about1.488s/1.633s/1.254s; this includes acknowledgments, not first useful task-answer latency. The later OAuth/read integration extends the catalog to30tools and has local protocol coverage, not another paid full-browser run. Naturalness and accent quality remain subjective; no human acoustic acceptance is claimed.

Sustained120ms input onset avoids treating every energy flicker as a new utterance. Playback retains80ms initial/120ms recovery lead and a bounded30second queue, with rebuffer diagnostics. A delivered proposal emits `turn_review` and clears the response deadline without pretending that speech played; the first browser run exposed that timeout and remains recorded as failed. Requested/provider-confirmed voice and settings version are retained as private diagnostics. A returned mismatching voice fails closed. [Current QA](../../output/qa/2026-11-08-caption-mail-voice/verification.md).

## 8 November: transcript groups, voice preferences and slow startup

`live_captions.py` groups display fragments from validated `start_ms`/`end_ms` on the provider session timeline; it does not call a gap “provider-final” or use playback completion as conversation history. `conversationTranscript.ts` updates stable speaker messages and selects only the newest reply on the compact home. Accepted Live text enters the existing bounded conversation buffer after the current grounding gate. Late older fragments cannot replace the latest reply. The provider supplies no completed-turn marker; the 700 ms input-gap/assistant-response display rule remains a presentation heuristic, not identity or action authority.

`voice_settings.py` stores owner-selected Live voice and delivery wording in two additive private SQLite tables. The owner/version/idempotence boundary uses the existing operation service. Changes during an active session are refused; choices apply on the next explicit/wake-triggered session. Custom voice IDs are allowlisted from owner registration, transmitted as `{id: ...}`, and never used as file paths. Cached previews use a hashed local filename, owner authentication and size/symlink checks. No preview is generated automatically. Full runtime backups include these tables; portable personal-history exports deliberately exclude project-bound provider resources.

Official [custom voice documentation](https://developers.openai.com/api/docs/guides/custom-voices) supports free prompt-to-voice creation for GPT Live. One original light/warm adult feminine voice was created for Alice with natural Mandarin, English and colloquial Hong Kong Cantonese as the design goal. Its metadata was accepted by `session.started`, but the first USD0.25-capped audition produced no speech and no final usage receipt. USD0.249 remains conservatively reserved in the now-closed ledger; it is not confirmed spend. A saved voice resource is not a successful naturalness audition. Realtime and Qwen are unchanged and do not receive this Live-only prompt voice.

That trial exposed silent warmup filling the old five-second pre-ready speech buffer, and a client disconnect ending receipt collection. Silent startup now retains only half a second of preroll while the separate ten-second connection deadline applies; voiced pre-ready audio retains the original five-second safety bound. `voice_shutdown.py` drains final Live/backend receipts with one socket reader even after the browser disconnects. Missing receipts still remain unknown. A 6.5-second delayed-start offline browser replay and disconnect/finalization tests pass. No additional paid generation followed the closed audition ledger. [Actual scope and results](../../output/qa/2026-11-08-dialogue-voice/verification.md).

Historical baseline: 2 November 2026, Asia/Hong_Kong. Owner requested OpenAI integration and selected calling Alice to wake. This replaces the earlier Qwen-only manual-preview choice for the current software session; Qwen, Gemini and other candidates remain available for comparison.

## Current interaction · updated 7 November

The primary Web chat retains Alice, shared tasks, memories, permissions and action cards. Enable **Say Alice to wake** once and allow the microphone. While waiting, PCM goes only to the connected desk's local keyword detector. On this Mac preview both browser and detector are on the same machine. Calling Alice or its Mandarin pronunciation wakes the normal voice client; only then does it request an OpenAI session.

The call accepts successive spoken turns without another button. After30 seconds without conversation activity, OpenAI closes and local listening resumes. Existing600-second overall session bound remains. Errors stop automatic listening instead of looping paid retries. Turning off the switch, changing identity, leaving the relevant view or closing the page releases the appropriate capture/socket resources. Returning from a temporarily suspended view can resume an enabled local listener; page reload restores a saved owner/origin-scoped opt-in only when the browser reports microphone permission already granted. Unsupported or ungranted permission leaves it off without prompting. This is not an OS-login/background daemon or a claim of native-phone background operation.

Typing a submitted message pauses local waiting without deleting the standing wake choice. With Live selected, typed input uses the existing Responses text path; Live is voice-only in this implementation. Long-idle client context is cleared before reuse so a new wake does not depend on an expired30-minute server context. Provider changes end the old connection and clear its resume handle without rewriting visible messages or unsent input.


## 7 November complete-catalog startup repair

The owner's normal wake attempts exposed a defect the restricted query smoke trial did not cover: schema flattening removed business title properties. The complete27-tool startup now preserves property names and passes an actual OpenAI preflight (old payload400, repaired payload200). The current shared Microphone selector applies the same exact input to preview, wake and voice; the normal Mac Web origin now selects its built-in microphone rather than an implicit system default.

A separate complete-app browser evaluation used real native capture permission/lifecycle and synthetic transmitted speech, the full production tool catalog, actual Live/Responses, calendar lookup and browser playback acknowledgement. Three sessions finalized and returned to local waiting; the final answered Alice identity and two fictional meeting times correctly. USD0.1864995conservative accounting, USD0.50repair ledger closed. Useful post-input playback6.393seconds remains above the approximate5second target. The prior USD1trial below used a restricted tool list; its scope does not substitute for this full-catalog check. [Repair QA](../../output/qa/2026-11-07-alice-wake-repair/verification.md).

Provider rejection records bounded error identifiers and phase, without raw error messages or private input. The UI distinguishes configuration rejection from microphone permission and clears a previous failure when a new deliberate attempt starts. Errors still stop paid retries.

## 7 November current Live implementation

The owner selected GPT Live as the primary voice route and retained Realtime as a comparison option. `openai_live.py` adapts native Live sessions and Responses delegation to the existing VoiceService/ToolDispatcher. Speech uses gpt-live-1; delegated business reasoning and independent text/browser requests use gpt-6.1-sol. `configure_openai.py --voice-provider openai_realtime` explicitly selects the retained comparison route. There is no silent provider fallback, new business queue or frontend credential.

Alice identity is included both in the speech instructions and in the invariant shared persona rules, including previously saved custom personas. Calling Alice starts a short greeting and accepts successive spoken turns. Local keyword listening and cloud voice share one locked slot. Same-owner session renewal rearms local listening; it does not automatically reopen paid voice after a failure.

Live backend completion is not spoken-output completion. Quiet caption grouping is explicitly a local display boundary; user transcript fragments remain unfinalized in the voice ledger. Shutdown requests session.close and drains the final usage receipt. Cumulative duration replaces earlier snapshots, backend receipts are deduplicated, and incomplete receipts stay marked unconfirmed. Thirty-second inactivity and the existing 600-second overall limit apply; a maximum of twelve delegated backend responses bounds a session. These limits are not an account-wide dollar cap.

No image or typed command is sent through this Live adapter. The shared camera panel still supports local preview; explicit cloud frame sharing remains available with a compatible selected provider such as Realtime. Existing owner authority, tool versions, confirmation, cancellation and result checks remain in the business services.

The fresh owner-approved USD1 /45-second synthetic trial is closed: local Hey Alice detection, correct Alice identity, a real calendar_query over two fictional meetings at10:30/14:00, returned audio, no calendar writes and released session slot. Provider duration20seconds; two delegated requests with5830input/133output tokens. Conservative accounting USD0.0518613333, not an invoice. The trial was manually stopped after the complete answer; idle closure was checked separately with offline protocol tests. Human microphone/speaker/AEC quality and a controlled Live-versus-Realtime comparison remain open. [Full QA](../../output/qa/2026-11-07-alice-home-wake/verification.md).

Current Mac uses Web5190/API8831, the approved private key reference, verified pinned wake models and the shared [Alice home](alice-home.md). Pi readiness/activation is recorded separately in that QA. Earlier runtime/default statements below are dated historical evidence, not instructions to restore those settings.

## Responsibilities

- `voice_protocols.py` holds the shared response/cancel/grouped-tool lifecycle and existing Qwen/Gemini formats. `openai_voice.py` adds the OpenAI GA format, event aliases and streaming16-to24k resampling. Existing browser/local-worker16k input and24k playback contracts remain intact.
- `VoiceService` retains authenticated tickets, session/task context, tool dispatch, independent authority, response grounding, cancellation and usage records. OpenAI uses the same business services; no second task/approval/queue system exists. Application-owned cancellation avoids double-cancelling through automatic server VAD.
- `WakeListening` owns only a short-lived owner/session/origin-checked local PCM channel and one detector slot. It cannot call a provider or execute business tools. Its tokens expire, are single-use, and audio rate/size are bounded.
- `WakeAudio` owns browser capture/local transport; `useAliceWake` coordinates local waiting and the existing cloud conversation. Local microphone state is not labelled microphone-off while the listener is armed.
- The pinned existing sherpa-onnx bilingual model uses fixed Alice phone sequences and a short silence prefill. Model files remain ignored runtime assets; raw audio is neither logged nor saved by this channel. Keyword-only activation can still misfire on similar words or background speech containing the name; human/noise/AEC validation remains open.

## 2 November Mac preview configuration (historical)

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


## 6 November Pi integration (superseded default)

The earlier Pi checkpoint added shared Alice/conversation with automatic local entry
and retained Qwen Omni. The owner's later OpenAI-default instruction supersedes
that provider choice; the runtime status below is current. Read-only wake weights
load successfully using a temporary keyword file, and the frozen audio extra
includes numpy. Pi currently exposes no capture device. No new OpenAI/Qwen paid
trial or human wake accuracy result was produced. A standalone synthetic Alice
sample on Mac did not trigger and remains a recorded gap. See the [actual Pi QA](../../output/qa/2026-11-06-passwordless-device/verification.md).

## 6 November OpenAI default and browser release

At the 6 November checkpoint, Mac and Pi explicitly selected OpenAI Realtime2.1; independent text/Work and
browser computer calls use OpenAI Responses with GPT6.1Sol. Existing supplier
adapters remain available, but there is no silent fallback to Qwen. Keys are read
from approved owner-private files, and background model generation stays off.

Mac's free model catalog check succeeded and normal service configuration is
ready. Pi's provider returned `unsupported_country_region_territory`; this is
shown explicitly and generation is disabled there. A local Alice wake detector
being available does not overcome that provider refusal. No model-generation,
human wake or microphone trial was performed in this release. The new public
browser's real execution checks use scripted planning, including on Pi.
[Current source, deployment and QA](../../output/qa/2026-11-06-openai-agent-merge/verification.md).


## 7 November Pi VPS route

The owner subsequently directed Pi to use the existing owned VPS. That explicit
route now returns authenticated model-list200and Realtime session.created;
normal voice/text/computer configuration is ready and the old direct-path region
flag is cleared. See [transport and actual limits](openai-vps.md). No microphone,
audio input, response.create, generated answer or paid voice trial occurred.
