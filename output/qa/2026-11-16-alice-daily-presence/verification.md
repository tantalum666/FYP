# Group 2 · Voice, weather, daily cues and local camera QA

16November2026. Owner screenshots show spoken formatting names, unavailable HK forecast, insufficient proactive task follow-up and a manual camera preview disconnected from posture monitoring. [Reading/scope](reading-and-plan.md), [behavior contract](../../../desk-companion/docs/daily-presence.md). Preserve A3 and existing account/data/approval boundaries.

## Implemented behavior

- Added `weather_query` to the complete31-tool text/voice catalog. Actual HKO query returned7dated forecasts, first date17November and issue16November11:30+08:00. The widget previously had current conditions only; there was no forecast tool. Coarse location preferences remain unchanged.
- Voice-only task-title hints preserve saved titles while replacing spaced formatting separators. Shared speech guidance asks for natural summaries; low reasoning uses the same Sol backend. Brief in-speech zero-PCM pauses are retained rather than removed, and idle silence remains filtered. Playback lead adapts160–350ms without changing PCM/pitch/A3.
- One owner-visible current cue beside Alice uses existing task/nudge/posture state. Completion is version-checked owner confirmation; ongoing work records progress; one-hour snooze persists. Closed task/nudge notices resolve together. Late morning openings can catch up; quiet/private/proactivity rules remain.
- Added browser-local CPU pose inference and an owner/session/camera-bound short lease. Local consent survives app navigation and is scoped to the backend origin. Same-client reload invalidates its old lease; other clients/replay/wrong cameras are rejected. Raw video/audio/images are not sent to this API or a cloud vision service. Model/WASM are local, pinned/checksummed generated assets; Apache license included. Chat picture sharing remains separate.

## Local and physical checks

Complete backend suite: **2370passed**, two existing warnings. A first run retained the old two-minute briefing expectation; updated that scenario to the new explicitly intended late-opening behavior, then the full suite passed. The later brief-PCM/Live changes passed30focused voice lifecycle checks. Frontend **389passed**, TypeScript/build/Ruff passed within the logged sequence; final cosmetic indicator/details changes are checked at release preparation. No CI.

Real browser/actual local-model synthetic camera:640×480, continuous accepted observation sequence, navigation/reload automatic recovery, pause releases the worker, explicit resume. The first reload revealed409from the old lease; same-client replacement fixed it and was retested, including rejection of late old-token frames. No page errors in the accepted flow.

Separate short **physical Mac camera** check through the built app/static CSP:15accepted observations, all correctly reported `uncalibrated`; connected=true; worker released afterwards; no page errors. No frame, recording or cloud vision request was saved/sent. This proves the camera/model/landmark path, not personal calibration or posture accuracy.

Actual desktop1365×950 and phone393×852 `?surface=phone` flows showed a single dark cue, readable wrapped content and no horizontal overflow. The full month and dominant Alice remain. Existing footprint measurement includes the cue. One fixture completed with statuscompleted/version2/no next check; another recorded progress atversion2 and a future check. Readback was independent SQLite, not just a toast. The synthetic and physical test browsers were closed.

## Authorized voice round — CLOSED

Owner allowed **US$0.20 total /60seconds**, synthetic speech, A3 unchanged. Exact token-count preflight included the full31-tool catalog plus the synthetic task/public forecast:6558tokens. All child ledgers are retained closed, with final provider usage receipts. No earlier managed-browser budget was reopened.

| Attempt | Elapsed | Result |
|---|---:|---|
| 1 |16.992s | Task read and A3 confirmed; evaluator incorrectly treated tool JSON arguments as a dict; stopped before forecast |
| 2 |16.575s | Task read/A3 confirmed; an overly narrow evaluator read allowlist stopped a legitimate follow-up; failure retained |
| 3 |24.926s | Bound synthetic task; task_details and weather_query(7,zh) succeeded; A3 confirmed; received natural task wording without slash/dot names |

