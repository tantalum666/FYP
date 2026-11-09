# Group 2 · Local GPT-SoVITS evaluation

9 November 2026. The owner selected GPT-SoVITS testing, then explicitly rejected these samples as more artificial than OpenAI and unsuitable for the desired sweet/cute Taiwan-Mandarin voice. This remains a technical record, not an accepted Alice candidate. Do not repeat the same public-reference audition as a proposed solution. The later owner-approved OpenAI comparison is recorded in the [current voice brief](../../planning/2026-11-09/alice-sweet-taiwan-voice.md).

This checkpoint is an isolated Mac synthesis experiment, not a replacement for production Alice voice, a trained custom speaker or a complete ASR/agent/TTS conversation route. No owner-selected reference recording was supplied for this trial; that does not invalidate the owner's rejection of its actual sound.

## Tested setup

- Official source: `RVC-Boss/GPT-SoVITS`, commit `04a44eb977586645f33594b72af13a035a2056c6`.
- Profile: **V2ProPlus, CPU, float32**, on the existing M2 Pro/16GB Mac; six CPU threads. MPS/V5/GPU inference was not tested.
- Separate Python3.12.13 environment: torch/torchaudio2.7.1, transformers4.51.3 and upstream requirements. `resampy` was additionally needed for the actual reference resampling path. The production FYP virtual environment and voice configuration are separate.
- Official linked checkpoints/auxiliary data were downloaded and checked against their published large-file digests. Initial11files total1,902,028,524bytes; fastText language identification adds131,266,198bytes. Model binaries are outside Git.
- Experiment directory: `~/.local/share/desk-companion/experiments/gpt-sovits-20261109/`. It retains source, environment lock, CPU profile, start helper, download manifests, private logs and generated WAVs.
- API was bound only to127.0.0.1:9880. The test process is stopped after verification to release memory; the installed environment, cache and results remain reusable.

## Setup defects found and resolved

The first actual synthesis request failed because `resampy` was not present in the resolved upstream requirements. Installing it in the isolated environment resolved that dependency.

Upstream `tools/portable_runtime.py` overwrites NLTK_DATA with `source/runtime/nltk_data`. Our previously downloaded corpus was at the experiment root, so import-time NLTK downloads were attempted and rejected by a network safety check. The fix maps the existing verified offline corpus into the path the application expects. No network restriction, DNS or download guard was disabled, and the blocked fetch was not retried through another route.

Chinese preprocessing also required the explicitly configured `pretrained_models/fast_langdetect` cache directory. After creating that directory, the library obtained its official fastText model through its normal download path and verified the publisher MD5. The completed file's SHA256 is retained. This is a different model/resource from the blocked NLTK download. It must be prepared before a production readiness claim; the first Chinese request included this one-time download.

No upstream inference-code patch was required. A pronunciation-cache MD5 marker was rewritten by the upstream runtime; it is not a model/code change. Setup instructions must keep the NLTK mapping, resampy and language-model cache, rather than report that pip installation alone is sufficient.

## Reference and audio evidence

Technical reference: the8.397second,22050Hz mono LJSpeech clip `LJ025-0076.wav`, downloaded from the dataset author's sample page. The author identifies the recordings/text as public-domain material. It is used only as a noncommercial technical reference, not as the owner-approved Alice voice or a fine-tuning dataset. [Dataset and provenance](https://keithito.com/LJ-Speech-Dataset/).

GPT-SoVITS's actual prompt-segment check in this profile accepts3–10seconds. A longer owner-supplied recording should be preserved and a suitable clean segment prepared from it, with the matching transcript. Do not send an entire30second recording straight to this API.

Three greeting requests and three longer time/meeting requests generated validated mono PCM16 WAV files at32000Hz, covering English, Mandarin and Cantonese request modes. The six corpus entries are a technical subset of the14prepared lines; mixed-language and owner-voice acceptance remain pending.

| Streaming time sentence | First received non-silent PCM | Total request time | Generated duration | Request seconds / audio second |
|---|---:|---:|---:|---:|
| English |2.129s|4.677s|5.52s|0.847|
| Mandarin |2.679s|4.557s|5.12s|0.890|
| Cantonese |1.641s|3.373s|5.08s|0.664|

These are one short batch on the existing Mac, not p50/p95, hardware-speaker latency or total conversational delay. The same English sentence later took9.725seconds in a non-streaming recheck, so stable real-time behavior is not established. The first successful Chinese request took54.822seconds because it also downloaded the language detector; do not mix that initialization with cached inference.

Independent local Whisper transcription is an auxiliary text check, not a voice-naturalness or Cantonese-tone judge. Its detailed findings and limitations are recorded in the [QA](../../output/qa/2026-11-09-sovits-classroom/verification.md). No cloud audio-analysis API is used.

## Interruption result

The probe intentionally closed a longer streaming response after the first4096bytes, then requested a new utterance. The first new request timed out at30seconds; server logs show that subsequent synthesis eventually progressed, so a permanent lock deadlock was not established. A repeat completed the next utterance in4.05seconds. No inference-source repair was made between these attempts.

Keep both results. Do not call interruption stable, or treat the successful repeat as proof the timeout was fixed. A future integrated route needs bounded generation cancellation, stale-chunk rejection and tests under realistic memory pressure; current browser/physical playback interruption has not been evaluated with this engine. This is why the experiment does not change Alice's default provider.

## Reusable probe

[`scripts/sovits_smoke.py`](../scripts/sovits_smoke.py) sends explicitly selected corpus cases to an isolated loopback server. It rejects remote/credential-bearing endpoints and redirects, validates the3–10second reference segment, bounds text/audio/read timeouts, preserves failed reports, checks nonempty mono PCM16 output and records hashes/durations. Streaming timestamps refer to receipt of non-silent PCM, not audible playback. It cannot grant app permissions or execute business actions.

Example after starting the prepared local server:

```sh
python scripts/sovits_smoke.py \
  --reference /absolute/path/reference-segment.wav \
  --reference-text /absolute/path/reference-transcript.txt \
  --reference-language en \
  --corpus ../planning/2026-11-09/alice-reference-voice-eval.json \
  --cases en-time,zh-time,yue-time \
  --streaming \
  --output /absolute/path/new-run-directory
```

Use the actual language of the reference, and a new output directory for each run. Six local regression checks cover remote/credential destinations, redirect refusal and truncated/silent audio rejection. They are separate from actual model requests. All prior hosted-model budgets remain closed.

## Gate if this route is revisited

Only revisit with a reference the owner likes and has rights to use, or a materially different agreed candidate. Sound fit comes before further integration. Resolve pronunciation and interruption/latency variability before introducing an ASR→existing OpenAI/tools→TTS route. Reuse current microphone ownership, conversation, approvals and playback; do not install a second agent or task system. Public reference speech, requested-language audio generation, transcription agreement, owner-approved sound and deployed end-to-end conversation are different results. The current next step is the owner's feedback on the younger-delivery refinement of retained OpenAI candidate A, not another LJSpeech run.
