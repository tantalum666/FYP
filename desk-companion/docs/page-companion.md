# A1 resident page companion

Updated 17 October 2026 · Group 2. The latest owner choice is genuine 3D with turning and larger actions. This branch provides a **3D visual draft** and retains the intact open-eyed illustration as a selectable fallback. Selecting the route does not approve this model’s final likeness or a default outfit. Earlier rejected segmented/depth/3D attempts remain historical on [PR #4](https://github.com/tantalum666/FYP/pull/4).

Authenticated Web and DeviceApp mount the same layer. Login/public share/standalone study do not mount a second resident canvas. When the device preference already shows the full companion scene, the floating layer is omitted so only one canvas exists. Editing/review/management panels hide the floating layer and stop the active character render loop, including the full device scene, protecting the active controls.

| Input | Result |
|---|---|
| Drag | Move freely; release near left/right/bottom to dock |
| Edge distance36–72px /12–36px /≤12px | Half body /head /hidden; hidden leaves a reachable A1 recall tab |
| Wheel, corner drag, or scale slider | Continuous uniform resize,50–200%, bounded to viewport |
| Click | Short real-rig wave or walking response; the2D fallback uses only a restrained whole-image response |
| Right-click/ellipsis | Display modes, actions, pause, reset,2D/3D choice and study link |
| Double-click/Shift+Enter | Open the existing assistant |
| Arrows /Escape | Move (Shift increases step) /cancel unfinished drag or resize |

The3D renderer uses a real GLB mesh, skeleton, morphs and clips. No body-part image masks or depth-warped PNG is used. Half/head states clip the rendered viewport rather than cut anatomy. The intact fallback is one unchanged PNG in its original SVG crop, uniformly scaled; no separate head/arm/leg transform is applied.

Versioned localStorage position/scale/dock/motion keys remain `desk.a1.page-companion.v1.web` and `.device`; the new render choice is `desk.a1.3d.v2.<surface>`. Only presentation preferences are stored, never credentials, calendars or conversations. Legacy sizes migrate; invalid/unavailable storage falls back. Existing scale/docking synchronizes between same-origin tabs. The 2D/3D choice persists separately per surface; already-open tabs pick it up on reload, without live choice synchronization.

The default in this review branch is3D; WebGL/load failure shows the intact illustration and an explanatory control. Original primary checkout/runtime files are preserved. The [standalone study](avatar.md) has orbit, zoom, source/licence and local large-action previews. The owner’s V4 attire is a continuity reference; the nine saved outfits remain unselected.

[QA](../../output/qa/2026-10-17-assistant-simplify-avatar/verification.md) separates actual browser, synthetic-media and asset checks from unmeasured Pi/Linux/physical results. Visible motion is not evidence of AI reasoning, tool success, health benefit or real hardware feedback.
