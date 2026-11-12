# Group 2 — Alice hand correction and cross-surface delivery

13 November2026, HKT. The owner reported the hand was reversed, movement was stiff and only the phone had been shown. Source correction c65ac229 is on the existing PR123 branch based on main6153b41d. The prior first-wave clip is rejected historical evidence.

## Cause and implementation

The previous held left-hand pose had camera-facing palm-normal Z about-0.803: it showed the back of the hand and the thumb pointed outward. The normalized wrist roll was incorrect. A positive1.35radian X roll is needed on **both** normalized wrists for this model; mirroring it on the right hand reproduced the reverse-palm defect during calibration.

The actual rendered correction measured left palm Z0.998 and right Z0.997 with inward-facing thumbs. Two new tests reconstruct the shipped VRM0 bone hierarchy through the actual VRMHumanoid normalization, reuse the renderer's relaxed-arm calibration, and check both hands at four held-wave instants. They assert palm Z>0.8, inward thumb and unchanged feet. These tests would reject the old pose; they do not substitute for visual judgement of naturalness.

The greeting lasts4.8seconds, with a slower0.85Hz wrist wave, staggered elbow/wrist lift and return, quintic easing, a slight shoulder/head response and small rig-derived finger curls. Hands open gradually rather than staying flat. Motion stays within the existing capped renderer and original Alice model/framing; no root/leg movement, new assets, dependency, provider call or permission change.

## Validation

- Main-based frontend:379tests, TypeScript and production build pass.
- Runtime-compatible frontend:358tests, TypeScript and build pass. The initial candidate harness lacked its original assistant-stream fixture; restoring that exact520ab563 fixture resolved the harness failure. No production protocol was changed.
- Model binary SHA256 remains370b2312e9f97834db868751e43e9dd33b9112e5d151d592757c3f47315e195e. Both hands were inspected in a private real-renderer probe. No third-party motion pack was included.
- Normal Mac browser1440×900: actual greeting click produces wave,55observed renderer frames lead to a palm-forward screenshot, and motion returns to idle. Console errors0. Normal provider/configuration and the existing owner's task content are present; the microphone/wake were not activated.
- Pi-hosted device page was loaded and greeted from Mac. This proves deployed assets/interface behavior on Mac, **not Pi-local rendering**. Its connection subsequently changed to offline during Pi kiosk loading.
- Actual iPhone17Pro/iOS26.5Simulator: compatible native app built, installed and launched with original Pi8891origin. Recorded initial load, palm-forward greeting and return to idle, with original large Alice and safe area. The recording is native WKWebView output, not a resized browser page. A native tap attempt was inconclusive; the accepted native evidence is the initial greeting. Physical iPhone touch, sustained performance and live voice were not retested.

Previously completed presentation-state, pause/reduced-motion and desktop/phone boundary checks remain in the first implementation's QA; only its aesthetic/anatomical acceptance was rejected. They were not relabelled as fresh tests. No backend change, so the backend suite was not repeated. No CI or paid call.

## Deployment and recovery

Pi and Mac were still on the520ab563 backend. A private candidate was built from that original frontend, overlaying only the shared motion/scene files, already-reviewed safe-area CSS and the small AssistantPanel presentation bridge. It does not include unrelated main/Grok backend-dependent UI. Both serve the same68-file candidate index SHA25633570313468827d3ffc8b2a2e326f7982633cb799a37e9e36bc51b6b7f7e0950.

Pi:11changed assets/312796compressed bytes staged beside the existing frontend, with all68candidate hashes and the complete old frontend independently checked. Unchanged assets were hardlinked; changed files were written to separate temporary files and replaced so old hardlinks were never truncated. Linux atomic directory/symlink exchange activated the new dist. Old frontend remains `frontend/dist-before-motion-20261113-v2` under the original release. HTTP index readback and health passed; backend PID1328,53protected configuration/key files and A3/version9 were unchanged at activation. No database migration or backend restart.

Mac: original runtime/data directory and backend retained; previous built frontend preserved as `frontend/dist-before-motion-20261113-v2` in the retained live-agent-eval worktree. A host-helper SQLite3.54read-only WAL check failed after startup, causing rollback and stopping only the newly started API. The same read-only check succeeded with the application's SQLite3.50.4 runtime; using that environment and the actual voice-settings API then completed activation. Original A3/version9, credential/configuration hashes, index and health were checked. No original database repair or replacement was performed. Current web is `http://127.0.0.1:8831/`.

Pi physical screen: original pinned relay/VNC connection worked; the desktop had no active dedicated Alice kiosk. Started the existing kiosk launcher in its existing Wayland session without invoking the backend-restarting session launcher. Dismissed optional Chromium keyring creation without setting a password. The real screen showed the connected device UI but Alice had not finished loading when the relay/VNC became unreachable. Subsequent SSH timed out, and the existing forwarder entered its normal reconnect loop. Cause is unresolved; a pre-existing low-voltage banner is not proof of causation. Red-LED/power investigation stays deferred. **Do not claim Pi animation, GPU performance or sustained operation passed.** New frontend bytes were verified before this loss and remain available for the next connection.

The rebuilt phone retains Pi8891as its API origin; current remote unavailability affects its online services. Mac web stays available independently. Phone/web preview of the same Mac workspace is available at `http://127.0.0.1:8831/?surface=phone`; it is not the native app's Pi connection.

## Evidence and closeout

Private artifacts: `~/.config/desk-companion/alice-motion-20261113/`, including both deployment receipts/manifests/rollback paths, native build/runtime logs, `native-corrected-greeting.mp4`, extracted6.5/8.5/10.5second native frames, `web-normal-greeting.jpg`, Mac-rendered device frames and Pi disconnect receipt. Failed/idle native capture attempts remain separately named and are not acceptance evidence. No private database, credential hash inventory, account screenshot or recording is committed.

Updated product, avatar/home contracts, decision/work logs, AGENTS, entry/handoff and the old QA's supersession notice. Source/docs publication remains PR123, separately recorded in publication.json. No automatic merge. One next step: on Pi connectivity recovery, inspect the kiosk renderer/logs and complete physical greeting/idle validation before declaring the third endpoint accepted.

Closeout checks: changed internal links and JSON receipts parsed successfully; source/assets/secret scope reviewed, with no new binary, credential or runtime database staged. The temporary Vite rig probe and isolated mock API were stopped; normal Mac8831 and the existing Pi reconnecting forwarder are retained. The original recovery checkout received only its current-entry marker update.
