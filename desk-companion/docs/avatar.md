# Full-body 3D companion

Updated: 10 October 2026 · Group 2. Runtime verification remains dated 9 October. This is the presentation layer of the existing Desk Companion assistant. The user requested a full-body anime-style female character with a Razer AVA-like desktop presence. The character is replaceable; the bundled development sample is not the final character design.

## Use it

- Assistant → **Open 3D companion**, or `?surface=avatar` on the same app origin.
- Open **Character controls** for local idle / listening / thinking / posture-attention previews and a short synthetic vowel that checks mouth motion. Preview is explicitly labelled and does not call AI, request a microphone, save tasks, or move hardware. **Live** returns to actual workspace state.
- Device → **Calendar & companion** → **Always-on display scene** → **Companion & next event**, then save. This replaces the month panel with the character while keeping time, next events, posture status and touch management.
- `?surface=avatar&clean=1` produces a black background without visible controls or labels. Add `&mirror=1` for a reflection display. Only the character is mirrored; ordinary controls remain readable. The clean page has a keyboard-focusable return link.
- English is the default; the standalone page can switch to Simplified Chinese. Pause animation is independent of ending a voice conversation.
- A self-contained `.vrm` file up to 25 MiB can replace the sample locally. It is parsed in the browser, not uploaded or persisted; reload restores the bundled sample. Models needing external resources or unsupported codecs are rejected. The user must have the relevant model rights. Embedded textures / buffers and VRM 0 / 1 humanoid data are supported; arbitrary glTF scenes are not accepted as avatars.

The standalone page reuses the browser's existing owner / paired session. Without a connection the static sample and local previews remain available, and the status says **Desk not connected**. It does not bypass access to calendar data or assistant tools.

## State and motion

React Three Fiber 9.8.1, Three.js 0.186.1 and pixiv three-vrm 3.5.5 render an actual skinned VRM. The renderer is loaded only when a character surface is used. Calendar and task business state remain outside the frame loop.

| State | Presentation |
|---|---|
| Idle | Small breathing / weight shift, intermittent blink, restrained neutral expression |
| Listening | Head inclination and gentle gaze movement |
| Thinking | Slight upward head angle and a modest arm pose |
| Speaking | Small hand / arm gesture; mouth follows measured assistant output |
| Review | Waiting pose and a screen-review label; the character cannot approve tools |
| Posture attention | A short attention / nod pose for a recent eligible **live** feedback item |
| Disconnected | Clear connection label; stale, paused, snoozed or replay posture data cannot create a live attention state |

Every pose is applied to normalized humanoid bones with bounded interpolation. No animation overwrites the stored calendar, inference result, permissions or output queue. No emotion recognition or treatment outcome is implied by facial expression.

The renderer targets at most 30 presentation updates / second, limits device pixel ratio to 1.5, and avoids postprocessing, physics engines and shadow maps. It stops scheduled frames when hidden / outside the viewport or paused. Reduced-motion mode removes idle movement and blinking while retaining output-linked mouth motion. The mouth closes when playback stops or its last level is older than 300 ms. These are software limits, not measured Raspberry Pi performance.

Loading / parsing / WebGL failure is contained inside the character area with retry and calendar navigation. Each mount owns its model resources; aborted / late loads, replaced files and disposed renderers are cleaned up. Model bytes are bounded even without Content-Length. A failed replacement does not silently become a successful character.

## Voice bridge and its limits

`VoiceAudio` routes the scheduled PCM output through an AnalyserNode before the destination. A PlaybackMeter samples output RMS every 40 ms. It never measures microphone input for mouth motion. Interruption, playback drain and session close explicitly reset the level.

The avatar reads finite, bounded `{level, at}` samples. Same-window events and BroadcastChannel carry these two numbers between tabs on the **same origin and browser profile**; no PCM, transcript, credentials or private task data is sent through that bridge. When BroadcastChannel is unavailable, same-window delivery remains possible. Separate origins, devices and browser profiles are not linked.

This is amplitude-driven mouth opening, not a phoneme / viseme recognizer. Chinese / English syllables do not yet choose distinct anatomically precise shapes. A listening state alone does not animate the mouth. The separate Python voice worker and audio played on a phone / another computer do not yet publish this browser presentation stream. A network presentation bridge is a later integration task, with session binding and expiry required. No endpoint or model permission is widened by adding the character.

A real provider remains separately configured and user-started through Assistant. Local synthetic playback checks the animation path; it is not a natural-language conversation quality test, AEC test or voice-model benchmark.

## Bundled sample and rights

`frontend/public/avatars/pixiv-sample.vrm` is the unchanged official **VRM1_Constraint_Twist_Sample**, version v1.0.1, © 2022 pixiv Inc. It contains 36,470 triangles, 13 mesh primitives and 18 textures; file size 10,776,032 bytes. Counts describe the asset, not observed frame rate or memory use.

