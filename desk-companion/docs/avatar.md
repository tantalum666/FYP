# A1 3D presentation study

## Current Alice motion — 13 November 2026

Alice now uses client-authored, bounded upper-body motion on the existing normalized VRM rig. One brief wave follows initial loading; clicking/tapping her home silhouette repeats it. Idle includes breathing, relaxed arm variation and occasional glances. Listening adds a gentle head tilt/nod, thinking a small upward turn, and speaking restrained hand/head gestures. Motions return smoothly to the model's relaxed pose. No walking/root/leg translation or camera reframing is introduced.

`alice-motion.ts` owns deterministic pose curves and blink timing. `interaction.ts` carries only local presentation state from the existing AssistantPanel, with per-source cleanup and no transcript/audio/business data. VrmViewer applies quaternion interpolation from saved rest poses inside its existing capped render loop. Speaker amplitude still comes from OutputMeter; animation does not acquire a microphone or start a provider session. User hello is a native accessible button over the silhouette, below calendar/header/chat controls.

The initial wave was rejected for a reversed hand and rigidity. The correction explicitly checks both palms against the shipped VRM's real bone hierarchy: palm faces the camera and thumb points toward the face. Both normalized wrists need the same forward X roll; mirroring this value reverses the right hand. `hand-pose.ts` shares the relaxed-arm calibration with the renderer/test and derives each finger's flexion plane from its actual joints. Missing/degenerate joints are skipped. Small finger curls soften the hand without introducing another animation loop.

The4.8second greeting staggers elbow lift, wrist opening and slow side-to-side motion, then settles with quintic easing. The forearm lifts forward before presenting the palm beside the face, avoiding the phone-edge sweep. Speaking arms move outward rather than through the torso. Reduced motion retains the existing static fallback, navigation/modal suspension stops rendering, and offscreen/hidden/disposed renderers retain their lifecycle. The original Alice asset/hash and licence are unchanged. [Correction QA](../../output/qa/2026-11-13-alice-motion-repair/verification.md) supersedes the rejected first-wave visual acceptance. The old six-action asset library stays historical.

Mac's normal web and native Simulator show the correction. Pi received the same compatible frontend with its backend/A3 preserved, but went unreachable during local character loading; Pi physical animation and sustained performance remain unverified. Do not treat a Mac-rendered device page as Pi GPU evidence.

<!-- FYP-CONTEXT-20261027 -->
> 2026-10-27 核对：**现行规范／入口**。已按本轮保存状态核对；最新软件、GitHub main 和 Pi 部署分开，Pi 暂停、旧 API 预算关闭。 [新聊天入口](../../START_HERE_NEXT_CHAT.md)。
<!-- /FYP-CONTEXT-20261027 -->

Updated 22 October 2026 · Group 2. **The owner selected AliceChan for initial use.** The [original and runtime source](../../design/desk-companion/characters/2026-10-22-alice/README.md) retain the creator’s complete character. The original release v1.0.4 contains a VRM0 asset named/versioned1.0.2; repository marketing metadata is not used to call it VRM1. No face/hair/outfit reconstruction is active.

## Current complete-model viewer

Open `?surface=models&lang=zh` (English by default). `a1`, `head` and ordinary `avatar` route here. Alice is the default, with source/author/CC BY-SA4.0 links visible. Shino/Victoria remain in collapsed options. Same-origin resident/Device tabs pick up an explicitly applied choice. The old v1 preference is preserved, and the new v2 default is Alice/original/100%.

Local self-contained VRM0/1 under64MiB can still be opened and remembered in this browser’s IndexedDB. The new preview preference distinguishes a local preview from the selected built-in character; an earlier cached model remains available through “Open saved local preview” without overriding Alice on first update. Choosing a built-in preserves cached bytes; removing the browser copy deletes only that record. Newly opened local previews restore after reload and are never uploaded or applied to resident pages. Parsing/header/resource checks are not a complete asset certificate; later renderer failures show retry.

Front/30°/side/back, portrait/full, orbit/zoom, source-native expressions and simulated mouth remain. Loading a new generation now applies current controls directly after the model becomes ready; a framing choice made before load is retained. Button/actual framing no longer depend on React loading-state timing. Disposed renderers also release their WebGL context. Optional A1 original-art comparison remains a historical reference.

The viewer mounts before WorkspaceProvider and does not poll calendar or acquire media. `@pixiv/three-vrm`3.5.5 retains MToon/morphs/spring bones. Current QA (local historical material: `output/qa/2026-10-22-alice-software/verification.md`; not included in this checkpoint) includes0 runtime glTF errors,17 legacy warnings, original/binary preservation and real browser checks. Earlier Reveria permission/6-source-error issues remain in its separate candidate record; no Reveria bytes are shipped.

## HISTORICAL: rejected native A1 v1

