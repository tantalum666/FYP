# Independent voice-to-Work UI lifecycle audit

Date: 2026-10-13. Status: current deterministic checks pass; mounted-browser and live-audio acceptance remain outstanding. Group 2 continuation of the existing full project intake, with focused rereading recorded in `reading.json`.

## Executed evidence

- `audit.mjs` / `independent-results.json`: **32 passing independent scenarios**, executing production reducers, VoiceWorkPanel / RunComposer / RunWorkspace / AssistantPanel component functions and callbacks with deterministic hook slots, plus the actual PrivateWriteQueue. Imports, network and nested visual components are mocked; these are hook/callback tests, not React DOM mounts
- `audio-audit.mjs` / `audio-results.json`: **13 passing independent scenarios** executing the actual VoiceAudio implementation with fake AudioContext, capture, WebSocket and deferred promises. No real microphone, audio stream, provider, network or physical output
- `repository-focused-tests.log`: **37/37 checked-in tests pass**, covering voice input/review/audio, run refresh lifecycle and existing search tests
- `source-manifest.json` identifies exact reviewed source bytes. This cloud materialization has no local Git metadata; no new SHA, publication, CI or browser acceptance is inferred

Run the independent scripts from the repository root with Node; they use the already installed frontend TypeScript dependency. The checked-in test command is recorded in its log scope and uses Node's experimental TypeScript strip flag.

## Findings and independent fix verification

1. Voice input allowed 4,000 Unicode codepoints while Work rejected more than 4,000 UTF-16 units. A 2,001-emoji goal could end voice then disappear. Validation now agrees; explicit fixture passes
2. Expired queued voice goals were accepted without TTL validation. Pending/initial goal validation and confirmation-time expiry now reject them with feedback while preserving an unrelated dirty draft. No implicit typed fallback
3. Audio playback and capture ran before the UI's event callback privacy check. Transport-level current-generation checks now stop capture, playback, socket-open/ticket and deferred microphone/setup continuations before effects, including the interval before React effect cleanup
4. Saved old-owner Start and input-selection callbacks captured a newly valid epoch and could dispatch old private goal/references. Mount-bound checks now reject them before dispatch. Both exact old-handler reproductions pass
5. Odd-length PCM or invalid base64 threw inside a socket callback. Validation now closes resources and emits an error without subsequently emitting the original ordinary audio event; odd/base64/oversized cases pass
6. Backend RUN_SESSION_EXPIRED was missing from fatal freeze invalidation. It and the other auth/privacy denial cases now clear pending private retry state and invalidate immediately
7. Root identified automatic Qwen speech-start interruption incorrectly latching owner mute. Independently verified the corrected distinction: ordinary provider interruption clears queued playback and permits the next response; explicit owner Stop speaking remains latched through provider interruption, turn completion and input events
8. Worker identified and corrected an event-state brace regression during its own final check. Independent Assistant callbacks confirm ready/audio/transcript/interrupted/turn-complete keep voice active, and only actual end/error closes the active state

## Covered continuity and authority boundaries

- No assistant/tool/raw partial/finality event automatically selects a snapshot, freezes, retains or starts Work; only the explicit owner selection callback requests the exact observed segment/revision
- Frozen review text remains unchanged by later transcript revisions; edits and provenance move together; origin metadata excludes duplicate transcript text
- Freeze failure does not end voice; retry uses the exact selection. Reviewed handoff ends the voice engine without sending Work cancel/pause or physical-stop commands
- Dirty Work draft keeps its content until explicit discard; queued goal provenance survives replacement; expired confirmation cannot erase the unrelated draft
- Voice defaults to deterministic; ordinary typed goal keeps its existing model default. Evidence, memories, saved conversation, provider destination sharing, retention and mutation permission start unselected
- Unknown create recovery retains the same operation ID, serialized reviewed goal and origin; no new input silently changes that retry
- Transient refresh keeps composer content mounted and disables dispatch; existing search navigation guards stay intact
- Owner/session/privacy/offline/provider changes fence late freeze responses, old callbacks, existing speech transports and queued goals before cleanup effects. Same-turn duplicate Start cannot create two microphone engines
- Speech mute, voice close, Work controls and physical-output controls remain separate. Fake audio teardown closes tracks/context/socket and rejects old socket callbacks

## Boundaries and remaining acceptance

No DOM/browser layout, focus, keyboard, narrow-screen, real permission prompt, real audio/provider quality, hardware, full backend admission or live model acceptance is claimed here. The ordinary modal/focus implementation was inspected but not mounted. Backend atomic admission, durable receipt/file readback and plaintext exclusion belong to the separate backend audit. Parent owns aggregate check/build, root documentation and any Git publication.

No source, dependencies, assets, existing user data, original preview or Git state was edited by this auditor. Only this QA directory was written. Latest focused checks have no remaining audit blocker; changes after `source-manifest.json` require affected rechecks.
