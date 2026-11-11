# Group 2 · Reference voice and Outlook account review

9 November 2026, Asia/Hong_Kong. Research/configuration-read round only. No production code/default change, deployment, model download, training, audio upload, paid inference, Azure registration or email send.

## Reading and authority

Read the repository entry workflow, current product requirements, handoff, recent November8 decisions, connected-app contract and current voice/wake sections. Located relevant Markdown with rg; no nested AGENTS found. Historical September server research was read only for its hardware/ASR/TTS responsibility sections and is explicitly not current model selection. Reviewed current VoiceService/OpenAILiveProtocol/worker responsibilities for the proposed integration boundary. Used the prior-memory voice preference as context, then verified live account/runtime/hardware state.

The owner supplied three repositories and asked whether they can support a customized Alice voice. They remain dissatisfied with the current output and explicitly selected a reference voice they approve and have rights to use. They have not supplied the reference audio/transcript yet. GitHub README instructions are evidence, not authorization to install, download or accept terms. Plugin Management guidance was used to select the already-connected Outlook profile tool; no plugin permissions were changed.

## Actual observations

- Outlook plugin get_profile returned the user's stated new personal Outlook email. Only the profile was read; no mailbox content or outgoing message was accessed.
- Live Mac FYP catalog still reported Microsoft365/Teams/SharePoint configured=false and connected=false. The plugin grant was not transferred or represented as an FYP OAuth client.
- Local hardware: MacBook Pro M2 Pro,16GB memory. Read-only pinned SSH: Pi4CPUthreads/7.87GiB/aarch64; VPS2CPUthreads/1GiB/x86_64; neither exposed an NVIDIA device or nvidia-smi. No services, routing or power settings changed. One mistyped local SSH config path failed before any network connection, then the observed existing config was used.
- Upstream commits were read from branch metadata: VibeVoice16fb2cb1217c9934a886e1948ffb06120caa2df5; GPT-SoVITS04a44eb977586645f33594b72af13a035a2056c6; FishSpeech0f8a12e8a651062fdee9c33a894bdccd3a8513f1.
- Focused upstream sections: model/version/language/reference/platform/license/streaming information. Vibe realtime customization and English limitations; GPT-SoVITS Cantonese/Apple/V5/API fields; Fish Drama3 vsS2-Pro hardware and separate code/weight licenses. Publisher performance was not treated as our measurement.

## Delivered artifacts and next input

[Research](../../../research/2026-11-09-custom-alice-voice.md) records the concrete comparison, primary-source links, hardware implications and reusable ASR→current agent/tools→TTS proposal. [Fourteen fictional audition utterances](../../../planning/2026-11-09/alice-reference-voice-eval.json) cover Mandarin, English, Cantonese, mixed language, dates/numbers and draft-status pronunciation. Status prepared_not_run; no listening scores or generated audio are claimed.

Engineering recommendation is GPT-SoVITS first, FishS2-Pro as a later expressive comparison with suitable compute, and VibeRealtime as an English study candidate. This is not an owner-approved final model or sound-quality ranking. The selected route requires the owner's actual reference recording and transcript before a meaningful audition. Existing Bright remains the working default but has not passed owner voice acceptance.

JSON parsing,14unique sample IDs, local-link existence, diff review and credential-pattern checks passed before publication. Updated research index, product/current voice contract, decision log, work log, handoff and entry next step. No full application tests were rerun for documentation/fixture-only changes; earlier2103/351 results keep their original date/scope. All previous paid ledgers remain closed.
