# Group 2 · Shared Alice home

## 8 November: latest reply and readable conversation

The home shows only the newest assistant reply, clearing the previous reply while a new user turn is waiting. Conversation expands into distinct user/assistant messages. Live transcript display uses session-timeline groups, independently of playback completion; late fragments update the original message. History remains bounded RAM with the existing identity/task lifecycle, not a new permanent archive.

The owner explicitly removed recognized-input/“use as Work goal” cards from Conversation. This supersedes the earlier 8 November hide-while-compact workaround below. Actual requested business proposals and their required approval controls remain. Expanded chat uses a dark, nearly opaque surface, contrasting text/bubbles, independently scrolling history and a nonshrinking composer. Optional file activity is reached from the existing menu rather than an always-visible chat link. Short-screen calendar space is reserved only when the compact transcript contains content. [Current QA](../../output/qa/2026-11-08-dialogue-voice/verification.md).

7 November 2026. The owner selected the dark phone visual for Web, phone and Pi, with Alice occupying the main space. The later decisions remove framed calendar/task cards, the white composer and the welcome question. Phone keeps a full month overview, time/date and weather beside a large Alice; it does not replace the month with one line or shrink Alice to make a dashboard.

## Composition and ownership

`AliceScene` renders the existing licensed AliceChan through A1Canvas, its fallback and Plan/More controls. Canvas CSS dimensions match its layout container independently of renderer pixel ratio. `AliceHome` composes Web/Pi; PhoneApp reuses the scene, agenda and conditions while preserving its own navigation and keyboard lifecycle. There is no permanent Web sidebar; the existing navigation opens through More.

`AliceAgenda` presents the existing parent calendar read and WorkspaceContext task snapshot. No additional calendar/task polling exists. Existing private-display, stale-connection and owner-context checks mask content. On phone, the left column has a full month grid, with its own bounded scroll area on shorter screens; it cannot flow into the weather or composer. Selecting the month opens the existing complete calendar.

ConversationWorkspace/AssistantPanel remains mounted across navigation, preserving unsent input, selected discussion, action cards and the existing permission controls. The dark translucent composer retains one camera/microphone entry and one voice entry. Detailed conversation expands on demand. Input height is measured before paint, and compact history is bounded. Background read failures use one concise AssistantRefreshStatus row with read-only Retry, outside the input area. Failed writes keep their existing explicit recovery flow.

## Location and weather

HomeConditions uses the existing workspace preference: automatic, Hong Kong or off. Automatic location first queries browser permission. It never requests permission during ordinary refresh when the result is prompt, denied or unsupported. Existing permission allows one shared location read; an application deadline clears the position watch after five seconds, including a stalled permission dialog. Concurrent updates share one request. A failed attempt records only a failure flag and requires a deliberate click on the location label before retrying. No coordinates are written to browser storage.

Successful coordinates are rounded to 0.1 degree before being sent in a POST body to the same desk. A ten-minute memory cache avoids repeated positioning. Revoked permission prevents cache reuse. A manual location request is consumed once; later refreshes recheck permission and location. If location or nearby weather is unavailable, the display falls back to Hong Kong. The label identifies Nearby or Hong Kong and links to the actual weather source. No synthetic temperature is shown as live weather.

`weather.py` owns fixed HKO/Open-Meteo requests, validation, a bounded shared memory cache, timeouts and fallback. WorkspaceData and HomeConditions reuse this service, rather than starting a second weather backend. The server coarsens coordinates again, does not log them, and uses neither redirects nor an ambient proxy. Existing weather-off preference prevents requests. Permissions-Policy permits same-origin geolocation; browser permission remains required.

## Wake and voice

[OpenAI/Alice](openai-alice-wake.md) defines the local wake and GPT Live lifecycle. The switch means local waiting for Alice, not a continuously connected paid Live session. One shared server lock protects wake/cloud capture ownership across tabs. Another window's capture is shown explicitly instead of spawning a competing connection. Initial microphone permission and deliberate opt-in remain necessary.

## Evidence and remaining limits

[This round's QA](../../output/qa/2026-11-07-alice-home-wake/verification.md) separates local regression checks, browser rendering and recovery, the capped synthetic real-provider trial and Pi deployment. Native-phone background listening, human acoustic interruption/AEC and physical Pi microphone/speaker acceptance are not established by a rendered page. Camera preview remains local; GPT Live in this release supports voice, while typed chat uses the normal Responses path and Realtime remains the explicit image-capable comparison option.


7 November wake repair: the Camera & microphone panel now has one explicit input selector shared by its local meter, local Alice detector and voice client. Re-enabling wake clears the stale voice failure notice. Full-catalog startup and browser playback/idle recovery are verified in the [repair QA](../../output/qa/2026-11-07-alice-wake-repair/verification.md); a waiting label alone is not end-to-end acceptance.

Historical 8 November workaround, superseded by the owner decision above: optional recognized-input/voice-to-Work details stay mounted but hidden on the compact home and appear when Conversation expands. This preserves in-progress review state without covering Alice/calendar during ordinary speech. Offline browser show/hide/content-retention checks passed; no extra model call.
