# Group 2 · Alice sweet Taiwan-Mandarin voice brief

9 November 2026. The owner rejected the public-reference GPT-SoVITS samples as more artificial than OpenAI and clarified the desired sound: sweet, soft, cute/youthful feminine Taiwan Mandarin, with warm and natural conversational delivery. This is a sound-selection task. A functioning engine, matched transcript or improved timing alone does not meet it.

## Current default and final A3 candidate

The owner explicitly selected original A / Alice · Taiwan Sweet as the current default on all three surfaces. Mac and Pi settings/cache readback passed; phone browser shares Mac and the running native Simulator app uses Pi8891. Web was opened for personal testing. [Activation evidence](../../output/qa/2026-11-09-original-a-three-surfaces/verification.md).

A2 was heard as adjusted but still not young enough. A3 / Taiwan Light uses a new original adult voice with perceived age18, light delicate vocal weight, a naturally high comfortable register and clear forward resonance. It used the last authorized attempt, returned full same-text output and finalized8seconds. Trimmed WAV5.776583seconds; no pitch or speed post-processing. A3 remains a candidate and does not replace A.

The USD0.05 refinement scope is now exhausted/CLOSED at conservative USD0.0300833, including the earlier USD0.0145 unknown reservation. No paid attempts remain; previous USD0.10/USD0.03 ledgers are also closed. A3 private clip: `~/.config/desk-companion/sweet-taiwan-campus-20261109/sample-light.wav`.

## Initial A/B audition

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

The owner separately approved one session, maximum20seconds and USD0.03. A1 returned the same A voice and complete fixed text, finalized9providerseconds and6.455875seconds of trimmed WAV. Conservative accounting USD0.00825; separate ledger closed. Clip/receipt: `~/.config/desk-companion/sweet-taiwan-younger-20261109/`. **The owner rejected A1 as sounding older than original A.** This delivery-only adjustment failed the desired age impression. There was no new voice creation, pitch/speed post-processing or production default change.

## A2 · new younger base voice

Created Alice · Taiwan Campus as a new original adult18–20voice resource, retaining the Taiwan-Mandarin direction but specifying light vocal weight, clear forward resonance, a naturally medium-high register and bright transparent timbre. Creation guidance uses ordinary campus conversation. The original A resource/audio remains intact. A2 is a new base voice, not an edit of A's immutable resource; quality/similarity is for listening, not inferred from creation metadata.

The owner authorized a new USD0.05 total, maximum3audition attempts /45seconds, to allow sequential feedback without a new question for every small sample. Each attempt is bounded to15seconds. First connection reset before session.started/audio, retaining USD0.0145 and15seconds conservatively. The retry returned complete text and the new requested voice, finalized9seconds at conservative USD0.00825, with6.302542seconds of valid24kHz mono audio. Accounting at the A2 checkpoint was USD0.02275 with one attempt remaining. The later A3 request consumed that final attempt; the scope is now CLOSED as recorded above. The older USD0.10 and USD0.03 ledgers remain closed.

A2 was presented and judged insufficiently young. Audio/voice/closed ledger: `~/.config/desk-companion/sweet-taiwan-campus-20261109/`, clip `sample-campus-retry.wav`. No default change, microphone, backend model, pitch shifting or speed effect occurred.

## Acceptance order

1. Original A is selected as the working default; A1 is rejected and A2 remains insufficiently young. Keep A selected while collecting feedback on A3. Do not call the result natural or emotionally suitable because the API returned audio. The agent cannot directly listen through the current audio tool.
2. Original A has been registered/selected through the existing owner-versioned settings with its original description and cached audition, and both servers were read back. A future replacement still requires explicit selection; it does not authorize another paid session.
3. Natural English, colloquial Hong Kong Cantonese, consistent timbre, dates/numbers and mixed-language speech remain required. These short Taiwan-Mandarin-only rounds do not test them. The current bounded scope is exhausted; further paid comparisons need a new explicit bound.
4. Measure real conversational first useful audio, interruption, captions and tool responses after a sound is accepted. Reuse the existing agent, approvals, microphone ownership and playback. Do not add a second task system or synthesize a paid Live reply a second time.

Production original A / Alice · Taiwan Sweet is selected on Mac/Pi and inherited by the phone clients. All audition budgets are closed. The rejected LJSpeech-based SoVITS reference is retained only as [technical evidence](../../desk-companion/docs/sovits-evaluation.md); do not re-present it as an Alice candidate.

## Targeted catalog research, not a listening result

The official [Doubao voice catalog](https://docs.volcengine.com/docs/doubao-voice/tone-list-3?lang=zh) explicitly labels 湾湾小何 (`zh_female_wanwanxiaohe_moon_bigtts`) as Chinese with a Taiwan accent and maps it to 小何2.0. The newer 小何2.0 row separately lists multilingual/dialect support including Cantonese; that mapping does not prove identical sound or accent. 撒娇学妹2.0 and 甜美桃子2.0 are other named catalog candidates; their names are not measured naturalness or Taiwan-accent evidence. The inspected catalog contained no playable audio elements, and no Volcengine account, provider call or voice switch was made.

The official [Qwen catalog](https://help.aliyun.com/zh/model-studio/qwen-tts-voice-list) was also checked; no Taiwan-accent claim is inferred from a feminine/soft style label. These references are fallback research, not an instruction to replace the default OpenAI reasoning or to purchase another service.

[Actual audition and cost checks](../../output/qa/2026-11-09-sweet-taiwan-audition/verification.md).