Total **58.493seconds**. Reconciled conservative cost **USD0.11280236**, including a10percent margin and actual cached-input counts. Verified pricing: short-context Sol input2/M, default30-minute cache writes2.5/M, cached reads0.1/M, output10/M; Live0.05/min. Treat all noncached input at the larger2.5/M write rate. This is a receipt-based conservative estimate, not an invoice. [Pricing](https://developers.openai.com/api/docs/pricing), [cache accounting](https://developers.openai.com/api/docs/guides/prompt-caching).

The final spoken summary was cut short at the time cap. **Full weather speech completion, physical speaker continuity and user-perceived naturalness are not accepted.** Do not turn successful tools or generated audio into those claims. No more paid calls in this round. The original user's playback metadata showed9rebuffers/5328ms largest gap, but that metric does not independently distinguish transport stalls from natural inter-response gaps.

## Delivery and remaining limits

Application source 2c31f430 has been delivered to all endpoints with the final hashes/readback below. Mac and Pi Google grants passed independent provider reads; Microsoft remains at human verification. Pi's physical rendering remains a separate unresolved check, and the owner subsequently prioritized frequent shutdown investigation. Its display/container are temporarily held for power diagnosis; deployed files are preserved. See [power QA](../2026-11-16-pi-power-recovery/verification.md).

Camera first-use consent/three-position personal setup remain necessary. Real accuracy, long-running Pi/mobile operation and background iOS camera use are not established by the short checks. Proactive cues currently appear on screen; they do not open paid A3 speech sessions automatically. Continuous mailbox tracking, authenticated browser takeover/payment/ticketing are not completed by this slice.

Private evidence: `~/.config/desk-companion/agent-runtime-20261116/` (physical-camera-readback.json, proactive-ui-readback.json, HKO receipt, voice-daily-recheck/round.json, local test/build logs and screenshots). No private media, credentials, databases or generated model binaries belong in Git.

### Final data-scope repair

Release review found a historical acceptance task appearing in general work summaries despite individual follow-up being disabled. Its exact `qa-task` operation and title were matched to `scripts/application_work_acceptance.py`; that one owned fixture was paused through the normal versioned API, preserving its evidence. Real user work was not bulk-edited. Proactive briefings now use followed/non-paused counts and previews; an empty followed list does not manufacture a daily cue. Today's manual summary excludes paused work and includes saved status/next-step fields, with private text redacted. Focused task/nudge/owner-lookup checks cover these changes. Initial daily source1d16329a was delivered to Mac/native and staged on Pi; final source/readback is recorded below after the small scope correction.

### Delivered version and owner reprioritization

Application source **2c31f430ab57b858cd32316830c34d8c4386b8a7**, release20261116-2c31f430. Mac/Pi350-file manifests and API/index readback passed; schema/table counts unchanged during final activation (Mac124, Pi123). A3/version9, protected files and account-connection versions matched before/after. The iPhone17Pro/iOS26.5 Simulator was rebuilt/installed/launched; embedded build-info/index matches, camera usage description and local pose assets present, actual connected Alice home observed. This is not physical-iPhone acceptance. Shared frontend indexSHA256:1818b3c7cf867d09a377df4bfe48d58dfad42e57b1b47031f8b3b5258a3be976.

Mac's existing08:00/21:00daily check-in times were enabled with quiet22:00–07:00preserved. The owned historic QA fixture was subsequently closed as a cancelled test record (not falsely completed), retaining documents/receipts. Final follow-up/owner-lookup scope checks:35passed; kiosk profile tests:2passed. Current native and web screenshots show no QA item in pending work and no page errors.

Pi's final autostart pointer, six real newlines, dedicated private profile and user kiosk-service start returned success after dorm reconnection. The owner then reported more frequent automatic shutdown and made that the priority. Relay loss/rendering instability prevents final physical-Pi acceptance. See the new power-recovery record. Both model-test budgets remain closed; no new paid call accompanied activation.
