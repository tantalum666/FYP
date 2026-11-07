# Group 2 · Complete Alice wake-to-Live repair

7 November 2026. Source `f2a33e9d3f9ff82cdc200e09d2a6cf5f07a943c6`. The owner reported calling Alice without a response and explicitly directed the agent to complete acceptance itself. The engineer set a fresh USD0.50 cap; earlier ledgers stayed closed. [Structured results](validation-summary.json). No CI.

## Recovery and confirmed cause

Read active AGENTS/entry/handoff, current product sections and latest decision; voice/wake/audio, device panel, schema conversion, evaluation runner and focused regression sources. Reused the current UI contract and earlier read evidence. Applied frontend debugging and OpenAI troubleshooting; checked official [Live error/session behavior](https://developers.openai.com/api/docs/guides/live-conversations), [delegation](https://developers.openai.com/api/docs/guides/live-delegation) and [token preflight](https://developers.openai.com/api/docs/guides/token-counting).

Two ordinary owner attempts at22:48Hong Kong time stopped before audio acceptance:4.4/5.6seconds, zero accepted audio and no final provider receipt. Old records did not retain failure identifiers. A free model-list200only established access, not valid session startup.

`flatten_schema` removed every dictionary key named title, including business fields inside properties. Nine required-field references across the complete catalog therefore lost their property definitions. An actual non-generation token-count preflight rejected the old27-tool payload with400/invalid_function_parameters at tools[2].parameters (application_job_draft). The repaired same27-tool payload returned200. Schema annotations are now removed without deleting business property names or literal enum/const data; existing validation and authority remain intact.

The previous USD1voice smoke trial restricted its advertised tools to read-only queries. It demonstrated that smaller path, but did not cover the normal complete-catalog startup. This was a validation gap; do not generalize that old result to the full production configuration.

System audio inspection also found an Apple Bluetooth device selected as the system default, with the MacBook Pro built-in microphone separately available. The application previously followed the default. A new shared preference now selects the exact input for local testing, wake listening and voice. Selection changes stop the local test; unavailable explicit devices do not silently fall back. Blocked storage retains the selection for the current page. The owner's normal Web origin was set to the built-in microphone and actual local input levels0.0550/0.0146were observed, without saving or sending that microphone audio.

## Complete browser acceptance

Used a separate loopback8832instance of the actual built app and production VoiceService/OpenAILiveProtocol, with the full27-tool catalog, normal1024output allowance and original business dispatcher. Fictional calendar entries were10:30–11:00and14:00–14:30. No owner data was copied.

The private fixture acquired and cleaned up the actual selected native microphone, while routing a fixed synthetic MediaStream into the unmodified wake/voice capture pipeline. Native microphone audio reached a local level analyser only; it was not recorded or sent to OpenAI. The fixture did not replace the keyword detector, voice client, model, tools, calendar service or playback. It bounded provider sessions/requests and reserved a separate durable budget before connection.

- Two greeting/idle cycles successfully woke, played “I'm here”, finalized usage and automatically returned to local waiting. Interactive inspection initially delayed the follow-up fixture beyond the30second idle boundary; the final scenario scheduled the question automatically after ready. One intermediate local fixture utterance did not trigger; a subsequent one did. These observations are not a keyword-accuracy percentage.
- The automatically sequenced full scenario produced one wake and ready event, no error, correct Alice identity and the spoken answer of two meetings at10:30a.m./2p.m., Hong Kong time.
- Independent tool audit contains exactly one calendar_query, outcome ok, saved=false, spanning the correct local day. Browser playback acknowledgement marks the answer played; no calendar writes occurred. It then returned to local waiting and released the cloud session.
- The first useful answer audio was rendered6392.6ms after the capture boundary. This passes the current10second deadline but does not meet the approximate5second experience target. No physical-ear, human-accent, background-noise or false-positive rate is claimed.
- Native device selection/meter and complete answer screenshots are owner-private. There was no app/framework console error; observed warnings came from an unrelated Chrome extension. The QA tab and server were closed and test streams released.

Three finalized provider sessions used36/34/53seconds. Only the final calendar scenario delegated backend work:two requests,13171input/119output tokens. Conservative uncached accounting including10percent margin is **USD0.1864995**. The **USD0.50ledger is closed**, with no unknown receipts; this is not a provider invoice. No further paid test is authorized by this receipt.

## Regression, diagnostics and release

Full backend via `.venv/bin/python -m pytest -q`:2054passed. Full frontend:343passed. Ruff/format, Prettier, TypeScript and production build passed. The standalone pytest entry initially lacked the project scripts import path; the standard module invocation resolved collection. Two old transpilation-based audio tests needed their module fixture to resolve the new shared microphone helper; assertions were unchanged. No dependency or workflow was added.

Provider errors now retain bounded code/type/parameter identifiers and startup/active phase in the existing voice receipt, never raw provider messages or owner prompts. Configuration rejection has a specific UI message; a deliberate new wake attempt clears the stale failure notice. Closed ledgers, explicit permission/identity checks, slot ownership and no automatic paid-error retry remain.

Mac normal API8831/Web5190 runs the repaired source and the selected built-in input. Pi sourcef2a33e9is active at `/opt/desk-companion-releases/20261107-wake-repair`:292files verified,22-file stopped/checkpointed backup verified off-device, original environment/keys preserved and app/application services active. [Activation receipt](activation-summary.json). This does not establish physical Pi microphone/speaker acceptance. Updated voice/media/maintenance contracts, product, decisions, handoff, work-log and entry routing. Private fixtures, audio, device IDs, backups and credentials are excluded from Git.

Normal Mac Web was reloaded after service restart, the saved MacBook Pro input was read back, and the final page visibly showed Waiting for Alice with cloud voice disconnected and no stale failure notice.
