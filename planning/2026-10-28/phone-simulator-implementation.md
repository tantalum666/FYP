# Group 2 · Phone implementation and local preview

Updated 28 October 2026, Asia/Hong_Kong. Continuation of the 27 October web/mobile task. The owner explicitly asked to temporarily omit web usernames/passwords and show the phone implementation in Simulator.

## Delivered locally

- The web workspace at127.0.0.1:5190 opens without a username/password in the explicitly enabled local preview runtime. The default service configuration still requires authentication.
- The existing Capacitor iPhone app now selects a dedicated PhoneApp. Its home is a single full-screen Alice VRM scene, Plan and More controls, one upcoming event, and the existing assistant composer. There is no seven-item phone bottom navigation.
- Plan uses day lists and an optional month calendar, with Calendar/Tasks segments. Event details, creation, edits, reminders, recurrence, operation IDs and version handling reuse the existing components/API.
- More opens the current conversation, memories, style, reminders, connections, activity and settings. Native notifications/Widget controls remain in Settings. The same assistant stays mounted while Plan/More are open, preserving unsent input; task discussion has an explicit end action.
- Long conversation content expands onto a readable full-screen surface. Pending proposals automatically expand for review and retain confirmation/cancellation. Browsing/reading panels pause the character; opening management/editor overlays or backgrounding stops an active media connection. No media starts on entry.
- The existing licensed Alice render is the reduced-motion/renderer-error fallback. Original VRM, geometry, textures and licence are unchanged; author attribution and source remain available. The new static fallback has a source manifest.
- iOS content insets now permit the scene to fill the screen while CSS respects safe areas. This removed the native white strip below the phone home.

## Local preview boundary

`DESK_LOCAL_PREVIEW=1` must be explicitly set. Preview bootstrap requires a loopback peer and localhost/127.0.0.1 host, no public origin, no forwarding headers, and an absent Origin or a permitted HTTP loopback Origin. The normal write header is still mandatory. The native URLSession bridge uses a direct loopback request without a web Origin; `capacitor://localhost` cannot bootstrap an owner session. Foreign/remote/public requests remain denied.

Bootstrap issues the normal HttpOnly/SameSite owner cookie with the existing8-hour expiry; it does not embed a password or remove route authorization. Models still prepare drafts and cannot approve them. Paired devices outside this explicit preview keep their existing permissions. Turning the flag off restores the normal sign-in flow. This is a development convenience, not a public no-auth deployment.

The retained preview uses the isolated `.runtime/web-ui-implementation-20261027` data with fictional QA events, memory, style and task, both model providers`none`, background AI and computer executors disabled. To reproduce from`desk-companion/` after stopping this preview:

```sh
DESK_RUNTIME_DIR="$PWD/.runtime/web-ui-implementation-20261027" \
DESK_LOCAL_PREVIEW=1 DESK_NATIVE_CLIENTS=1 \
DESK_VOICE_PROVIDER=none DESK_TEXT_PROVIDER=none DESK_TEXT_BACKGROUND=0 \
DESK_COMPUTER_ENABLED=0 DESK_LINUX_DESKTOP_ENABLED=0 ./scripts/dev.sh
```

## Simulator result and review entry

Existing project`desk-companion/frontend/ios/App/App.xcodeproj`, scheme`App`, bundle`dev.group2.deskcompanion`; iPhone17Pro, iOS26.5, UDID`F57B6381-6448-434C-AE61-A2663F3458A7`. The app was built, installed, launched and captured with its actual Alice home and real local calendar data. Its simulator-only local address is`http://127.0.0.1:8831`. The native preference was configured locally; there is no embedded credential or changed real-device HTTP policy.

The missing official Capacitor8.5.2/Cordova framework copies were restored from the previous local cache. Both original archive SHA256 values and112 extracted files were independently checked against the repository's existing preparation script. No framework code was altered.

The real Simulator mirror is`http://localhost:3200/`. It is a stream of the installed iPhone app, separate from`?surface=phone` browser testing and the historical static HTML concept at8853. The mirror process must stay alive for review; stop only its tracked helper when no longer needed. This is not a deployed mobile service.

## Evidence and remaining work

QA (local historical material: `output/qa/2026-10-27-phone-simulator/verification.md`; not included in this checkpoint) contains tests, screenshots, independent API readback and the native build result. Browser mobile checks passed for create/save, unsaved guards, retained composer text, local calendar query, full conversation, management, Chinese labels and320/393px layouts. These browser flows are not claimed as native touch/keyboard acceptance.

**Simulator visual delivery is complete; full native interaction acceptance remains open.** The available native accessibility snapshot did not expose the WebView controls. Mirror/HID taps also failed to produce a reliable app transition despite live frames and a working Home control, so no native tap/soft-keyboard pass is claimed. Real phone pairing/TLS, VoiceOver, large text, orientation/keyboard interruption, native media, notification delivery, memory/energy/temperature and Pi remain separate checks.

M1 has a real implementation and a native visual build; M2–M4 reuse existing functions with the browser flows above, not a blanket mobile acceptance result. M5 remains incomplete. Next: complete a native touch sequence Plan→New→Save→Back, including software-keyboard visibility and draft recovery, before calling the mobile experience fully verified. No new paid AI, real microphone/camera/screen, Pi/Luwu trial, Git publication or report submission occurred in this continuation.
