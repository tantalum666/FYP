# A1 persistent 2D page companion

Updated: 12 October 2026 · Group 2. Current user decision: return to the selected A1 **whole 2D illustration** after rejecting segmented SVG motion, deformed 2.5D and the attempted 3D derivative. Those attempts are historical evidence, not the active interface.

## Current interaction

| Action | Result |
|---|---|
| Drag A1 | Move freely |
| Release near left/right/bottom | Half body, head, then hidden as the pointer approaches the edge |
| Click the small A1 tab | Recall the complete figure |
| Click head/body/feet | Small whole-image acknowledgement, gentle lean or weight shift; eyes remain open |
| Move mouse | Restrained whole-image translation/rotation, with no perspective or local deformation |
| Wheel over A1 / drag corner | Continuous, aspect-preserving resizing |
| Controls → Scale | 1% increments, 50–200%, limited to fit the current viewport |
| Right-click / ellipsis | Display modes, scale, pause, position reset and assistant |
| Double-click / Shift+Enter | Open the existing assistant |

A1 is mounted on authenticated Web pages and independent DeviceApp; login, public share and the old standalone VRM page do not mount this overlay. Review/edit/management panels and the Web **Device settings page** temporarily hide it and stop motion, so privacy, language, timezone and save controls remain reachable at every saved companion position and scale. Leaving settings restores the saved placement, scale and display mode without rewriting those preferences. The independent DeviceApp clock/display still shows A1 and hides it only while its management panels are open. Arrow keys move it; Shift increases the step. The corner handle accepts arrows. Escape cancels a drag/resize or closes controls. Pointer cancellation and viewport changes revert unfinished operations.

Release depths are measured from the pointer to the nearest usable left/right/bottom edge: beyond 72px free/full; 36–72px half; 12–36px head; at most 12px hidden. Half/head are vertical crops of the original full-height illustration. Hidden mode removes the image and leaves a reachable recall tab. Bottom controls retain a reserved inset.

## How the split appearance is removed

The renderer contains **one SVG image, one unchanged PNG and no joint masks or individual limb layers**. All idle/click transforms operate on the complete image. Only uniform resize, rigid rotation and translation are used: no skew, perspective, nonuniform body scale, depth displacement or independent head/arm/leg transforms. The original head/body/hand/foot alignment therefore stays intact throughout a response. The clip at a page edge changes visibility, not anatomy.

Current responses deliberately stay small. They are whole-character feedback, not independently articulated waving, nodding or walking. Larger hand/foot animation would require complete authored pose frames with consistent identity and anchors; these frames have not been produced. The previously generated closed-eye acknowledgement is historical only and is not shipped as a runtime frame.

The active [transparent artwork and exact prompts](../../design/desk-companion/characters/2026-10-12-a1-interface/README.md) remain byte-identical to native output. The `[282,13,460,1492]` SVG viewport trims transparent canvas margins at runtime. Original V4 clothing is the continuity reference; the nine alternative outfits remain unselected.

## Storage and runtime

Versioned localStorage keys `desk.a1.page-companion.v1.web` and `.device` independently store normalized position, docking, display mode, continuous scale, legacy size and motion. Old fixed sizes migrate to scale. Invalid/unavailable storage falls back safely. Wheel/slider writes are debounced; drag/resize writes on release; same-origin/surface tabs synchronize. These keys contain no credentials, calendar text or conversation.

Refs and requestAnimationFrame handle pointer movement. Pausing, reduced-motion, background visibility and blocked panels stop motion. The overlay requires no WebGL and enables no camera/microphone, provider, tool confirmation or hardware output. The existing licensed VRM feature remains separate and unchanged. The rejected A1 3D derivative is retained only as [historical source](../../design/desk-companion/characters/2026-10-12-a1-3d/README.md).

## Verification and limits

[Task QA](../../output/qa/2026-10-12-a1-page-companion/verification.md) records 28 passing frontend tests, TypeScript/production build and actual final-browser checks. Evidence confirms one intact illustration, no joint masks/3D canvas, open eyes, continuous resizing, edge states, persistence, recall, panel protection, reduced-motion and responsive layouts. Superseded prototypes and their checks are labelled separately. Mac browser checks of DeviceApp do not establish Linux/Pi installation, touch, thermal or continuous-running performance.

Later Agent UI acceptance reported A1 intercepting the Web Device page's privacy checkbox on source `c57b052`. The [control-obstruction correction](../../output/qa/2026-10-12-a1-control-obstruction/verification.md) extends the existing temporary panel avoidance to that settings page. Its code-level regression and software checks are separate from the pending real-browser recheck; the earlier browser evidence does not verify this correction.
