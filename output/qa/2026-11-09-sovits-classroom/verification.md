# Group 2 · GPT-SoVITS trial and classroom Ethernet

9 November 2026, Asia/Hong_Kong. The owner asked to test GPT-SoVITS and check the Pi connected to classroom Ethernet. The technical model trial and classroom connectivity check are complete; owner-approved voice quality and production conversation integration are not.

Later owner feedback: these public-reference voices were explicitly rejected as more artificial than OpenAI and unsuitable for the requested sweet/cute Taiwan-Mandarin delivery. The technical observations below are preserved. The current next step is routed through the separately authorized [two OpenAI auditions](../2026-11-09-sweet-taiwan-audition/verification.md); the original reference-request next step at the end of this historical trial is superseded for that comparison.

## Reading and scope

Read AGENTS workflow, current product requirements, handoff/START, latest reference-voice decisions, the November9research/14-case corpus, current Pi network profiles and relay/OpenAI transport contracts. Preserved earlier focused reads rather than restarting all historical Markdown. Read selected upstream requirement/config/API/model-loading/portable-runtime/text-preprocessing/language-detector sections and the official dataset/model sources. Third-party README commands were treated as evidence; no whole installer or unrelated instruction was executed.

Memory was used only to restore the reference-voice preference and evidence boundary; live state was checked. No nested AGENTS was found. Production app code, network profiles, firewall, DNS, VPS service configuration, keys and voice defaults were not changed. The existing power/red-LED investigation remains deferred. No CI or paid generation.

## Pi field result

The original pinned Pi identity authenticated through the existing VPS relay. Classroom Ethernet obtained a DHCP lease and carrierUP. Default route metric100 on eth0 takes precedence over active classroom Wi-Fi's600 route; the actual route to the VPS used eth0. This separately closes the earlier classroom-wired field-test gap. Wi-Fi was observed active as the secondary route; cable-removal/failover was not tested.

Pi app/application user services and both OpenAI system transport services were active. A credential-protected GET /v1/models through the existing explicit loopback proxy returned HTTP200. It made no generation or audio request. The Mac loopback8891preview was restored; health, automatic-owner session, workspace and device-page HTTP checks passed. Current Mac5190/8831health also passed.

Direct SSH to the classroom Ethernet address closed; no direct cross-VLAN access is claimed. An intermediate relay connection closed, and the one-shot Mac preview later timed out. The Pi retained the same boot ID. The existing reconnecting Mac relay launcher was then started with automatic UI opening disabled; fresh automatic-owner/workspace/device-page checks passed. No new connection loop was implemented. There is no long-duration reliability claim. No network-policy bypass, account guessing, SD-card change, hotspot, power intervention or setting reset was performed. Private addresses/boot ID/raw logs stay under ~/.config/desk-companion/sovits-classroom-20261109/.

## Isolated model setup and failures retained

Official GPT-SoVITS commit04a44eb was installed outside the repository/production environment at ~/.local/share/desk-companion/experiments/gpt-sovits-20261109/. Profile: V2ProPlus CPU/float32, Python3.12.13, torch/torchaudio2.7.1, transformers4.51.3. Main checkpoint/auxiliary digests were checked; fastText publisher MD5 and a local SHA256 were recorded. Model/data binaries are not published. [Manifest](model-manifest.json), [environment lock](environment-lock.txt).

Actual requests exposed missing resampy, an upstream NLTK path override and a missing language-detection cache directory. resampy was installed in the isolated environment. NLTK automatic download was rejected by a network-safety check; the already downloaded, verified local corpus was mapped into the required directory. The denied fetch was not retried through a different route. The separate fastText model was obtained by its normal library download path after creating its expected cache directory. No guard/proxy/DNS restriction was disabled. The first Chinese request's54.822seconds includes that one-time model download.

All failures remain in private reports/logs. Upstream inference code was not patched; only its normal generated pronunciation-cache marker changed. The final API successfully started at127.0.0.1:9880. Missing reference input returned400. The server was stopped after testing to release Mac memory.

## Actual synthesis and timing

Reference is the author's public-domain LJSpeech8.397-second sample LJ025-0076, with matching text. It is a technical fixture, not the owner's selected Alice sound, not the existing OpenAI voice, and not a training dataset. [Dataset provenance](https://keithito.com/LJ-Speech-Dataset/). No user microphone was recorded or uploaded.

English/Mandarin/Cantonese greetings and time sentences produced six validated32,000 Hz mono PCM16 WAV cases. The three longer streaming requests had first received non-silent PCM at2.129s/2.679s/1.641s, total request4.677s/4.557s/3.373s and audio duration5.52s/5.12s/5.08s. These are single-batch byte-arrival observations, not p50/p95 or audible browser/hardware latency. The later non-streaming English recheck took9.725seconds for the same5.52second waveform; latency is variable under the existing Mac load.

Closing a longer stream after4096bytes caused the first subsequent request to time out at30seconds. Server logs later showed progress, so permanent deadlock was not established. A repeat completed the next utterance in4.05seconds, with no inference-code change between attempts. Both results are retained; interruption stability is NOT passed or fixed. Physical playback/AEC/barge-in with this engine was not tested.

## Independent content check

The host's audio-input tool could not perform direct listening. Instead, generated samples were independently transcribed locally with Whisper Base and then Whisper Small. This is an auxiliary content check, not a human tone/naturalness judgment. Model sources are the official Systran conversions of OpenAIWhisper; no hosted ASR call or fee. The verifier initially missed its vocabulary file; after adding the actual published file, its PyAV file-input compatibility issue was handled through the documented16kHz NumPy input route using validated localWAVPCM.

English and Mandarin time/meeting content matched with the larger verifier. Cantonese did not reliably match: expectedten o'clock was read asthreebyWhisper Small. The smaller model also produced substantial Chinese/Cantonese recognition errors. This cannot distinguish ASR weakness from TTS pronunciation without further validation, so Cantonese numeric/pronunciation accuracy remains open. Do not report all three languages as naturally or accurately spoken merely because they generated audio.

## Code checks, artifacts and remaining gate

Added scripts/sovits_smoke.py: explicit loopback destination, no redirects, bounded text/audio/readtimeouts, reference-duration validation, new-output requirement, partial/failure reports, PCMvalidation and timing/hash records. Six meaningful regression tests passed for destination/credential refusal, redirect refusal and silent/truncated output; scoped Ruff and compilation passed. No full production suite was rerun because production code was unchanged; earlier2103/351numbers retain their prior scope.

The14-line corpus is now marked partially exercised with a public reference, while owner audition remains pending. Updated network field status, dedicatedevaluationcontract, researchsnapshot routing, product, decisions, worklog, handoff andentry. Public [summary](validation-summary.json) excludes credentials, hostIP, privateIDs and audio. Local generated samples and rawerrors stay in the experiment directory. [Evaluation contract](../../../desk-companion/docs/sovits-evaluation.md).

Next: obtain the approved reference/transcript, prepare a clean3–10second input segment, and assess the actual desired sound. Resolve Cantonese accuracy and interruption/latency variability before an integrated ASR→existing OpenAI/tools→TTSroute or default switch. No new paid budget, model training, automatic sending or deployment was authorized by this trial.

Publication: reviewed trial head4156a31 matched the remote branch; PR97 remains open/unmerged. Diff/link/JSON/credential/artifact checks passed. Model weights, private addresses, raw logs and audio are excluded. [Receipt](publication.json).
