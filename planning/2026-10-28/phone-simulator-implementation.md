# Group 2 · Phone implementation and local preview

Updated 29 October 2026, Asia/Hong_Kong. Continuation of the 27 October web/mobile task. The owner explicitly asked to temporarily omit web usernames/passwords and show the phone implementation in Simulator.

## Delivered locally

- The current web workspace atlocalhost:5190 opens without a username/password in the explicitly enabled local preview runtime. The default service configuration still requires authentication.
- The existing Capacitor iPhone app now selects a dedicated PhoneApp. Its home is a single full-screen Alice VRM scene, Plan and More controls, one upcoming event, and the existing assistant composer. There is no seven-item phone bottom navigation.
- Plan uses day lists and an optional month calendar, with Calendar/Tasks segments. Event details, creation, edits, reminders, recurrence, operation IDs and version handling reuse the existing components/API.
- More opens the current conversation, memories, style, reminders, connections, activity and settings. Native notifications/Widget controls remain in Settings. The same assistant stays mounted while Plan/More are open, preserving unsent input; task discussion has an explicit end action.
- Long conversation content expands onto a readable full-screen surface. Pending proposals automatically expand for review and retain confirmation/cancellation. Browsing/reading panels pause the character; opening management/editor overlays or backgrounding stops an active media connection. No media starts on entry.
- The existing licensed Alice render is the reduced-motion/renderer-error fallback. Original VRM, geometry, textures and licence are unchanged; author attribution and source remain available. The new static fallback has a source manifest.
- iOS content insets now permit the scene to fill the screen while CSS respects safe areas. This removed the native white strip below the phone home.

## Local preview boundary

`DESK_LOCAL_PREVIEW=1` must be explicitly set. Preview bootstrap requires a loopback peer and localhost/127.0.0.1 host, no public origin, no forwarding headers, and an absent Origin or a permitted HTTP loopback Origin. The normal write header is still mandatory. The native URLSession bridge uses a direct loopback request without a web Origin; `capacitor://localhost` cannot bootstrap an owner session. Foreign/remote/public requests remain denied.

Bootstrap issues the normal HttpOnly/SameSite owner cookie with the existing8-hour expiry; it does not embed a password or remove route authorization. Models still prepare drafts and cannot approve them. Paired devices outside this explicit preview keep their existing permissions. Turning the flag off restores the normal sign-in flow. This is a development convenience, not a public no-auth deployment.

The current isolated preview uses `desk-companion/.runtime/task-journey-20261028`, API8833 and Vite5190, with fictional tasks/files. Both providers are`none`; background AI, extraction, push and the Linux executor are off. Only the fixed local-note executor is enabled. The previous42-fact memory runtime and other data remain preserved; older process status is not inferred. Current process ownership and reproduction boundaries are in[handoff](../../handoff.md) and[QA](../../output/qa/2026-10-28-native-memory/verification.md).

The memory page now shares `MemoryFactList` with web: local English/Chinese search, result count, empty state and clear action; the parent keeps writes/versions. Search/other fact actions stay locked during one correction, and the existing phone Continue/Discard guard retains the exact draft.

## Simulator result and review entry

Existing project`desk-companion/frontend/ios/App/App.xcodeproj`, scheme`App`, bundle`dev.group2.deskcompanion`; iPhone17Pro, iOS26.5, UDID`F57B6381-6448-434C-AE61-A2663F3458A7`. The app was built, installed, launched and captured with its actual Alice home and real local calendar data. The current build uses launch argument `-desk.server.origin.v1 http://127.0.0.1:8833` for this Simulator process only. Its previous saved address and real-device HTTP/TLS policy were not rewritten. No credential is embedded.

The current preparation reused the pinned official Capacitor8.5.2/Cordova archives, verified their SHA256 values through the repository helper and prepared the ignored local Swift package. Final Capacitor sync and the fresh Simulator build passed. No framework code or dependency version was changed.

The real Simulator mirror is`http://localhost:3200/`. It is a stream of the installed iPhone app, separate from`?surface=phone` browser testing and the historical static HTML concept at8853. The mirror process must stay alive for review; stop only its tracked helper when no longer needed. This is not a deployed mobile service.

## Evidence and remaining work (updated29October)

QA (local historical material: `output/qa/2026-10-27-phone-simulator/verification.md`; not included in this checkpoint) contains tests, screenshots, independent API readback and the native build result. Browser mobile checks passed for create/save, unsaved guards, retained composer text, local calendar query, full conversation, management, Chinese labels and320/393px layouts. These browser flows are not claimed as native touch/keyboard acceptance.

**Current source build/install/launch and native visual delivery are complete; full native interaction acceptance remains open.** The latest mirror eventually exposed WebView labels through its accessibility overlay, but taps still did not produce an app transition. Native CUA showed a transformed/offscreen Device Hub thumbnail and coordinate input failed. Neither an overlay label nor a browser flow establishes native tap/soft-keyboard acceptance. Real phone pairing/TLS, VoiceOver, large text, orientation/keyboard interruption, native media, notification delivery, memory/energy/temperature and Pi remain separate checks.

M1 has a real implementation and a native visual build; M2–M4 reuse existing functions with the browser flows above, not a blanket mobile acceptance result. M5 remains incomplete. The remaining mobile gate is a native touch sequence Plan→New→Save→Back, including software-keyboard visibility and draft recovery. Current393/320px browser memory search, correction/return protection, Plan save/back and API readback passed; see[current QA](../../output/qa/2026-10-29-assistant-permissions/verification.md). The bounded task/job journey is now locally accepted; the broader software next step is mixed-action partial-success recovery in[delivery readiness](../../desk-companion/docs/delivery-readiness.md). No new paid AI, real microphone/camera/screen, Pi/Luwu trial or report submission occurred; branch publication is recorded separately.

## 29 October shared action and navigation update

Calendar/Tasks/More now use PhoneScreen rather than a generic full-page modal. Back, unsaved guards and Alice home remain; task results continue into the same conversation. Web, phone browser and Capacitor share PermissionsPanel, ProposalActionCard and JobActionCard. Current authority is visible beside the composer, with durable choices in Settings. No seven-item bottom bar returns.

The29October source was freshly built, synced, prepared, installed and launched on the pinned Simulator. Its live frame includes Alice and Ask first. One fresh mirror Plan tap again produced no app transition, so native tap/keyboard remains an explicit incomplete gate. Actual393/320px browser checks and short420px viewport checks are separate evidence, not an actual software keyboard measurement.
