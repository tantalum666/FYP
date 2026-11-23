# Group 2 · Daily assistance and local posture observation

16November2026. Owner asks for natural spoken work/weather answers, proactive progress follow-up and ongoing posture observation. Reuse the existing workspace/task/nudge/posture services; do not add a second scheduler, planner or conversation store.

## Spoken work and weather

As of 23 November, `weather_query` resolves cities worldwide. Ordinary questions such as “帮我查一下东京的天气” use the same public read as the OpenAI Sessions and Live functions. A return includes the destination-local date, a current observation or model estimate, the available daily range and the sourced precipitation outlook. Exact named sites such as airports use their own public position and timezone. Unresolved or ambiguous destinations request a country, region or coordinates. A temporary public-source failure has one bounded retry. If only the station reading is available, the daily response identifies the missing rain outlook. [First-request recovery](../../output/qa/2026-11-23-global-weather-cold-start/verification.md) · [named-site checks](../../output/qa/2026-11-23-global-weather-sites/verification.md). An explicit lookup leaves the Home preference and location permission in the owner’s control.

Hong Kong uses the Observatory station temperature, the local forecast covering today or tonight, and the official dated daily rows. The tool labels Open-Meteo’s supplementary numbers when the official nine-day feed starts tomorrow. HKO’s significant-rain category remains qualitative. Open-Meteo’s daily probability is the highest hourly probability, and precipitation windows come from the hourly modeled amount. [Weather acceptance](../../output/qa/2026-11-23-global-weather/verification.md).

Saved task titles remain exact. The voice-only tool copy adds `speech_title` with spaced layout separators normalized; dates, fractions and paths remain intact. Shared voice guidance asks for natural language summaries rather than reading slash/dot/formatting. A3 remains selected. Live delegation uses low reasoning effort on the same backend model. Short in-speech zero-PCM pauses are retained, while continuous idle silence still cannot keep a session alive. Playback lead adapts within160–350ms; it does not alter samples, pitch or voice identity.

## Proactive flow

`daily_checkin.py` projects one current cue into the existing workspace snapshot. Only the owner with visible private context sees it; quiet hours and proactivity-off suppress it. Active voice/conversation work hides the compact home cue until the user is free. The shared `AliceCheckIn` is inside the already-measured assistant area on web, phone and device; long text folds into Details.

| Trigger | Behavior | Owner response |
|---|---|---|
| Saved morning/evening time | One dated briefing; late app opening can catch up within that day's window | Got it dismisses the existing nudge and notice |
| Existing task follow-up becomes due | Ask progress, show its saved next step or first unfinished checklist item | Done uses version-checked owner confirmation; Still working records progress; In an hour reschedules |
| Confirmed completion action | Acknowledge the saved result and suggest another existing task or a short pause | Never infer completion from silence, time or camera state |
| Sustained calibrated deviation | One short position cue, followed by reassessment | Quiet for10minutes or adjust; show observed return to reference |
| Existing movement reminder | Suggest a brief movement break using actual observation time | Unknown frames never count as a verified break |

No model is polled for these local cues and no new paid speech is generated automatically. They are visible reminders; autonomous spoken check-ins with A3 are not claimed by this slice. Closing the whole client prevents on-screen presentation until it reopens; the backend retains task/nudge state.

## Camera workflow

In **Posture & feedback**, choose **Use this device's camera** once and grant the browser/OS camera permission. The local choice is scoped to the backend origin. Record the three existing personal reference positions; changing the camera/geometry requires new calibration. Afterward, opening the app or changing pages restores local observation without pressing the chat-camera button. A small home camera indicator allows stopping observation.

Browser capture, model inference and chat image-sharing are separate. `PostureCaptureProvider` lives above navigation. A dedicated worker runs pinned MediaPipe Pose Landmarker Lite on CPU with a640×480preferred stream and roughly4–5observations/second. Only one frame is in flight. Video/audio/frame bytes never go to this endpoint or the model provider; the API receives five head/shoulder landmark coordinates plus quality metadata. No recording is created.

The backend admits an owner-bound4-second lease. Different clients cannot interleave observations; same-client reload replaces its lease and rejects late old frames. Camera/source/boot/session expiry, explicit pause, privacy hide and disconnect remain effective. Browser-source selection disables the Python camera agent's capture and rejects competing agent observations. Local consent does not authorize a different backend after a native server switch.

Desktop tabs can continue while open. Mobile OS background suspension can stop execution; returning creates a fresh stream. This is not an always-running background iOS camera service. Permission revoked/expired, unsupported components or disconnected hardware stop and surface a bounded error rather than repeatedly asking for permission. First physical calibration is a user setup step, not an automatic assumption about healthy posture.

## Build and evidence

Install the pinned frontend dependencies; run `scripts/fetch_models.py pose_lite` from the Python project and `npm run prepare:posture` from frontend before building a camera-enabled release. The helper verifies the existing model SHA and copies local WASM/model assets. Generated binary assets stay ignored; MediaPipe's Apache license is included under public/licenses. No runtime CDN, cloud vision or new Python vision dependency is required for browser inference. Static CSP permits WebAssembly evaluation only, not general unsafe JavaScript evaluation.

The existing calibrated engine/persistence/cooldown/unknown/reassessment baseline remains. Real local-model synthetic-camera flow, reload/navigation/pause and a short physical Mac camera check passed. The physical check returned15uncalibrated valid observations and then closed; it did not record frames. Personal calibration, real-posture accuracy and long-term Pi/mobile performance remain unaccepted. [Current QA](../../output/qa/2026-11-16-alice-daily-presence/verification.md).

### Pi display profile

The dedicated kiosk now uses a separate mode700 `kiosk` browser profile with browser password saving/sync disabled and `password-store=basic`, avoiding a blocking system-keyring initialization prompt in an unattended local display. It must not use a personal browser profile. The previous profile is retained; FYP OAuth grants stay in its own encrypted runtime vault. This is the already-trusted local-device/automatic-owner environment, not a general browser for retaining account passwords. First media permissions remain separate. The autostart pointer must target the active release; physical display readback is required after activation.
