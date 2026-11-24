# Alice’s facial expression and uniform fit

The ordinary Mac Web home and the installed iPhone 17 Pro Simulator run source `c8aa1982` over the previous home release `69099a24`. Group 2 added seven facial expressions, improved the readability of the nose and lips in the normal home framing, and added a small amount of fullness at the front of the uniform. [Simulator comparison](simulator-home.jpg) · [matched portrait and profile](face-and-uniform.jpg) · [expression sheet](expressions.jpg) · [five-second expression film](expressions.mp4) · [measurements](observations.json).

## What changed

The same official OpenAI Session reply now also supports relief, bashfulness and an apology by Alice. The local performance layer supplies attentive listening, a thoughtful expression, a playful wink and pride. It separates brow/eye timing from mouth timing. In relief, for example, the lids lower and the lips round during the exhale. The mouth then eases into a smile as the eyes reopen. Speaking gives the existing audio viseme priority. An explicit neutral answer clears the previous response.

The original 57 facial morphs retain their indices. Three one-sided variants derive from the original artist's displacements with a continuous blend across the face. The nose uses a sparse adjustment to the original skin geometry and its normals. Local color follows the nose and the existing lip atlas. The artist's closed-mouth shape now settles the lips between turns. The original VRM digest is `370b2312e9f97834db868751e43e9dd33b9112e5d151d592757c3f47315e195e`.

| Matched rest pose | Observed smooth displacement |
| --- | ---: |
| Nose-tip vertex | 2.42 mm |
| Front of the two uniform top materials | 11.32 mm and 11.28 mm |
| Bow vertex with greatest displacement | 2.03 mm |

The distances come from corresponding vertices after skinning in the two regular renderers. The chest edit tapers within 75 mm of the midline and between heights 1.068 and 1.284 m in model space. Checked normal-home captures show more visible detail even at the usual 402 × 874 pt viewport. For an image-space check, local facial contrast is the neighboring cheek median minus the 15th percentile in a small central feature patch, using 8-bit sRGB luminance. It rose from 4.9 to 22.9 at the nose and from 13.4 to 60.9 at the mouth for these paired stills. This measures these frames. Lighting, camera and display size influence the result.

## Ordinary home and conversation

- The Simulator opened the regular native home and verified the installed index digest against the release record. The same home sent “原来昨天以为弄丢的照片都有备份，虚惊一场！陪我松口气吧。” The live GPT-6.2 Sol reply was “太好了，照片都有备份。来，一起慢慢呼口气……这下可以放下心了。” The visible home moved from thinking to `relax` with `relieved`. The stored answer and its delivery matched the same operation.
- One new OpenAI usage row recorded 15,256 input and 44 output tokens, with zero cached input. The local usage estimate rose by US$0.084392. The existing US$0.08 unresolved reservation stayed the same. Provider-billed currency for this turn was not independently available. The previously closed trials stayed closed.
- An isolated official-Session protocol replay exercised the same installed ordinary composer. Bashfulness produced `hairTuck`, apology produced `nod`, and relief produced `relax`. Each displayed the replayed answer. The app was restored to the connected regular Mac desk afterward. The film and expression sheet use the resident renderer at a fixed camera for comparison.
- The released Web home responded to its greeting control. With the browser's reduced-motion preference, the home displayed the updated 1280 × 720 poster. The full figure fits within the frame, including the top of the hair and the shoes. Both browser runs had zero captured page or shader errors. The regular mobile home has separate native before/after captures.

## Garment, facial skin and local checks

The first full-width chest adjustment made returning sleeves intersect the outer panel during gratitude and comfort. Group 2 narrowed the lateral taper before release. The matched 30 Hz sweep reused the standing release's joint and spring trajectories. It intersected the new surfaces for four classes of contact on both sides across 54 paths and 13,234 frames. No hand or sleeve crossed the facial skin, and neither hand crossed the outfit. The two earlier fabric contacts were identical by path, duration and maximum depth. The left sleeve touches the garment during the right-hand wave (38 frames, 2.42 mm) and explanation (31 frames, 1.68 mm). Their locations are outside the new chest contour.

The runtime renderer also supplied 350 samples of the actual expression-deformed face and the moving hand during bashful hair tuck and hand-to-heart, thought, laughter and apology. No sampled hand crossed that facial skin. The closest sampled hand vertex was 29.69 mm away during laughter. The tie had 214 sampled triangle centroids with a garment layer behind the same projected area. None switched from clearly in front to clearly behind, or vice versa, at a 0.15 mm depth threshold. These are sampled geometric checks on this outfit.

The production TypeScript/Vite build, asset provenance checks, focused front-end regressions and three ordinary Session protocol cases passed. Tests covered one-sided shapes on shared geometries, original viseme indices, audio release of the closed lips, delivery replacement, relief timing and binding the sparse data to the licensed asset. A first browser render exposed a shader type mismatch between MToon 3.5.5 and Three r186 when enabling face vertex colors. The shipped face shader consumes RGB explicitly. The corrected face was inspected in WebGL and native WebKit.

## Release and scope

The Mac activation verified 524 installed file hashes, a private rollback copy, SQLite schema 3 and integrity, protected account configuration, A3 v9 and the same app grants. Ordinary text and delegation use GPT-6.2 Sol. Voice uses GPT-Live-1.1. The prepared Pi package was verified against its recorded `85e6aa94` base. The configured, pinned owner route returned an SSH forwarding failure. The Pi package is retained. Physical iPhone appearance and Pi kiosk rendering still need on-device observation. [Draft PR 139](https://github.com/tantalum666/FYP/pull/139) stacks on [PR 138](https://github.com/tantalum666/FYP/pull/138).

The work used the current avatar sections of `AGENTS.md`, `product.md`, `handoff.md`, the latest motion decisions, the avatar and ordinary-Session contracts, the source/license manifests, the prior release evidence and the relevant renderer, rig, presentation and Session source. The official Session create reference and installed SDK schema support a structured answer format. This change extends that existing answer. The product, avatar, Session and handoff documents, decision log and work log record the result. [Official reference](https://developers.openai.com/api/reference/resources/beta/subresources/agents/subresources/sessions/methods/create).

The reproducible surface bake runs from `desk-companion/frontend` with `blender -b --python-exit-code 1 --python scripts/avatar-audit/fit_features.py -- src/companion/alice-surface.json`. For the reduced-motion still, use the resident renderer at neutral 1.45 s, a 1280 × 720 viewport, and a front orthographic camera centered at (0, 0.831, 0.01) with half-height 0.921. The local mesh audit accepts `--appearance-contacts` with the existing sampled motion directory.

Model and rendered media use *Alice Chan (Uniform ver.)* by edisonlee55 / yuna0x0. Group 2 adapted the face, pose and uniform and edited the comparisons. The adaptations and rendered media are available under CC BY-SA 4.0. [Original model](https://github.com/yuna0x0/AliceChan) · [License](https://creativecommons.org/licenses/by-sa/4.0/).
