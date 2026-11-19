# Original Pi release and Duffel signup eligibility

19 November 2026, Hong Kong. The owner powered on the original Raspberry Pi 5 and asked to install the update previously retained for it. The acceptance target was the same build already in use on normal Web and the native iPhone 17 Pro Simulator, a functioning Alice device screen, and preservation of this Pi’s own account grants and data. An old service process, desktop-only capture or changed grant would leave the respective check open. [Device receipts](receipts.json) · [Web and Simulator acceptance](../2026-11-19-flight-ledger/verification.md).

## On-device release

The pinned owner SSH route authenticated the original Pi. Its live service and working directory identified the former build `c607759e`. The retained portable archive matched its recorded SHA-256. The transfer reused 356 unchanged files from the Pi and sent 50 changed files. The Pi verified all 406 files against the target manifest before activation. The existing ARM environment supplied Python 3.13.5 and Pydantic 2.13.5.

A rehearsal on a private copy compared every original row in all 127 tables. The migration added `text_provider_sessions`. Activation checked for active work, stopped the service, took a verified SQLite backup and retained the previous service definition, environment and kiosk startup entry on the Pi. The new service, its process working directory, the normal device URL and the persistent startup entry all select `85e6aa94d22412b10e0a0d62a4879fb93e9615ef`. The device URL returned the expected frontend hash. The existing Chromium profile opened the kiosk.

| Check | Result from the original Pi |
| --- | --- |
| User data | SQLite integrity returned `ok`, schema 3. All 13 protected live table fingerprints matched, including conversation history, events, tasks, preferences, identity and permissions. The existing secure runtime files matched at activation. |
| Ordinary and browser work | The workspace reported official OpenAI Sessions, GPT‑6.2 Sol for ordinary text, managed browsing and Live delegation, and background inference off. The managed browser was configured and enabled. The installed flight adapter built a request containing only Kiwi’s `search-flight` and no hosted environment. This adapter check remained local to the Pi. |
| Voice | GPT‑Live 1 for audio. A3 version 9, selection, description, delivery and the cached recording matched. Listening quality was outside this deployment. |
| Account authorization | Gmail profile matched this Pi’s own stored Google account. Google Calendar returned the primary calendar’s event-list type. Each provider request returned HTTP 200 with its own grant version preserved. Microsoft 365, Teams and SharePoint remain unconnected. |
| Spending | No paid OpenAI request was made. On 19 November the Pi showed US$9 available, US$0 measured estimate and US$0 reserved. Its allocation runs through 24 November, Hong Kong time. |
| Screen and hardware | The initial compositor capture caught the desktop during startup and showed a low-voltage warning. At 21:10 HKT a second, hash-verified 1280 × 720 frame showed Alice, “Desk connected” and the message composer. Kiosk restarts were zero. The 2.4 GHz CPU ceiling and enabled, active RTC timer matched their pre-deployment readings. The firmware status at the second frame was `0xf0008`. Continuous power stability and unattended restart were outside this rollout. |

The deployer can return the service and desktop startup entry to the retained `c607759e` installation using the private backup on the Pi. Keep newer user data and the spending ledger when changing the running release. The backup includes a SQLite snapshot for recovery if database damage is demonstrated. No rollback or reboot was exercised. The operator retained both compositor frames and the private backup outside Git.

## Duffel and ticket acceptance

A fresh, empty official signup form exposed **32 choices** after expanding the required **Country of incorporation** menu. Hong Kong, mainland China and an “Other” entry were absent. This field concerns the legal entity applying for API access. An existing authorized team can create a developer test token from its dashboard. The published test path uses that token and a simulated airline order. Access for a Hong Kong or mainland student project through a separate channel still needs confirmation from Duffel. No personal form was submitted and no Duffel order was created. The earlier WooCommerce guest checkout remains independently verified. [Official signup](https://dashboard.duffel.com/join) · [Duffel test mode](https://duffel.com/docs/api/overview/test-mode) · [WooCommerce receipt](../2026-11-19-woocommerce-guest/verification.md).

Breeze Airways also documents a sandbox Visa and separate order creation and retrieval. Its test API key is issued by a Breeze contact. This is a supplier option requiring partner access. [Breeze test booking](https://pro.flybreeze.com/docs/api/json/sample-flows/make-a-test-booking/) · [access requirements](https://pro.flybreeze.com/docs/api/certification).

## Scope and evidence

Read the active repository instructions, handoff, current product requirements, latest release and commerce decisions, the relevant research index and runtime sections, the previous deployment and sandbox records, and the Codex review manual’s release guidance. Inspected the retained release manifest, deployment and budget scripts, voice-sample endpoint, flight adapter and on-device app, service and kiosk state. Reused the previous Web, Simulator and paid-provider acceptance. Updated the project entry points, product, personal-agent status, Sessions contract, research index, decisions, work log, handoff and Duffel access note. Checked the changed local links, structured receipts, whitespace and publication scope. No application or third-party test store was added to the deployable source in this closeout.
