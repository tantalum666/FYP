# Group 2 · Alice reference-voice options

Research snapshot from early 9 November 2026, Asia/Hong_Kong, before the owner selected GPT-SoVITS testing. The research itself made no model download or inference. Later that day, an isolated V2ProPlus CPU technical trial generated English/Mandarin/Cantonese samples using public-domain reference audio; owner-selected voice quality remains open. See [actual results](../output/qa/2026-11-09-sovits-classroom/verification.md) for installation, latency, interruption and transcription limitations.

## Owner decision and current acceptance

The owner remains dissatisfied with Alice's voice after the previous changes, and explicitly chose **customization from a reference voice they like and have the right to use**. That replaces further blind prompt-only voice iteration as the next step. The previously verified Bright selection proves that the requested voice was used; it does not constitute owner acceptance of the sound. No actual reference clip has yet been supplied for this new route.

The target remains one recognizable Alice voice with natural Mandarin, English and colloquial Hong Kong Cantonese, a light and friendly character, and natural short conversational replies. Voice similarity, accent, delivery and response delay are separate dimensions. OpenAI remains the default reasoning/tool provider; changing synthesis does not require replacing the agent's existing application tools.

## Repository snapshots

| Project | Checked main commit | Scope read |
|---|---|---|
| Microsoft VibeVoice | `16fb2cb1217c9934a886e1948ffb06120caa2df5` | README model/news sections; MIT license; Realtime0.5B documentation and model card; demo entry point |
| GPT-SoVITS | `04a44eb977586645f33594b72af13a035a2056c6` | README features/platforms/V2Pro/V5 notes; MIT license; latest relevant changelog entries; api_v2 synthesis/streaming request fields |
| Fish Speech | `0f8a12e8a651062fdee9c33a894bdccd3a8513f1` | README models; current license terms relevant to research/product use; installation/inference hardware/reference/streaming sections; S2-Pro and Drama3 model cards |

Branches and source files were read through the GitHub connector; official model/documentation pages were checked separately. Publisher benchmark figures are not measurements on our machines.

## Comparison

### GPT-SoVITS — first reference-voice candidate

