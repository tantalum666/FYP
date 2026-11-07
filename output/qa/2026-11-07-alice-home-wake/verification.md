# Group 2 · Shared Alice home, local wake and GPT Live

7 November 2026. Source `1660ffcfffa6242d4618d7996469b926ac30b61b` is active on Mac and Pi. [Structured results](validation-summary.json) and [Pi activation](activation-summary.json) distinguish the local, browser, provider and deployment tracks. Publication is recorded separately.

## Request and focused recovery

The owner selected the dark, simple phone appearance for Web/phone/Pi and asked to retain a large Alice, full phone month, clock/date, location-based weather with Hong Kong fallback, and a dark translucent composer without the welcome question. Subsequent reports identified input flicker, overlapping read errors and repeated location permission prompts. The voice direction is GPT Live with Realtime retained, and local calling Alice after initial microphone opt-in.

Read the active AGENTS and entry/handoff in full; current product requirements and current-state sections; the latest relevant decision-log sections; ui-copy, desktop-conversation and openai-alice-wake focused contracts. Read current phone/device/companion/conversation/wake/audio and changed backend protocol/configuration sources. At closeout, read passwordless-device and software-maintenance in full. Earlier unrelated historical Markdown was not mechanically reread. Preserved the pre-existing preview handoff/work-log edits and preview QA directory.

Applied frontend design/testing, React lifecycle and OpenAI documentation skills. Consulted official Live overview/model/migration/delegation/conversation/cost/pricing and HKO/Open-Meteo sources. The second generated layout concept was visually compared with actual rendered Web/phone, then superseded where the owner's explicit full-calendar/time/weather/large-Alice corrections required it. No generated avatar or new third-party character asset was shipped; existing AliceChan licensing remains visible in More.

## Implemented and checked

- Shared AliceScene/AliceAgenda/HomeConditions reuse current business readers and permission services. Web/Pi use AliceHome; phone preserves its navigation and full month. No new task/calendar polling or second assistant service. No permanent Web sidebar, framed agenda cards, white composer or welcome question.
- Actual browser checks covered phone393x852, short phone393x640, normal Web1312x681 and short Web800x480. A discovered short-screen overlap was repaired by bounded independent agenda scrolling. Desktop weather/calendar spacing and canvas CSS sizing were corrected. Phone Plan/More and returning to an unsent draft worked; test draft was cleared. Existing privacy regression remains green.
- Four injected read503s produced one concise recovery row outside the input, with existing content retained and subsequent recovery. Eight geometry samples over3627ms recorded stable input y695/height62, zero disabled samples and unchanged draft. Test interception was cleared; temporary QA tabs were closed. Same-device capture contention is shown rather than opening a duplicate microphone/socket.
- Mac and Pi loopback cookies formerly shared one name and caused401/403 reconnects/rate limiting. Port-scoped cookie names now preserve the original cookie flags, lifetime, local bootstrap and role/origin checks. Two-store/shared-cookie-jar tests include independent logout and legacy-cookie rejection. The final1000 Mac HTTP records were all200; this is a bounded observation, not a claim of indefinite uptime.
- Automatic location never prompts on prompt/denied/unsupported permission states. Already-granted location uses one pending request and coarse RAM cache. A five-second application deadline clears the watch, failure persists only a flag, and manual location retry is explicit. Six tests cover concurrent reads, failure across module restart, manual request and stalled/late callbacks. Chrome rendered nearby Open-Meteo weather; IAB used actual HKO Hong Kong weather after refresh. Native permission dialogs were not automated. Coordinates are rounded before same-origin POST and never stored in browser storage.
- Local wake was missing from the normal Mac service configuration; pinned model configuration is now explicit. Synthetic Hey Alice/Alice/爱丽丝 triggered; two unrelated English/Chinese phrases did not. Reload with existing mic permission restored local waiting. The final Web preview was left visibly waiting locally with cloud voice disconnected. This is not a measured human/noise accuracy rate or native background listener.

## Real provider trial and cost

The owner explicitly approved one synthetic trial, max45seconds and USD1. The real production VoiceService/OpenAILiveProtocol was used with an isolated fictional calendar and existing approved key, not a scripted model. Local wake was detected; the model identified itself as Alice, read the calendar and spoke two meetings at10:30 and14:00. Returned audio, zero calendar writes and slot release were checked.

Provider duration20seconds; end-to-end controller25.251seconds; two Responses delegations,5830input/133output tokens including2561cached input. Conservative usage accounting **USD0.051861333333333336**; the ledger is **closed**. This is not a verified provider invoice. The test was manually stopped after the complete answer and received a final session.closed; the30-second idle path was separately exercised offline. No human voice was recorded and no physical speaker/AEC or controlled Live-versus-Realtime ranking is claimed. Earlier closed budgets were not reopened.

## Local validation and limitations

- Full backend:2051passed. Full frontend:341passed. Changed Python Ruff/check/format, frontend Prettier, TypeScript and production build passed. Existing dependency deprecation/test warning and bundle-size advisory remain; no new CI workflow or Actions run was used.
- Live uses gpt-live-1 speech with gpt-6.1-sol delegated reasoning. Independent typed chat remains Responses. Realtime is explicitly selectable by configuration. Live does not accept typed/image messages in this implementation; local camera preview remains, with frame sharing available only for a compatible provider.
- Human wake/interrupt/AEC, native phone background and physical Pi microphone/speaker acceptance remain open. Real merchant login/payment/ticket receipts and native email sending remain outside this UI/voice milestone.

## Runtime and release

Mac Web5190/API8831 runs the active checkout. Pi `/opt/desk-companion-releases/20261107-alice-live-final` contains292 hash-verified source/assets, reusing the retained frozen environment. Original owner keys and database are preserved, both app/application services are active, and local automatic entry, frontend bytes, GPT Live/wake/text/browser readiness were independently read back. Pi continues using the explicitly owned OpenAI-only VPS route; no VPS configuration or power diagnosis was changed here. Activation made zero paid model calls. The forwarded Pi page rendered the new Alice home; that is separate from physical display/audio acceptance.

A21-file stopped/checkpointed backup was transferred off Pi and every member hash verified before activation; archive SHA256 `4765fe3613094cf998b0c6bb55dc3953a263c3cf550469d2a473d954f530daa5`. Private backup/activation scripts and media are outside Git. Activation retains prior releases and restores unit/autostart/environment on failure; weather preference rollback also restores compatibility with older binaries without replacing other preferences or owner data. Do not remove the20261106 release supplying the frozen environment symlink.

Updated alice-home, openai-alice-wake, desktop-conversation, passwordless-device, software-maintenance, product, decision-log, work-log, handoff and entry routing. Added-line credential-signature scan and asset/workflow scope review passed; raw owner screenshots, audio, credentials, database and private deployment scripts are excluded from publication.

Local Markdown link check:398targets,0missing. Recovery-only AGENTS routing banners in the retained all-pr-review and openai-personal-agent checkouts now point to this active entry; their other local changes were left intact.
