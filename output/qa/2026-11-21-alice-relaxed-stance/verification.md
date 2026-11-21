# The ordinary standing pose and hands · 21 November 2026

The owner noticed that Alice’s arms remained visibly open on the ordinary home screen and asked for more detail in her fingers and palms. Acceptance starts after the home greeting settles. A passing pose needs a close frontal silhouette, a plausible side view, and hands that stay clear of the skirt. The hand should open and close with distinct finger timing and thumb opposition. [Same-device still](standing.jpg) · [Native standing comparison and hand close-ups](stance-and-hands.mp4) · [Measurements and release receipts](observations.json) · [Per-path surface results](mesh-audit.json).

## Observed at the normal home

The original installed build was `a1f9b76b`. The final daily Web endpoint and iPhone 17 Pro Simulator (iOS 26.5, 402 × 874 points) run `69099a24`. The same ordinary greeting button was used on both builds. Measurements use the actual rendered raw bones at rest for about 2.4 seconds after the greeting ended. The front angle uses the horizontal and vertical components of the shoulder-to-elbow or shoulder-to-wrist vector. The separate side measurement uses the depth component.

| Mean angle, left / right | Original native home | Final native home |
| --- | --- | --- |
| Upper arm from vertical, frontal projection | 22.9° / 26.6° | 5.4° / 7.9° |
| Shoulder to wrist from vertical, frontal projection | 18.4° / 23.7° | 10.1° / 12.4° |
| Upper arm from vertical, side projection | 12.7° / 14.1° | 4.8° / 4.4° |

The breathing and weight-shift cycle produces small variations outside this short video window. Over the separate 18-second quiet rig sample the frontal upper-arm angles ranged from about 5.0–7.8° and 6.2–8.9°. The comparison film first shows the genuine Simulator screen recordings. Its following sections use the same shipped model and runtime drawing path, with a tracking camera to make the motion of the fingers legible. The old and new fingers are shown at the same gesture time and playback speed.

## Posing and fitting

The previous implementation used the wider sleeve-clearance reference as its everyday neutral pose. The new renderer applies the hanging pose before the first draw and initializes the joint filters there. An existing low forward arm landmark guides the raised palm clear of the phone edge. Each lowered elbow and each cuff can engage a small, local shape correction on the original jacket or skirt. The three garment primitives were observed in the actual native viewer. The two sides recover independently as the arms lift. The original asset hash was checked and the sparse cloth data regenerated from the supplied rig sample.

An initial narrow pose exposed hand and sleeve intersections with the garment. The final fit lets the inner sleeve yield to the actual pleated skirt, including its cuff edge. The skirt correction is limited to 8 mm. The inner sleeve and covered side panel can compress more, and the original front, materials and character remain recognizable. The existing hair solver uses the contact weights to adjust its clearance beside lowered sleeves.

At idle the final native middle-joint bends were roughly 17°, 21°, 27° and 31° from index to little finger. Four joint profiles control flexion, spread, the direction of opening or closing, and the small arch of the ulnar knuckles. The original thumb bones are fitted once against the palm. The thumb clears the index before crossing the folded fingers. The first direct opposition candidate could cut through folded fingers. The final path was checked through the intermediate states as well as the endpoints.

## Scope of verification

- The 30 Hz sweep contains 20 gestures, a dedicated 18-second idle window and six interruptions, on each side. All 54 paths and 13,234 frames were skinned using the actual joint matrices, original hair/garment springs, and contact weights on the corrected garment. There were zero tested hand intersections with facial skin, hair, jacket/skirt, the opposite hand or opposite sleeve. Terminal digits stayed clear of their own cuff. Testing all pairs of free digits also produced zero intersecting frames.
- The separate finger sweep covered 81 settled shape levels and 180 frames of rapid changes. No inter-digit crossings were found. The oblique applause still closed and reopened three times. The original cuff covers some intermediate finger skin. The remaining numerical crossings involve sleeve against coat in the right-side wave (up to 2.42 mm for 38 frames) and explanation (up to 1.68 mm for 31 frames). Neither occurred in the ordinary standing pose. These crossing depths describe the open fabric surfaces at the sampled instants.
- The production TypeScript/Vite build and 29 targeted frontend checks passed. The final native build was installed, measured and left on its connected regular home. One short native sample observed about 29.7 rendered frames/s. The connected 1280 × 820 Web home responded to a greeting. Reduced motion displayed the static image with zero avatar canvases. The final Web run logged zero JavaScript page errors.
- The versioned rollout compared the index and protected state, retained the existing backend files, A3 v9, account grants and settings, and verified database integrity and its rollback backup. This was a frontend task with zero paid test calls. The Pi package is staged against `85e6aa94`. This turn’s hardware evidence covers the original Simulator and the local Mac Web endpoint.

The cloth fit can be regenerated after exporting the normal body samples. From `desk-companion/frontend`, run:

```sh
node --experimental-strip-types scripts/avatar-audit/sample.ts /tmp/alice-body
blender -b --python scripts/avatar-audit/fit_uniform.py -- /tmp/alice-body /tmp/uniform-rest.json
node --experimental-strip-types scripts/avatar-audit/springs.ts /tmp/alice-body /tmp/alice-springs --fit-sleeves
blender -b --python scripts/avatar-audit/mesh.py -- /tmp/alice-springs --digits
```

Reviewed the active entry, current product and handoff sections, recent decisions, avatar and previous collision acceptance, the resident renderer, gesture scores, palm geometry, and existing QA/rollout tools. Updated the entry, product, avatar contract, decisions, work log and handoff. Self-reviewed against `d427506f`. [Draft PR 138](https://github.com/tantalum666/FYP/pull/138).

The comparison uses *Alice Chan (Uniform ver.)* by edisonlee55 (now yuna0x0). Group 2 adapted the pose, finger motion and runtime cloth fit and edited the comparison. The media are available under CC BY-SA 4.0. [Original model](https://github.com/yuna0x0/AliceChan) · [License](https://creativecommons.org/licenses/by-sa/4.0/).