- Fixed source commit: `ff42fae4fcee1fcbca2cd262c7f5f8cbddeaf5ab` in [pixiv/three-vrm](https://github.com/pixiv/three-vrm/tree/ff42fae4fcee1fcbca2cd262c7f5f8cbddeaf5ab/packages/three-vrm/examples/models).
- SHA-256: `12c2b97e95e700783a6a550dc0eee2d7880aeedccef9ae67bc4c5a2f0f2631a2`.
- [Provenance and embedded settings](../frontend/public/avatars/source.json) retain the author, copyright and restrictions. The model uses **VRM Public License 1.0 plus embedded permissions**, not the software's MIT licence. [Local licence text](../frontend/public/avatars/VRM-Public-License-1.0.txt) and [official licence](https://vrm.dev/en/licenses/1.0/) are retained.
- Embedded metadata allows everyone to use the avatar, corporate commercial use, redistribution and modification / redistribution; anti-social or hate usage is prohibited. This does not grant Razer character, brand or endorsement rights.
- The runtime does not strip or change the model's metadata. User-selected local models keep their own terms and are not added to Git automatically.

This sample is deliberately a development asset. Custom hair, clothing, materials, identity and authored animation remain separate character-art work, with source assets and rights to be agreed. No Razer / game character asset is copied.

## Original character art research

The user requested a study of current popular anime-style characters before changing the art. The [10 October study](../../research/2026-10-10-avatar-art/popular-character-study.md), [reference board](../../research/2026-10-10-avatar-art/reference-board.html) and [source record](../../research/2026-10-10-avatar-art/source-register.json) distinguish dated community polls from official design sheets / sampled video frames. Existing IP references are not reusable application assets.

The user retained the silver / soft-tech and dark / urban directions and requested hosiery plus mild sensual clothing references. The warm / cheerful option remains historical. The [wardrobe study](../../research/2026-10-10-avatar-art/wardrobe-study.md) defines four written outfit briefs for an adult original character. After the explicit generation request, [A1/B1 full-body PNG concepts](../../research/2026-10-10-avatar-art/character-concepts.md) were generated with native ImageGen and visually checked; raw files, actual prompts and provenance are preserved. A2/B2, turnarounds and expression sheets are not generated. The actual style is more semi-realistic than the cel-shaded brief; no final face, outfit, palette, name or replacement VRM is selected.

The user subsequently chose A1 and requested less realism. [A1 anime V4](../../research/2026-10-10-avatar-art/character-concepts.md) is one small further native edit of V3 after the user again requested less realism. It uses flatter color and harder-edged shadows for clothing, hosiery and boots, while keeping the face close to V3 and retaining the outfit/full-body pose. A1 is the selected working direction; V4 style is pending review. B1 and the original A1 remain historical references.

The user now explicitly retained all five concepts (A1 V1–V4 and B1) and requested Japanese anime appearance and characterization research. The [six-character study](../../research/2026-10-10-avatar-art/japanese-character-study.md), [visual board](../../research/2026-10-10-avatar-art/japanese-character-board.html) and [source record](../../research/2026-10-10-avatar-art/japanese-character-sources.json) are complete. A1 remains the working direction; no version is rejected or finalized by this preservation request. Proposed personality, six expressions and purposeful state transitions are art recommendations, not implemented animation or new tool permissions. The next suggested step is review of a concise A1 brief before further edits / turnarounds. All original PNGs and prompts are unchanged; no V5, runtime model or code was made this phase. Device and voice-bridge validation boundaries remain unchanged.

## Physical display and remaining validation

A transparent-looking character on a normal screen is not a volumetric hologram. This page supplies real-time pixels and optional mirror output. A reflection assembly needs its own screen, geometry, light control and viewing test. A rotating LED fan needs an actual real-time video or SDK input to follow generated frames; ordinary video upload is insufficient. Razer's marketing reference does not establish its internal optical path.

The M2 Mac browser is the current software validation target. Pi 5 8 GB, its GPU driver, Chromium hardware acceleration, thermal load, concurrent camera / audio work, iPhone WebView, remote voice output and a physical optical module remain unmeasured. The school V100 server can serve AI inference but does not automatically render this browser avatar. Start with this sample on the target Pi, record FPS / CPU / GPU / memory / temperature, then reduce texture cost, render scale or asset complexity if necessary.

Validation evidence and the actual tested paths are recorded in [this task's QA](../../output/qa/2026-10-09-3d-avatar/verification.md). This extension does not change the school's proposal or log sheet, and AI-assisted implementation is not automatically credited as the three students' actual contribution.