The complete J/Reira [editable source, export and provenance](../../design/desk-companion/characters/2026-10-19-a1-vroid-refinement/README.md) remain at `?surface=a1-history`, explicitly marked rejected. Its dated QA (local historical material: `output/qa/2026-10-19-a1-vroid-native-refinement/verification.md`; not included in this checkpoint) records engineering checks and art differences; the owner subsequently rejected it. Modern J A-Z conditions and Reira attribution remain in force for those preserved files. No renewed sculpting, hair editing or wardrobe work is active. Older v3/Galaxy/custom head also stay historical; custom head is only `head-history`.

## Use and rendering

Assistant → More → Character & appearance opens the complete-model viewer. For independent black/mirrored output use`?surface=avatar&clean=1&mirror=1`; it loads the chosen complete model through the shared resident renderer. Pause freezes physics and closes output-driven mouth; reduced-motion starts paused. The old six-action library is not used by the current complete models. Click response is a brief nod, with small attention/breathing and native blink.

Authenticated Web and DeviceApp use the same renderer in the [resident layer](page-companion.md). Static local model viewing does not grant access to calendars or tools. A1 gestures cannot approve a job or represent a successful hardware action. The study creates no model-provider connection and requests no microphone, camera or screen access.

Three.js0.186.1 and three-vrm are lazy-loaded, with VRM data bounded to64MiB. Every mount owns/disposes its resources; late results are disposed and fetch aborts on unmount. Resident failure retains intact2D fallback; the viewer can retry. Embedded textures decode through HTML images under existing`img-src blob:`; connect-src is unchanged. Standalone clean output also bypasses WorkspaceProvider, removing its old unauthenticated calendar polling.

The loop targets at most30 presentation frames/second and DPR≤1.5, without shadow maps or postprocessing. It stops when paused, hidden, outside the viewport or behind a blocked panel. These are software limits, **not Pi performance results**. Review controls can redraw a paused view without restarting animation.

## Historical v2 asset, rig and motion

[Blender source and reproduction](../../design/desk-companion/characters/2026-10-17-a1-3d/README.md) / [runtime provenance](../frontend/public/companion/source.json).

The new continuous jacket/knit top replaces stock hidden-surface cutouts; visible leg/ankle topology is retained. Fitted boot surfaces, grouped silver hair, a physical-left open ring, grey-blue iris material bake and eye-shape adjustments form this adaptation. Bone weights interpolate through joints and use at most four normalized influences. Facial UVs remain; the source keeps the original expression set, while the runtime keeps nine useful targets.

Five authored clips use eased whole-body keyframes and 0.22s runtime transitions. Walk uses sagittal two-segment leg IK with planted stance and lifted swing targets, plus ankle orientation compensation. A nine-second Gesture excerpt uses CMU subject 14 trial 26 upper-body capture, zero-based indices 1080–2160 / AMC frame numbers 1081–2161, resampled from 120Hz to 30Hz. Gesture legs retain an authored planted stance; finger/thumb convenience channels are ignored because CMU says they were not captured. This is retargeted public data, not a recording collected from our users. Source/terms and exact frames are in the manifest. Walking remains a pose study; foot contact, cloth collision and secondary hair are not physical simulations.

## Voice bridge

`OutputMeter` analyses only scheduled browser speaker output. It never connects to microphone input. Same-window events and same-origin BroadcastChannel send only `{level, at}`; no PCM, transcripts, credentials or task data. Nonfinite, future and≥300ms-old samples do not open the mouth. Playback drain, interruption and close reset the level; the character also closes its mouth on pause. This is amplitude-driven movement, not phoneme lip-sync. Python-worker/other-device output is not connected by this browser bridge.

## Rights and verification boundary

The archived v1 rights are recorded above and in the native source manifest. The following is the historical v2 study, with its own base/terms; it does not define modern J or Reira rights.

Base anatomy, face and rig derive from the pinned official pixiv sample, ©2022 pixiv Inc., under [VRM Public License1.0](../frontend/public/avatars/VRM-Public-License-1.0.txt) plus embedded permissions. The [unchanged sample metadata](../frontend/public/avatars/source.json) and original source are retained. New geometry, fit and motion are AI-assisted Group 2 adaptation; they are not wholly original student-authored art, a Razer asset or an endorsement. The adaptation retains the same licence/settings. CMU capture and Three.js software have separate terms.

This task’s QA (local historical material: `output/qa/2026-10-17-assistant-simplify-avatar/verification.md`; not included in this checkpoint) records source/GLB renders, Khronos validation, actual browser actions, media simulation and responsive checks. Native Blender viewport review complements those checks. Mac checks do not establish Pi/Linux installation, thermal/concurrent performance, iPhone or optical output. Real microphone/screen and paid provider tests were not repeated.
