# Alice’s hands and GPT-Live-1.1 · 21 November 2026

The owner identified reversed hands and clipping during gratitude and laughter. The acceptance includes the lift, held pose, return and mid-gesture changes. For voice, the acceptance checks the requested model in both the application and provider receipt, the existing custom voice, audio and terminal usage. [Native before/after film](native-hand-comparison.mp4) · [All twenty gestures, front and side](all-actions.jpg) · [Per-path measurements](motion-audit.json) · [Release and voice receipts](receipts.json).

## What the old checks missed

A fingertip could remain inside the phone frame while the hand turned sharply at the cuff. On the original rig, the maximum hand rotation relative to its relaxed wrist was 114.0° for gratitude and 128.9° for laughter. Gratitude also put one hand through the other sleeve. The hair-tucking path could cross the facial skin. The prior QA did not cover these mesh pairs.

The new scores give elbow flexion, forearm roll, wrist bend and sideways wrist movement separate values. The standard wave and explanation retain their palm orientation while longitudinal rotation moves to the forearm. A continuous rotation vector avoids unwinding between equivalent Euler triples. The free arm hangs at the side during gratitude and laughter. The fingers curl beside the mouth and the palms approach obliquely during applause. The existing hair and coat spring rig uses the outer sleeve clearance. The source VRM remains byte-identical.

## Geometry and visual acceptance

| Measurement | Original | Shipped |
| --- | ---: | ---: |
| Maximum local wrist rotation, gratitude | 114.0° | 41.1° |
| Maximum local wrist rotation, laughter | 128.9° | 16.4° |
| Hand-to-face triangle intersections in 280 additional expressive-face samples | — | 0 |
| Foot movement caused by the new motion, all paths | — | 0 m |

The final run sampled all 20 gestures and six interruption pairs, on both sides, at 30 Hz. The 52 paths contained 12,154 frames. The offline sampler uses the resident joint and finger filters, the model’s actual inverse bind matrices, and its 131 simulated spring joints. Blender’s triangle-BVH checks cover hands against facial skin, hair, the coat/skirt/tie, opposite hands and opposite sleeves, and distal fingers against their own cuffs. The primary hand check found zero crossing frames on these paths. The extra WebGL check included actual facial expression targets. The nearest sampled hand-to-face surface during laughter was about 29 mm. These finite checks use Alice’s shipped rig and the tested transition sequences.

Two kinds of contact remain visible in the numerical results. The long cuff intentionally covers skin near the palm, including parts of the intermediate finger segments. The terminal finger geometry had zero crossings through its own cuff. Sleeve/coat surfaces crossed in some poses, reaching a local estimate of 4.24 mm during clapping. One mirrored sleeve-adjustment-to-victory transition had a sleeve/hair crossing over two frames, with a local estimate of 6.82 mm. These are surface observations on thin, open garment and hair meshes. The receipt records their duration and locations separately from hand penetration. No hand, face or opposite-sleeve crossing remained in the two owner-reported gestures.

The contact sheets used the ordinary renderer, four sampled instants per gesture and front, 45° and profile cameras. The 12-second split film uses actual home recordings from the same iPhone 17 Pro Simulator at normal speed. The original clips came from the previous real text acceptance. The corrected recording drove the ordinary composer with those same replies through the isolated local provider fixture. No paid emotional chat was repeated. The Simulator was restored to its connected daily home afterward.

To reproduce the geometry run from `desk-companion/frontend`, create separate directories for the pose and spring samples:

```sh
node --experimental-strip-types scripts/avatar-audit/sample.ts /tmp/alice-body
node --experimental-strip-types scripts/avatar-audit/springs.ts /tmp/alice-body /tmp/alice-springs --fit-sleeves
blender -b -t 1 --python scripts/avatar-audit/mesh.py -- /tmp/alice-springs
```

The sampler output is operator evidence and can occupy hundreds of MB. Blender is used for this offline audit only.

## Voice and standby

The official model entry confirms `gpt-live-1.1`. The WebSocket primary connection still sends `session.start` first and receives `session.started`. The implementation had previously hard-coded the old ID inside that payload. The configured model now reaches the request, and a different returned ID fails explicitly. Operators can still explicitly pin version 1. Existing tools, approval ownership, A3 settings, and GPT‑6.2 Sol delegation remain intact. [Official model](https://developers.openai.com/api/docs/models/gpt-live-1.1) · [WebSocket connection](https://developers.openai.com/api/docs/guides/voice-websockets?api=live) · [Live API reference](https://developers.openai.com/api/reference/typescript/resources/live).

A speech wake policy and an idle timeout of 5–60 seconds apply to WebRTC. In that mode the microphone track stays active, speech resumes inference, and the same session keeps its history. The timeout covers transcript inactivity. The documented active and standby rates are US$0.05 and US$0.02 per minute respectively. Between daily conversations Alice’s existing local wake detector can listen for her name without opening a cloud voice session. The application continues to use the primary WebSocket during a call. WebRTC standby would be relevant for short pauses in a future explicitly opened WebRTC call. [Idle-session guide](https://developers.openai.com/api/docs/guides/live-conversations#managing-idle-sessions) · [Duration pricing](https://developers.openai.com/api/docs/pricing#live-session-duration).

The existing FYP key returned the exact model through the catalog. One acceptance under the existing daily authorization used synthesized Mandarin through the ordinary desk voice ticket. The input was “你好，请只说收到。” The provider transcript rendered “你好,请直说‘收到’。” Alice replied “收到。” The acknowledged model was `gpt-live-1.1`, the provider confirmed the configured custom A3 voice (settings v9), and the client received 10 packets / 48,000 bytes of 24 kHz PCM. The graceful close returned five billable seconds. This WebSocket receipt contained the total duration. The local ledger moved by US$0.011026 during the acceptance window. That is a local cost-control measurement. No platform invoice was imported. No physical microphone, external task or separate classifier was used. This short test does not establish Cantonese/English accent quality or long-call performance.

## Versions, release and review

The source baseline was `08a8b49b`. The real voice acceptance used backend `8e4fd800`. Its voice source is identical in the final release `a1f9b76b`. The final regular Mac endpoint and native bundle agree on revision and index digest. The Mac verified its database backup, original protected files, A3 v9 and account-grant versions. The only intended persistent setting change was the Live model pin. Prior releases, configuration backup and the original native bundle are available for rollback. Pi’s pinned relay could not reach the device and its known LAN name did not resolve. A code-only delta from `85e6aa94` was reconstructed and verified against all 505 files, 118 changed and 387 reused. The package includes no private runtime data.

The production frontend built and the 24 targeted motion/rig/delivery checks passed. The selected Live/default tests passed (15), as did the separate voice-model/delegation and operator configuration checks. A stale assertion previously expected two text-only shopping/flight functions in Live. The test now checks the actual voice exposure boundary. The application tool policy was preserved. Local testing supplied the evidence. This was a self-review. [Draft PR 137](https://github.com/tantalum666/FYP/pull/137).

Read the current entry, product motion requirements, handoff, the latest hand/voice decisions, the avatar and wake contracts, the previous expressive acceptance, the official model/transport/standby references, and the actual renderer, rig, provider adapter and operator configuration. Updated the entry, product, avatar and voice guides, README, work log, decision log and handoff.

The film and contact sheet use *Alice Chan (Uniform ver.)* by edisonlee55, now yuna0x0. Group 2 adapted the animation and edited the recordings. These media are licensed under CC BY-SA 4.0. [Original model](https://github.com/yuna0x0/AliceChan) · [License](https://creativecommons.org/licenses/by-sa/4.0/).
