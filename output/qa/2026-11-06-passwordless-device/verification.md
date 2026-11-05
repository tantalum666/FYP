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

## Pi deployment and execution

Owner explicitly deferred red-LED investigation and prioritized Pi software/cross-app work. Monitor ended. Confirmed normal app still runs while installing ordinary-user Podman5.4.2/uidmap/fuse-overlayfs from Debian. Rootless engine works; exact ARM64 image transfer is resumable. New release's261source/frontend files match the staged manifest;35frozen core/audio wheels were transferred. Activation and real-app acceptance subsequently completed as recorded below.

Pi had no enumerated capture device, only HDMI playback. Qwen service configuration is preserved for manual owner use; no API budget was reopened. Previous physical reboot wording is corrected: red LED happened first, then the user unplugged/reconnected power. No confirmed cause or hardware-stability result is asserted.

## Additional focused reading

Continued with current product/decision sections, application-work (complete), application-execution (complete affected responsibilities/setup/recovery sections), application runtime/executor/desktop/bridge entry paths, Pi launcher and existing acceptance runner. The research index's current implementation/gap sections were reviewed; combined output for the full index was truncated and is not recorded as full reading. Official Podman user namespace documentation checked for `keep-id:uid/gid`. Historical power sources were used only before the user deferred that investigation.

Updated current entry, product, decision log, handoff; added passwordless-device and Pi application runtime contracts; corrected current architecture/first-boot/application-work/display/maintenance descriptions. Final activation evidence, work-log and publication receipt follow actual results, not plans.

## Production media response correction

Production middleware still sent `camera=()`, although Vite local media worked. Changed it to same-origin camera/microphone permission eligibility; browser consent and explicit share controls remain. Local owner/origin/media-policy checks19passed after this correction. The first activation probe omitted mandatory X-Desk-Request and received403; the transactional rollout restored the old unit/autostart. Corrected the probe before retrying. Off-device backup archive and all13included files are hash-verified; schema3quick_check passed. Pi recognizer construction with read-only weights succeeds, independently of keyword accuracy.


## Pi runtime startup diagnosis

The verified620,205,835-byte ARM64 image archive was resumed rather than retransmitted. Archive SHA2562e81e1448591e1ed2dc4a031aa20a37a405cb365897c9b6b39f4693d4681d4ed. Docker's OCI manifest ID differed from Podman's config ID; architecture/user and every RootFS diff ID were verified before using local imagef8787344ea77ea05dabac5d66f93cbf22c0a7e8ff4a35c68c70ed396634e6222. The initial45-second launch cutoff interrupted first-use mapped-layer preparation. A longer bounded attempt exposed the actual missing memory controller. Only the identified never-started container was removed; image, mounts, prior app and user data were preserved.

Host root controllers:cpuset/cpu/io/pids; delegated owner controllers:cpu/pids. Launcher now refuses missing RAM control unless an operator explicitly sets DESK_APP_ALLOW_UNBOUNDED_MEMORY=1. This host uses that recorded exception; it has no container RAM cap. Actual runtime has2CPU/256PID limits, network none, Privileged false, scoped mounts and Chromium sandbox. No boot change/reboot was made. Launcher/transport checks10passed. Bridge status from a NoNewPrivileges user unit reports UNO connected with real office/browser processes; API's existing NoNewPrivileges protection remains.

Pi API source26c347a is activated with automatic owner connection and Qwen idle/configured; Alice wake is available but inactive. Native simulator was relaunched against the Pi relay and shows Alice, Desk connected and Qwen controls. The real Work acceptance subsequently passed, as recorded below.


## Completed target acceptance and service activation

Pi runs the new release at `/opt/desk-companion-releases/20261106-passwordless-apps`, with the original schema3data and provider credentials preserved. The normal API returns applications enabled/configured with workbook/document/PDF/text actions. Qwen is configured/idle; wake is available/inactive. Permission mode remains Ask first. Standalone text/background AI remains none/off; there was no paid-model request. This is not live-model autonomous Work acceptance.

The isolated acceptance ran on the Pi, not on the Mac Docker reference. Chromium read the selected fictional quotation HTML. Real Calc first handled36copies/HKD900, then the scripted steering changed to48copies/HKD950. The returned totals were1020.80/902.00/1003.20; only Birch was feasible at50copies after the explicit synthetic minimum-order answer. Four real app jobs produced initial/revised XLSX, Writer ODT and PDF. Run phase exited73after12.14s at the intentional saved-before-ack checkpoint; after app restart, resume succeeded in14.59s. These timings are scripted harness durations, not model/voice latency.

The revised workbook's SHA/mtime stayed identical across recovery. All four downloaded output hashes match receipts. Both A4 PDF pages were rendered and visually checked; table/text are legible with no clipping. [Acceptance](pi-application-acceptance.json), [normal service](pi-normal-service.json), [deployment](pi-deployment.json). Private binary artifacts/screenshots remain outside Git.

Initial container termination required SIGKILL after10seconds. Added Podman's init/catatonit and disabled inherited proxy environment. Actual normal stop now takes0.38seconds with no forced stop; a new office/browser instance starts. After that recreation, all four immutable versions and three current outputs were reopened through the real applications; every file SHA/mtime remained unchanged. The new user service is enabled, and the API Wants/After it while retaining NoNewPrivileges. Kiosk is active and the next graphical autostart points at the active release. This does not establish a new physical cold-boot or touch/microphone result.

## Final scope and retained gaps

Power/red-LED investigation remains deferred at the owner's request. No hotspot, SD rewrite, power stress test or reboot was added. No CI, paid models, external messages, purchases or school submission. Source/target app configuration are separate from GitHub merge; this branch is proposed independently.

The next step is ordinary Alice/voice → admitted persistent Work using the existing queue, including partial failure and owner cancellation. Normal standalone Work planning still needs provider setup/manual use; live-model quality remains open. General host GUI, real authenticated email/shopping/travel accounts, human Pi audio/AEC, physical touch and container RAM control remain unverified/unavailable as stated above. Synthetic acceptance is not a purchase or a professor-facing deliverable.


## Publication and closeout

[Draft PR88](https://github.com/tantalum666/FYP/pull/88) targets mainabf6387. GitHub source checkpoint10708abeb6f9d7a14b4b97d8565beb04340cccd6 matches the locally tested/deployed source; all262target source/frontend files were independently hash-checked. The PR is open/draft/unmerged; no CI was used. [Receipt](publication.json). Later receipt-only commits do not change deployed code.

Updated AGENTS/current entry/product/decision/work-log/handoff and affected connection, display, media, application, architecture and first-boot contracts. All local Markdown links in changed documents resolve. Existing original-recovery checkout notes were preserved, with a local routing/correction notice to this new branch. The isolated providers-off QA API/Vite and temporary browser viewport/tab were cleaned up; raw test logs and screenshots remain in the owner-private task directory. Pi relay/API/kiosk/application service and the Pi-connected native simulator remain available.
