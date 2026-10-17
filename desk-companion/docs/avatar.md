# A1 3D presentation study

Updated 17 October 2026 · Group 2. The owner chose to remake A1 as **genuine 3D with turning and larger actions**. This supersedes the 12 October intact 2D-only development direction for this new branch. The old illustration and rejected source remain preserved on [PR #4](https://github.com/tantalum666/FYP/pull/4); the old rejected model is not reused as the new runtime asset.

This is a reviewable visual/motion draft, **not owner-approved final A1 art**. Facial likeness, wavy hair silhouette, cloth detail and action polish still need visual review. V4 clothing is the engineering continuity reference; the owner has not selected a default among the nine outfits.

## Use and rendering

Open `?surface=avatar`, or Assistant → More → Explore A1 in 3D. Drag to orbit, scroll to zoom, choose front/side/back, or play Rest, Wave, Turn around, Stretch, Walk in place and Gesture study. Pause freezes animation and closes the mouth. Reduced-motion starts the standalone study paused. `&clean=1` gives black output; `&mirror=1` mirrors the figure. The clean page keeps a keyboard-focusable return link. English/Simplified Chinese are supported.

Authenticated Web and DeviceApp use the same renderer in the [resident layer](page-companion.md). Static local model viewing does not grant access to calendars or tools. A1 gestures cannot approve a job or represent a successful hardware action. The study creates no model-provider connection and requests no microphone, camera or screen access.

Three.js 0.186.1 is lazy-loaded. GLB data is bounded to20MiB; every mount owns its geometry, materials and textures. Late parse results are disposed, requests abort on unmount, and WebGL failure offers intact 2D fallback or retry. Embedded textures use HTML-image decoding under the existing `img-src blob:` policy; `connect-src` stays unchanged. Missing textures are an error rather than a successful blank face.

The loop targets at most30 presentation frames/second and DPR≤1.5, without shadow maps or postprocessing. It stops when paused, hidden, outside the viewport or behind a blocked panel. These are software limits, **not Pi performance results**. Review controls can redraw a paused view without restarting animation.

## Asset, rig and motion

[Blender source and reproduction](../../design/desk-companion/characters/2026-10-17-a1-3d/README.md) / [runtime provenance](../frontend/public/companion/source.json).

The new continuous jacket/knit top replaces stock hidden-surface cutouts; visible leg/ankle topology is retained. Fitted boot surfaces, grouped silver hair, a physical-left open ring, grey-blue iris material bake and eye-shape adjustments form this adaptation. Bone weights interpolate through joints and use at most four normalized influences. Facial UVs remain; the source keeps the original expression set, while the runtime keeps nine useful targets.

Five authored clips use eased whole-body keyframes and 0.22s runtime transitions. Walk uses sagittal two-segment leg IK with planted stance and lifted swing targets, plus ankle orientation compensation. A nine-second Gesture excerpt uses CMU subject 14 trial 26 upper-body capture, zero-based indices 1080–2160 / AMC frame numbers 1081–2161, resampled from 120Hz to 30Hz. Gesture legs retain an authored planted stance; finger/thumb convenience channels are ignored because CMU says they were not captured. This is retargeted public data, not a recording collected from our users. Source/terms and exact frames are in the manifest. Walking remains a pose study; foot contact, cloth collision and secondary hair are not physical simulations.

## Voice bridge

`OutputMeter` analyses only scheduled browser speaker output. It never connects to microphone input. Same-window events and same-origin BroadcastChannel send only `{level, at}`; no PCM, transcripts, credentials or task data. Nonfinite, future and≥300ms-old samples do not open the mouth. Playback drain, interruption and close reset the level; the character also closes its mouth on pause. This is amplitude-driven movement, not phoneme lip-sync. Python-worker/other-device output is not connected by this browser bridge.

## Rights and verification boundary

Base anatomy, face and rig derive from the pinned official pixiv sample, ©2022 pixiv Inc., under [VRM Public License1.0](../frontend/public/avatars/VRM-Public-License-1.0.txt) plus embedded permissions. The [unchanged sample metadata](../frontend/public/avatars/source.json) and original source are retained. New geometry, fit and motion are AI-assisted Group 2 adaptation; they are not wholly original student-authored art, a Razer asset or an endorsement. The adaptation retains the same licence/settings. CMU capture and Three.js software have separate terms.

[This task’s QA](../../output/qa/2026-10-17-assistant-simplify-avatar/verification.md) records source/GLB renders, Khronos validation, actual browser actions, media simulation and responsive checks. Native Blender viewport review complements those checks. Mac checks do not establish Pi/Linux installation, thermal/concurrent performance, iPhone or optical output. Real microphone/screen and paid provider tests were not repeated.
