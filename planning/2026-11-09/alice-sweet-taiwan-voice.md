# Group 2 · Alice sweet Taiwan-Mandarin voice brief

9 November 2026. The owner rejected the public-reference GPT-SoVITS samples as more artificial than OpenAI and clarified the desired sound: sweet, soft, cute/youthful feminine Taiwan Mandarin, with warm and natural conversational delivery. This is a sound-selection task. A functioning engine, matched transcript or improved timing alone does not meet it.

## Current audition

The owner explicitly approved up to USD0.10, at most two GPT Live sessions and40seconds combined, using synthetic input and no microphone recording. The approved comparison does not change the production voice before listening. Both samples are now complete; the ledger is closed at conservative USD0.0183333 for20providerseconds. Original voices were created from text descriptions, without a reference recording or named-person/character imitation. Creation is free under the current [OpenAI custom-voice documentation](https://developers.openai.com/api/docs/guides/custom-voices); speech is billed at the current [GPT Live rate](https://developers.openai.com/api/docs/pricing).

| Candidate | Design intention | Current result |
|---|---|---|
| A · Alice · Taiwan Sweet | Light, naturally sweet young-adult feminine voice; relaxed Taiwan-Mandarin conversation, warm rounded vowels, gentle melodic endings | Requested voice confirmed; complete fixed text; owner retains A but finds it too mature |
| B · Alice · Taiwan Soft | Slightly higher, smaller, softer young-adult feminine timbre; clear delicate resonance and lightly playful phrasing | Different requested voice confirmed; complete fixed text; not selected as the refinement base |

Same text for both:

> 欸，我在呀。今天辛苦了，先休息一下嘛。你慢慢說，我有在聽喔。

The prompts avoid announcer cadence, Western-accented Mandarin, exaggerated baby talk, squeaky falsetto, artificial pitch shifting, pinched/nasal tension and excessive breath. These instructions express the intended direction; their acoustic success has not been independently established. Only silence at the waveform edges was trimmed. Voice IDs, request payloads, audio and usage receipts remain in the private owner directory `~/.config/desk-companion/sweet-taiwan-voice-20261109/`. No audio or private profile identifier is published in Git.

## A1 · younger delivery using retained A

The owner said A is promising but sounds older, asked to retain it and make the next version closer to a college or high-school impression. The original A resource/audio remains unchanged. The new performance targets an18–20-year-old adult college-freshman character: clearer/lighter vocal placement, gently brighter resonance, less heavy chest resonance and less slow mature reassurance, with natural small inflections. It reuses the exact A voice ID and original description; only the delivery instructions change. This tests an adjustment to the same voice, not a claim that an immutable voice can be precisely age-edited.

The owner separately approved one session, maximum20seconds and USD0.03. A1 returned the same A voice and complete fixed text, finalized9providerseconds and6.455875seconds of trimmed WAV. Conservative accounting USD0.00825; separate ledger closed. Clip/receipt: `~/.config/desk-companion/sweet-taiwan-younger-20261109/`. A1 was presented; perceived age/naturalness remain for owner feedback. There was no new voice creation, pitch/speed post-processing or production default change.

## Acceptance order

1. The owner retained A as a promising direction but asked for a younger impression. Keep original A unchanged; use feedback on A1 before a default decision. Do not call the result natural or emotionally suitable because the API returned audio. The agent cannot directly listen through the current audio tool.
2. If the owner explicitly selects a default, register/select it through the existing owner-versioned voice settings, retaining its original prompt and cached audition. Read back actual Mac/Pi settings; do not conflate a sample with deployment. Selection alone does not authorize another paid session.
3. Natural English, colloquial Hong Kong Cantonese, consistent timbre, dates/numbers and mixed-language speech remain required. This short Taiwan-Mandarin-only round does not test them. Any further paid comparison needs its own explicit bound.
4. Measure real conversational first useful audio, interruption, captions and tool responses after a sound is accepted. Reuse the existing agent, approvals, microphone ownership and playback. Do not add a second task system or synthesize a paid Live reply a second time.

Production Alice · Bright remains selected pending an explicit default decision. All older budgets remain closed. The rejected LJSpeech-based SoVITS reference is retained only as [technical evidence](../../desk-companion/docs/sovits-evaluation.md); do not re-present it as an Alice candidate.

## Targeted catalog research, not a listening result

The official [Doubao voice catalog](https://docs.volcengine.com/docs/doubao-voice/tone-list-3?lang=zh) explicitly labels 湾湾小何 (`zh_female_wanwanxiaohe_moon_bigtts`) as Chinese with a Taiwan accent and maps it to 小何2.0. The newer 小何2.0 row separately lists multilingual/dialect support including Cantonese; that mapping does not prove identical sound or accent. 撒娇学妹2.0 and 甜美桃子2.0 are other named catalog candidates; their names are not measured naturalness or Taiwan-accent evidence. The inspected catalog contained no playable audio elements, and no Volcengine account, provider call or voice switch was made.

The official [Qwen catalog](https://help.aliyun.com/zh/model-studio/qwen-tts-voice-list) was also checked; no Taiwan-accent claim is inferred from a feminine/soft style label. These references are fallback research, not an instruction to replace the default OpenAI reasoning or to purchase another service.

[Actual audition and cost checks](../../output/qa/2026-11-09-sweet-taiwan-audition/verification.md).
