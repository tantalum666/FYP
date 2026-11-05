# Passwordless surfaces and Alice on Pi — 6 November 2026

In progress. Owner explicitly requested removing Sign in across all app surfaces and restoring Alice/voice on Pi. This supersedes manual sign-in UI and the calendar-first engineering default for DeviceApp. No paid-model test budget is opened. Current software work starts at mainabf6387 on codex/passwordless-alice-device-20261105; Pi network recovery remains in separate draftPR87.

## Read scope and implementation scope

Read the recovery checkout AGENTS/current entry/handoff and relevant current product/Pi decisions; the unified checkout AGENTS, desktop-conversation, openai-alice-wake, ui-copy, device-display-spec and phone-simulator contracts. Read the actual session/bootstrap, workspace identity lifecycle, login/settings routes, DeviceApp/calendar/panels, phone home/environment, AssistantPanel media/session sections, native setup, first-boot launcher, wake configuration and captured audio-device inventory. Relevant React and frontend-testing skills applied. Long App/AssistantPanel files are read by the complete affected session/render/lifecycle sections, not claimed fully re-read. Memory is orientation only; historical PR/Pi states were refreshed from current source and the device.

Implement a common local-owner bootstrap and connection recovery, remove application password forms/Sign out entry points, keep network/paired-device/action authority boundaries. DeviceApp opens Alice plus the existing conversation/voice client and keeps calendar/tasks/settings accessible. Preserve conversation across overlays and release media when obscured/backgrounded. Existing licensed avatar/assets are reused. Native setup retains only desk-address selection. Validate all rendered surfaces through CUA; do not resize the owner's tabs.

## Initial evidence

The running Pi's capture-device list is empty; playback lists HDMI devices only. The Mac browser can use Mac media independently. This is not a Pi microphone/speaker acceptance result. Backend local/bootstrap boundary tests18passed; frontend session coordination4passed. Initial test-harness TypeScript syntax/formatting input issues were corrected. Existing provider config and keys remain private; no live model call made.

## Completed local verification

- Full backend:1789passed, frontend:324passed; typecheck/build and changed-Python Ruff passed. Transport/job/Work focused checks:36passed. The first command-line pytest invocation omitted the project root from import paths; `python -m pytest` resolved collection. A shell variable named `status` caused a wrapper error after the successful full run; the recorded pytest summary is authoritative.
- Web chat→Tasks→chat preserves an unsent draft. Pi surface checked at1280×720 and1024×600; composer remains visible with no horizontal overflow. Expired QA sessions reconnect automatically without a password form or lost draft.
- Phone393×852 keeps full-screen Alice, has no password fields/overflow, preserves a draft across Plan, and keeps its own media dialog open. Local device tests do not start a cloud provider. QA tab viewport reset and tab closed.
- iPhone17Pro/iOS26.5 native build/install/launch succeeds; first screen shows Alice and Desk connected with no login. Native touch/keyboard remains unverified (accessibility snapshot exposed no actionable targets).
- Actual Mac microphone input meter reached0.0516009563 after the owner allowed permission; test stopped and media panel closed. No raw audio saved. The initial network trace was truncated, so no full-trace proof is claimed.
- WakeDetector construction succeeds against read-only Mac weights without modifying them. The standalone synthetic Alice sample did not trigger; no positive human/keyword accuracy claim.

## Pi work in progress

Owner explicitly deferred red-LED investigation and prioritized Pi software/cross-app work. Monitor ended. Confirmed normal app still runs while installing ordinary-user Podman5.4.2/uidmap/fuse-overlayfs from Debian. Rootless engine works; exact ARM64 image transfer is resumable. New release's261source/frontend files match the staged manifest;35frozen core/audio wheels were transferred. Activation and real-app acceptance are not yet complete.

Pi had no enumerated capture device, only HDMI playback. Qwen service configuration is preserved for manual owner use; no API budget was reopened. Previous physical reboot wording is corrected: red LED happened first, then the user unplugged/reconnected power. No confirmed cause or hardware-stability result is asserted.

## Additional focused reading

Continued with current product/decision sections, application-work (complete), application-execution (complete affected responsibilities/setup/recovery sections), application runtime/executor/desktop/bridge entry paths, Pi launcher and existing acceptance runner. The research index's current implementation/gap sections were reviewed; combined output for the full index was truncated and is not recorded as full reading. Official Podman user namespace documentation checked for `keep-id:uid/gid`. Historical power sources were used only before the user deferred that investigation.

Updated current entry, product, decision log, handoff; added passwordless-device and Pi application runtime contracts; corrected current architecture/first-boot/application-work/display/maintenance descriptions. Final activation evidence, work-log and publication receipt follow actual results, not plans.

## Production media response correction

Production middleware still sent `camera=()`, although Vite local media worked. Changed it to same-origin camera/microphone permission eligibility; browser consent and explicit share controls remain. Local owner/origin/media-policy checks19passed after this correction. The first activation probe omitted mandatory X-Desk-Request and received403; the transactional rollout restored the old unit/autostart. Corrected the probe before retrying. Off-device backup archive and all13included files are hash-verified; schema3quick_check passed. Pi recognizer construction with read-only weights succeeds, independently of keyword accuracy.
