# Group 2 · Web, iOS Simulator and Raspberry Pi release

On 18 November 2026 (Hong Kong), the normal Mac Web service, the installed iPhone 17 Pro Simulator app and the Raspberry Pi kiosk all served `c607759e420fce8a0701474f9ceecf782ce85b35`. The owner selected the Simulator for mobile acceptance and deferred the physical iPhone. [Release readback](release-readback.json) · [GitHub readback](github.json).

## Release and endpoints

GitHub’s full recursive file listing matched all 7,694 tracked entries in the fetched checkout. PR 129 contains the five reviewed heads from 124–128. PR 130 saved the handoff and supplied this release commit. All seven PRs were merged, and the repository had zero open PRs at intake. The shipped backend, frontend, scripts, config and dependency files match tested candidate `42bc01ec`. All 76 files from the delivery build match the retained production build byte for byte. The release adds build metadata and keeps old hashed assets for open Web clients. Its index SHA-256 is `a768850add5fcb1253240dd33cefeb629e0cc753a64d8f07fa9e4284acba5a24`. [Integration acceptance](../2026-11-17-proactive-agent-merge/verification.md).

| Endpoint | What was observed on the running release |
|---|---|
| Mac Web on localhost port 8831 | Verified the 386-file release manifest, backed up the original runtime and switched the service. Chrome opened the ordinary URL, obtained the owner session and rendered Alice and the composer. The authenticated initiative endpoint responded and reported background research off. A new browser profile initially received two 401s while establishing its local session. |
| Native iPhone 17 Pro Simulator on iOS 26.5 | Xcode installed the update over the existing app. A cold launch with no arguments opened the connected Alice home using the saved Mac origin. All 77 frontend files, including build metadata, matched the Web build. Through the running Capacitor bridge, read back the owner role, rendered model, A3 selection and account grant versions. The native grant versions matched the Mac backend. |
| Raspberry Pi | The private delta passed archive and 386-file manifest verification on the device. Both the user service and desktop autostart select the new release. Restarted the existing Desk kiosk using its original profile. A frame captured from the Pi’s own Wayland compositor showed Alice, the connected indicator, calendar and composer. Its hash matched again on the Mac. This verifies a displayed frame. Long-running animation, supply stability and reboot recovery were outside this rollout. |

## User data, voice and account access

Performed the upgrade first on private copies with scheduling and model providers disabled. Every pre-existing table retained its row contents. Before activation, both services were idle and each original SQLite store had a separate checked backup. The actual stores remained at schema version 3 and passed SQLite integrity readback after activation.

| Store | Existing tables checked on copy | Live tables after upgrade | Live protected contents |
|---|---:|---:|---|
| Mac | 124 | 128 | 13 tables matched, including tasks, calendar events, conversations/messages, memories, voice choices, owner permissions and trusted clients |
| Pi | 123 | 127 | The same 13 categories matched against the Pi’s own original data |

The four additions are `initiative_state`, `initiative_findings`, `initiative_seen` and `mail_followups`. Protected configuration and key files kept their original hashes. iOS relocated the data-container pathname during installation. All 12 previously backed-up durable files matched after the update, including the local-storage database and app preferences. SQLite shared-memory files can change when the WebView reopens.

The normal Mac and Pi APIs returned the selected A3 voice ID, description and delivery direction at version 9. Both cached samples matched the original A3 recording by SHA-256. The Simulator independently matched the selection through the app’s own bridge.

| Existing authorization | Mac | Pi |
|---|---|---|
| Gmail | Profile GET 200, identity matched the stored account | Profile GET 200, identity matched its own stored account |
| Google Calendar | Primary-calendar metadata GET 200 | Primary-calendar metadata GET 200 |
| Microsoft 365, Teams and SharePoint | Unconfigured and disconnected | Unconfigured and disconnected |

Google connection versions remained stable for all four grants. The Pi and Mac have separate Google connections. The provider checks requested profile identity and calendar metadata only. The last Microsoft registration attempt required human verification.

## Operating state and verification limits

The release uses the existing official OpenAI Responses integration for changed-source research and the managed executor for browser jobs. Both servers report the managed browser configured, Live as the voice provider and background model research off. No new model request, hosted session or automation was created. The prior 2,501 backend passes, two platform skips and 393 frontend passes belong to the tested candidate. No full suite or paid evaluation was rerun.

The Pi retained its 2.4 GHz configured maximum and the enabled, active RTC timer. The installed timer and service files matched their pre-deployment hashes. No power trial or reboot was performed. An initial compositor capture requested JPEG, which the installed `grim` did not support. PNG capture succeeded. An additional iOS debugger read initially addressed an unavailable controller property and terminated one simulator process. After a normal cold start, the corrected diagnostic used the public view hierarchy and obtained the native readback. The application binary was unchanged and the app remained running on the connected home screen.

## Reading and evidence

- Read the requested worktree’s full `AGENTS.md` and `handoff.md`, current product/identity/runtime requirements, and the latest deployment, OpenAI-reuse, mail, Pi-performance and budget decisions. The Markdown inventory returned one applicable `AGENTS.md`.
- Read the handoff’s 17–18 November integration review, evidence index, verification and research, the proactive contract, the current capability map, and the previous Mac/native/Pi deployment and Pi autostart evidence. Consulted the release scripts, native origin and bridge code, Web/device entry points, database migration definitions, OAuth refresh/account logic, the A3 reference and existing kiosk launcher used for this release. Historical hardware and school artifacts were outside the deployment.
- On GitHub, retrieved the repository’s PR inventory, main tree and paginated details, commits, files, reviews, issue discussion and inline review comments for PRs 124–130. Verified the seven heads against Git ancestry and the run-relevant files against the tested commit. The existing PR review supplies the prior implementation/mesh/test evidence. [PR 129](https://github.com/tantalum666/FYP/pull/129) · [PR 130](https://github.com/tantalum666/FYP/pull/130).
- Updated the project entry points, product contract, proactive contract, capability map, relevant research and Pi status, decision log, work log and handoff. The release receipt contains status, counts and artifact digests. Raw private backups, account details, simulator data and screenshots are retained outside Git under the deployment’s private `three-end-rollout-20261118` directory. The staged scope check covered 15 Markdown/JSON files, 38 added local link occurrences, whitespace and credential/material patterns. It found zero missing link destinations and no application, workflow, runtime database, screenshot or key file in the change.
