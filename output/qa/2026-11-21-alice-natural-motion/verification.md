# Alice movement on the normal home · 21 November 2026

The owner found Alice’s movement stiff. The acceptance flow starts on the connected home screen, taps Alice to greet her, feeds a local speaker-level sample for a short explanation, then lets her settle. A second sequence interrupts the raised hand with a listening presentation. The arm should travel through the gesture and return over several frames. Eyes should acquire attention before the torso turns. Palms, fingers and feet should remain in their intended positions on the phone.

[Play the 6.7-second Simulator comparison](comparison.mp4) · [Measured observations](observations.json) · [Draft PR 135](https://github.com/tantalum666/FYP/pull/135).

## Version and comparison

The original installed native frontend was `c4207e4f`. Its motion sources also matched the `3041b6b5` branch baseline. The final frontend on Mac Web and the same iPhone 17 Pro Simulator (iOS 26.5) was `64485c7f`. The Mac backend stayed on the `4a773f31` code. The final native bundle and the connected Web endpoint returned the same build identity and index digest. The packaged Alice model matched the original byte for byte.

Both video panels show the ordinary native home, served by the same Mac desk, on the same Simulator, at normal speed. The same six-second input enters the existing playback meter. The comparison aligns the input onset, crops to the upper body, and shows the old release on the left. Direct simulator recording captured the screen at approximately 60 Hz. The exported H.264 comparison is 30 fps. Only the cropped, silent comparison is published.

| Observation | Original | Final |
| --- | ---: | ---: |
| Mean observed renders/s in a 12-second greeting and explanation | 20.29 | 30.09 |
| Median observed render interval | 50 ms | 35 ms |
| Wrist path during seconds 1.5–3.5 of the explanation, measured on the same rig at 60 Hz | 0.44 cm | 7.25 cm |

Frame counts come from the home renderer’s advancing counter and wall-clock observations. They describe this Simulator run. The real-rig path uses normalized rotations, the model’s hierarchy, and raw wrist world positions. An earlier candidate held 30.06 renders/s with XcodeBuildMCP recording enabled. The final native film independently counted 30.00 renders/s during the simulated speech input.

## What changed in the frame

- A gaze shift now starts in VRM LookAt. Head and chest rotation follow at different times. During a controlled listening → thinking → idle sequence in the installed app, the eye bone rotated, the mouth stayed closed and the sampled foot world coordinates remained identical.
- The elbow guides the palm forward before it opens. In the first candidate, reviewing the two films revealed excessive lateral reach during the lift and return. The whole-gesture check found up to 0.426 m from the centerline. The final filtered path stayed under 0.38 m on both hands. In the normal 402-point phone viewport, the closest distal finger joint stayed about 18 points inside the right edge during the wave and 10 during the explanation.
- In a separate native readback, a controlled listening input interrupted an actual rendered explanation. The wrist was at 1.164 m, entered listening at 1.147 m and reached 0.893 m as the attentive tilt started. The recording captured 63 successive frames and a maximum neighboring height change of 3.4 cm. The existing mouth output returned to zero on the next observed frame.

The playback signal and listening/thinking inputs were simulated locally. The measurements cover the avatar and its normal renderer. Conversational prosody with a live voice, long-session visual preference, and Pi/physical-phone performance were outside this acceptance.

## Verification and rollout

- The production TypeScript/Vite build succeeded. Ran the affected `alice-motion`, `alice-rig` and `motion-cues` Node test files. All 17 tests passed. The set covers phase ordering, interruption velocity, display jitter, cue timing, actual palm orientation, planted feet, and the full 30 Hz fingertip trajectory. No paid model or separate commerce acceptance ran.
- On the active Web endpoint, Chrome at 1280 × 820 opened Desk Companion, rendered Alice, and responded to a real click on the greeting button. Opening More froze the renderer counter over the observation. A 390 × 844 mobile viewport with reduced motion rendered the static image and zero avatar canvases. The final connected Web run returned no browser warnings, JavaScript errors, HTTP errors or framework overlay. The Browser skill was unavailable in this session, so local Playwright drove Chrome. An earlier fresh, unconnected browser context saw two 401 responses. The final check established its ordinary local desk session first.
- XcodeBuildMCP installed and launched the native app. The Simulator remained on its ordinary connected home after comparison. A diagnostic originally assumed the iOS data-container UUID would persist through bundle reinstalls. The UUID changed. The saved server origin, old WebKit/preference data, authenticated native readback, database contents and installed revision were checked separately.
- The normal Mac rollout used a versioned release, retained older content-addressed assets, and verified the previous database backup and current database integrity, schema, representative row counts, A3 v9, app-grant versions, and protected files. The original `20261119-4a773f31` Mac release and a private copy of the original Simulator bundle remain available for rollback. Pi’s last recorded revision is `85e6aa94`.

## Reading and review

Reviewed the current entry and handoff, motion-related requirements in `product.md`, recent relevant decisions in `decision-log.md`, the active motion sections of the avatar guide and the earlier rig/gesture QA. Inspected the resident home and viewer, interaction state and speaker meter, hand rig, cue/pose functions, their targeted tests, the shipped VRM metadata, and the pinned three-vrm LookAt implementation. Updated the entry, product, avatar guide, decision log, work log and handoff. This was a self-review of the motion diff against `3041b6b5`. The PR remains open for independent review.

The film uses *Alice Chan (Uniform ver.)* by edisonlee55 (now yuna0x0). Group 2 animated the existing model, cropped the recordings, and added the comparison labels. The comparison is available under CC BY-SA 4.0. [Original model](https://github.com/yuna0x0/AliceChan) · [License](https://creativecommons.org/licenses/by-sa/4.0/).
