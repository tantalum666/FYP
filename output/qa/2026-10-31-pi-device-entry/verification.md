# Group 2 · Pi dedicated-display entry correction

31 October 2026, Asia/Shanghai. The owner correctly recalled the independent Pi display. The previous reply showed ordinary workspace settings and did not clearly distinguish that from the dedicated device surface. This continuation checks the actual source, installation and rendered entry; it does not redesign or upgrade the app.

## Actual reads and selected scope

- AGENTS.md and handoff.md in full; unchanged product requirements carried forward from the preceding full read and its relevant current sections reread; decision-log September30 device decision and latest October31 Pi sections.
- Full planning/2026-09-30/device-display-spec.md, design/desk-companion/device-ambient-v1/README.md and output/qa/device-ambient-redesign-2026-09-30/verification.md. Their historical browser results are not recounted as new Pi tests.
- Full frontend/src/main.tsx, scripts/kiosk.sh, scripts/pi/welcome.py, scripts/pi/session.sh and frontend/public/manifest-device.webmanifest. DeviceApp.tsx lines1–125 only; firstboot.py autostart-generation section only. Existing Pi Mac/first-boot guides carried forward and relevant sections reread.
- Actual installed kiosk.sh, welcome.py, session.sh and desktop autostart file, plus DeviceApp bundle filenames, read over the original pinned SSH connection. No credential file or private database was read for this check.
- frontend-testing-debugging skill in full. All GUI work used the available CUA in-app browser API as required by the host; no external Playwright process or browser dependency installation.

## Findings

| Evidence | Result |
|---|---|
| Source routing | `surface=device` selects DeviceApp independently from PhoneApp and ordinary App |
| Incorrect previous screenshot | `page=device` is the ordinary workspace settings view, not the dedicated display |
| Pi installation | DeviceApp JS/CSS bundle, kiosk.sh and welcome launcher are present |
| Dedicated launcher | kiosk.sh defaults to local8831 `?surface=device` with Chromium `--kiosk`; welcome button uses the same surface with `--app` |
| Actual boot entry | desktop autostart → session.sh → welcome.py; direct kiosk autostart is not configured |
| Runtime architecture | Dedicated React interface and local Pi API/static resources; Chromium renders the local application; Mac browser is a management/preview client |

## Rendered verification

Target flow: Pi-provided `?surface=device` → visible clock/month/locked-calendar display → Touch to manage → login panel → close → display. The original tunnel had ended between turns and the previous temporary tab was absent. Restored the same paired-key LAN tunnel; no network/firewall policy change. The initial preview refusal belongs to that missing local tunnel, not a missing DeviceApp.

The actual page at `http://127.0.0.1:8891/?surface=device&lang=zh`, title Desk Companion, rendered at1280×720 with no framework overlay. It showed the independently composed device layout, without the workspace sidebar. The flow above passed; browser warn/error logs were empty. Device language currently follows its own saved preference, so the fresh device view remained English despite lang=zh; no preference was changed. The calendar stayed locked in this fresh browser session, and login/pairing was not performed. This is not a test of authenticated calendar edits or hardware touch.

Screenshot: owner-private `~/.config/desk-companion/pi5-home/qa/device-display-correct-entry.jpg`. It is an actual Pi-served page rendered on the Mac, not a new mockup or a Pi GPU/physical-screen performance result. The correct display tab was marked as the deliverable. No Pi-local Chromium was started, no kiosk/autostart setting changed, and no camera/microphone/model or mechanical action ran.

## Correction and next gate

Product, current entry/handoff, Pi access guide and dedicated-display contract now state both routes and the actual boot gap. The device target remains independent full-screen startup and recovery on the Pi. The previous real undervoltage event still requires supply/cable confirmation before a load retest and app/database upgrade. Physical touch, Pi full-screen cold boot, durable pairing/session recovery and sustained operation remain open. No source code changed; unchanged backend/frontend suites were not rerun for this explanation. Local links, JSON evidence and secret publication scope are checked separately before pushing this clarification to the existing PR73 branch.