The official README explicitly supports Chinese, English and Cantonese (`zh`, `en`, `yue`), alongside Japanese/Korean. It advertises zero-shot synthesis from approximately five seconds of reference audio and few-shot fine-tuning from approximately one minute. Those are entry capabilities, not guarantees that any short/noisy clip will sound good. Its API accepts reference audio plus transcript/language, output language, speed and streaming controls. [Pinned README](https://github.com/RVC-Boss/GPT-SoVITS/blob/04a44eb977586645f33594b72af13a035a2056c6/README.md), [API](https://github.com/RVC-Boss/GPT-SoVITS/blob/04a44eb977586645f33594b72af13a035a2056c6/api_v2.py).

V5 is already documented, including improved similarity without SoVITS fine-tuning and a changed vocoder. Its CUDA acceleration route is not an Apple performance guarantee. V2Pro/ProPlus remains a useful smaller baseline; compare versions after selecting the reference rather than blindly following an old V1 tutorial. The README reports ProPlus RTF0.526 on an M4 CPU, which measures throughput, not first-audio latency on this M2 Pro. macOS is documented, but the project warns about Mac GPU training quality and temporarily uses CPU training. Begin with inference, not training from scratch. [V5/platform notes](https://github.com/RVC-Boss/GPT-SoVITS/blob/04a44eb977586645f33594b72af13a035a2056c6/README.md#v5-release-notes).

The source code uses MIT. Check the chosen weights, dependent models and reference-audio rights independently before distributing a trained voice. Engineering recommendation: use this as the first controlled three-language reference audition; no particular version or resulting voice is accepted yet.

### Fish Speech — expressive comparison with a heavier deployment requirement

Current Fish Speech is not just the older1.x tutorial stack. The repository offers S2-Pro and Drama3. S2-Pro supports reference cloning and natural-language delivery tags; its model card lists Chinese and English among the main languages, but does not explicitly establish Cantonese quality. Do not turn “Chinese” or “80+languages” into a claim of natural Hong Kong Cantonese. A separate `yue` listening test is required. [S2-Pro card](https://huggingface.co/fishaudio/s2-pro), [pinned model overview](https://github.com/fishaudio/fish-speech/blob/0f8a12e8a651062fdee9c33a894bdccd3a8513f1/README.md).

The current official installation guide specifies at least24GB GPU memory for S2-Pro's GPU path, with a CPU path also offered. Drama3 is35B-A3B, requires at least48GB at FP8 and supports NVIDIA only in the documented runtime; CPU, Apple MPS and AMD ROCm are not supported for that model. “3B active” is not a3GB memory requirement. The advertised roughly100ms S2-Pro first audio is on an H200, not this Mac/Pi/VPS. [Installation](https://speech.fish.audio/install/), [inference](https://speech.fish.audio/inference/).

License versions matter: the current code/Drama3 use the Fish Audio Community License; S2-Pro weights remain under the Fish Audio Research License. The latter permits research/noncommercial use and requires a separate commercial license. The Community License has attribution, revenue and hosted-service conditions, with specific provisions for assistant replies and noncommercial research demos. FYP research use is a candidate permitted use subject to the selected artifact's terms; do not call all versions MIT or assume unrestricted commercial deployment. [Current license](https://github.com/fishaudio/fish-speech/blob/0f8a12e8a651062fdee9c33a894bdccd3a8513f1/LICENSE), [S2-Pro license section](https://huggingface.co/fishaudio/s2-pro#license).

Engineering recommendation: retain S2-Pro as the expressive comparison when suitable compute is available. Drama3 is not the first deployment target on the currently verified hardware. This is a resource/fit decision, not a measured sound-quality ranking.

### VibeVoice — not the primary three-language reference route

VibeVoice is a family containing both ASR and TTS. Its new ASR/CPU/streaming releases recognize speech; they do not by themselves replace Alice's generated voice. The repository states that the original long-form TTS code was removed in September2025; its historical multilingual demos are not proof that the current Realtime0.5B entry point provides the same capabilities. [Pinned overview](https://github.com/microsoft/VibeVoice/blob/16fb2cb1217c9934a886e1948ffb06120caa2df5/README.md).

Realtime0.5B is primarily English. The nine experimental additional languages listed do not include Chinese or Cantonese, and the documentation continues to warn about unpredictable non-English output. Speakers are provided as embedded voice prompts; customization is directed to the project team rather than a documented arbitrary-reference upload workflow. Its documentation reports hardware-dependent initial audio in the200–300ms range and real-time tests on T4/M4 Pro; that is not a result on our M2 Pro. The streaming-input capability wording and remaining TODO also deserve implementation verification before integration. [Realtime documentation](https://github.com/microsoft/VibeVoice/blob/16fb2cb1217c9934a886e1948ffb06120caa2df5/docs/vibevoice-realtime-0.5b.md), [model card](https://huggingface.co/microsoft/VibeVoice-Realtime-0.5B).

Code/model metadata report MIT, while the project describes a research intended-use boundary. It can be studied as an English low-latency comparison. It does not satisfy the present reference-voice plus Mandarin/English/Cantonese requirement based on the official current workflow.

## Verified local resources

Read-only checks in this round found:

| Host | Observed resources | Proposed responsibility |
|---|---|---|
| MacBook Pro | M2 Pro,16GB unified memory | First isolated GPT-SoVITS inference/voice audition; measure actual memory and cold/warm latency before integration |
| Raspberry Pi | Four CPU threads, approximately7.87GiB RAM, aarch64, no NVIDIA inference device | Existing wake, capture/playback, Alice UI and application core; no claim of heavy TTS real-time performance |
| Existing VPS | Two CPU threads,1GiB RAM, x86_64, no NVIDIA device or nvidia-smi | Existing relay/control role; unsuitable as the selected heavy real-time TTS host |

No resource upgrade, subscription or GPU rental was requested or purchased. The previously discussed school DGX/V100 is historical/unconfirmed capacity, not currently available deployment hardware.

## Maintainable integration proposal

```mermaid
flowchart LR
  Mic[Microphone] --> Wake[Existing local Alice wake]
  Wake --> ASR[Speech recognition]
  ASR --> Agent[Existing OpenAI reasoning and tool service]
  Agent --> Reply[Verified reply or explicit draft status]
  Reply --> TTS[Selected reference-voice synthesizer]
  TTS --> Play[Existing playback and Alice output meter]
```

Current GPT Live owns its generated audio. External GPT-SoVITS/Fish model weights cannot simply be entered into the Live voice selector. A separate ASR→existing text/tool service→TTS route is required. Avoid producing and paying for a complete Live reply only to synthesize it again. Keep the Live implementation as an explicit baseline during evaluation, with no silent fallback or new paid test authorization.

Reuse the existing conversation, tool authority, result receipts, microphone ownership and playback cancellation. A synthesis adapter receives only a validated voice-profile ID, language and permitted reply text; it has no tool/approval capability. Resolve approved reference paths in backend-owned profiles, not arbitrary model-supplied paths/URLs. Normalize returned PCM to the existing playback contract. Cancellation must stop playback immediately and discard late chunks; provider-generation cancellation is a separate observation. Do not create a second persistent chat store or duplicate the30-tool catalog.

Keep the UI in Assistant style: selected profile, cached audition and speaking-style control. Engine/model/debug detail belongs in expandable configuration. Merely installing a TTS WebUI does not satisfy hands-free wake, interruption, cross-app operation or synchronized captions.

## First audition and acceptance

1. Obtain the owner's chosen reference with usage permission and an accurate transcript. Suggested initial material: one clean speaker,10–30seconds without music/other speakers; longer licensed material can support a later fine-tune. If three-language material exists for the same speaker, retain those language labels. These are engineering preparation recommendations, not mandatory model minima.
2. Run a small zero-shot audition before training. Use the [fixed local corpus](../planning/2026-11-09/alice-reference-voice-eval.json) for Mandarin, English, Cantonese, mixed language and date/number pronunciation. Compare with cached Bright as a baseline, without using its audio to train another model.
3. Let the owner choose on voice fit and naturalness. Record language-specific pronunciation, timbre consistency, missing/repeated words, cold/warm first-audio time, synthesis throughput and peak memory. Publisher RTF numbers are not end-to-end latency evidence.
4. Only after the sound is acceptable, integrate a bounded streaming route and test playback interruption, late-chunk rejection, caption alignment and calendar/mail/browser draft workflows through the existing services. Any new paid OpenAI experiment needs a fresh cap; all previous budgets remain closed.

At this research snapshot no candidate had been synthesized. The subsequent technical trial is linked above; it does not replace the still-missing owner reference or establish voice acceptance. Bright remains the production baseline, not an accepted final sound.

## Microsoft account follow-up

The Outlook plugin's profile read confirmed the owner's newly connected personal Outlook account. No emails were read or sent in this round. A separate read of the live FYP app catalog still shows Microsoft365/Teams/SharePoint as unconfigured/unconnected. Codex's grant is not an FYP OAuth client or transferable token.

FYP still needs its own Microsoft app registration and delegated account consent. A new Outlook mailbox does not establish access to the old school's Entra tenant or the developer role. The current registration guide requires a suitable Azure account/tenant and application-developer access. Organization-only Teams/SharePoint capabilities do not become personal-Outlook features. [Microsoft registration guide](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app), [Teams permissions](https://learn.microsoft.com/en-us/graph/api/chat-list-messages?view=graph-rest-1.0), [SharePoint followed sites](https://learn.microsoft.com/en-us/graph/api/sites-list-followed?view=graph-rest-1.0).

Prior Microsoft authorization was deferred by the owner. This round verifies the new connector account and readiness distinction; it does not create an Azure subscription, accept new Microsoft terms or register a client on the owner's behalf.
