# Group 2 — Alice natural motion

**Historical first implementation.** The owner subsequently rejected its reversed palm and stiffness. Its test results do not establish acceptable hand anatomy. Current correction, native build and runtime activation are recorded in [the repair QA](../2026-11-13-alice-motion-repair/verification.md). Retain the old clip as rejected evidence, not a current preview.

13 November2026. Owner requested actions because Alice stood still. Source base6153b41d; isolated branch `codex/alice-natural-motion-20261113`. This change is frontend presentation only. No paid generation, microphone/camera capture, new dependency, CI, production data migration, native build or Pi deployment.

## What changed

- `alice-motion.ts`: deterministic breathing/relaxed upper-body variation, uneven blink intervals, occasional idle glances, bounded initial/tap wave, listening tilt/nod, thinking turn and speaking hand/head gestures. Gesture envelope returns to the current idle pose; root/hips/legs/feet are not animated.
- `interaction.ts`: one local presentation-state channel for the existing AssistantPanel, keyed by source and cleaned on suspension/unmount. Contains no text, PCM, credentials, business permissions or result authority. New renderers immediately receive the current state; disposing one source cannot erase another active source.
- VrmViewer saves each normalized bone's relaxed quaternion, applies small interpolated offsets and retains its existing spring bones,30fps cap, DPR1.5cap, hidden/offscreen/pause/disposal behavior. Actual speaker amplitude still owns mouth movement and expires as before.
- AliceScene adds an invisible native button on her silhouette for click/tap/keyboard hello, below header/calendar/chat controls. It is disabled when blocked and omitted for static/reduced-motion output. No permanent extra toolbar, model replacement, camera reframing or avatar shrinking.
- Existing voice configuration, A3 profile, backend tools, subtitles and user data are unchanged. Shared Web/phone/device render code uses this layer; source sharing does not establish deployment to a native app or Pi.

## Defects caught during implementation

The previous renderer accepted conversation state but never used it, and kept both arms fixed. The first gesture test exposed a floating-point boundary and a slight pose discontinuity at the end of a wave; zero-weight gestures and rest blending now agree. Real screenshots then revealed Alice's arm-axis direction: the initial speaking pose bent a hand through the torso. Corrected the direction using actual rig inspection. An outward wave then clipped the right edge on phone; the final curve rolls the forearm forward during the lift and uses a compact bend beside the face. Actual 393/320phone screenshots now retain the hand and unchanged Alice scale. Voice-not-configured maps to idle, allowing a greeting without any provider connection.

## Verification

Frontend377tests pass; TypeScript and production build pass. No backend code changed, so the previous backend suite was not repeated. Existing build warnings concern the large shared3D/runtime chunks. No CI.

Actual production-build browser flows, using installed Chrome through Playwright1.62:

| Check | Result |
|---|---|
| Identity and render | Correct Desk Companion URL/title; rendered Alice; no blank page or framework overlay |
| Console/network | Zero page exceptions and zero failed responses in the final acceptance run |
| Greeting/tap | Initial wave -> idle; clicking/tapping Alice repeats the wave; keyboard Enter also works |
| Conversation bridge | Real text-send UI enters thinking during the3second local mock transport and returns to idle after response |
| Voice presentation | Synthetic workspace listening/speaking state and synthetic speaker-level samples drive poses/mouth; after samples stop the mouth closes |
| Pause | Opening navigation freezes the frame counter and disables the silhouette target |
| Reduced motion | Runtime preference change disposes the animated canvas, shows static fallback, then restores exactly one loaded canvas |
| Layout | Desktop1080×900, phone393×852 and320×740; no horizontal overflow; calendar/header/composer remain usable |
| Render pacing | 23rendered frames in a1050ms sample, under the30fps cap; this is a short Mac/Chrome observation, not a Pi benchmark |
| Asset preservation | Original Alice runtime SHA256370b2312…15e195e unchanged; source/licence retained |

Manual visual review covered greeting, rising-hand poses, idle, thinking, listening, speaking, both phone widths, paused navigation and reduced motion. A temporary rig probe read actual hand/finger positions and was kept outside shipping source. No live audio, phoneme-sync or physical-device performance claim.

Browser plugin/skill is absent; the frontend-testing skill's regular Playwright fallback was used with already-installed Chrome. React review covered stable renderer ownership, effect cleanup, no per-frame React state, accessible native interaction and no new polling. No browser/library install.

## Evidence and availability

[Machine summary](validation-summary.json), [actual reading/scope record](reading-record.md). Private artifacts and harnesses: `~/.config/desk-companion/alice-motion-20261113/`; includes real screenshots, acceptance.json, reach.json and Alice-motion-preview.webm. The movie is an actual browser recording, with no generated visual replacement.

Local preview `http://127.0.0.1:8832/` and `?surface=phone` use an isolated test store. Schedulers and real providers are off; text response and voice state are test fixtures. It is an animation preview, not a rollout of the user's real mailbox/voice/data environment. The temporary rig-probe Vite server is stopped at closeout; only the requested reviewable preview is retained.

Updated avatar/Alice home/page companion/provenance documentation, root product, decisions, work log and current handoff. Remote source publication is recorded after readback; source push, merge and runtime activation remain separate states.


Publication: [PR123](https://github.com/tantalum666/FYP/pull/123) is open/unmerged; reviewed source659403c2matched the remote head. [Receipt](publication.json). The following receipt update changes documentation only. The isolated animation preview remains available; normal runtime/native/Pi activation remains separate.
