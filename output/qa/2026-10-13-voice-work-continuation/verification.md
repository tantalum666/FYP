# Voice-to-Work frozen integration verification

Completed 2026-10-13 07:11 UTC in the authorized cloud workspace. Baseline source is `fd4be86fc55a72ebba252b12dcec01b6ad55f6b9`; its 46 blobs/ref and both exact CI runs passed. This voice record precedes voice publication; actual browser/live audio and remote CI are separate stages.

## Implemented

Owner selects a server-observed bounded voice input, reviews/edits it, then explicitly ends voice and opens the existing Work composer. No speech event, provider tool, partial ASR, assistant answer or interruption creates work or grants scope. Voice origin defaults to deterministic compilation; typed-chat defaults are preserved. Sources, retention, destination sharing and effects remain explicit. The server binds snapshot identity to actual session/privacy/provider state and uses one durable reference claim in atomic run admission. Only final reviewed goal and minimal origin metadata are retained.

Original same-operation receipts recover committed work after volatile draft expiry/restart. New expired refs never silently fall back to typed work. Five-minute volatile retention uses both wall and monotonic deadlines, bounded text and draft counts; disconnect clears unselected text. Closing speech does not cancel independently retained work. Automatic barge-in clears old playback and permits the next response; only explicit owner Stop speaking latches mute. Audio capture/playback and all async continuations check the current identity/privacy scope.

## Full frozen command and result

`UV_CACHE_DIR=/workspace/shared/fyp-uv-cache npm_config_cache=/workspace/shared/fyp-npm-cache bash desk-companion/scripts/check_software.sh`

- Original bundled A1 and licensed VRM hashes: passed
- Ruff backend/scripts/tests: passed
- Entire maintained backend suite: **791 passed**, 229.61 seconds
- Entire maintained frontend suite: **169 passed**
- TypeScript and Vite production build: passed
- **245 source/test/config/lock hashes unchanged** through the run

See [full log](release-software-checks.log), [stability record](release-source-stability.json), before/after manifests. Existing Starlette/httpx deprecation, unrelated pytest empty-regex, inherited npm http-proxy configuration warning and Vite large-chunk advisory remain; no failed stage.

Focused backend: [170 passed, including 44 new bridge tests](../2026-10-13-voice-work-backend/verification.md). Frontend: [169 tests/type/build](../2026-10-13-voice-work-interface/verification.md). Independent authority review: [20 probes plus 126 inherited regressions](../2026-10-13-voice-work-authority-audit/verification.md). Independent UI/audio review: [32 production hook/callback/reducer cases and 13 audio-function scenarios](../2026-10-13-voice-goal-ui-audit/verification.md).

## Reproduced faults corrected

- Existing run-create privacy/scope preflight-to-commit gap and numeric1 accepted as retention
- Ledger teardown error stranding voice active slot/socket
- Wall-clock rollback extending frozen plaintext lifetime
- Malformed UTF-8 advancing sequence/removing prior input before rejection
- Unicode character-count mismatch, expired queued goals and stale-owner callback dispatch
- Playback/capture proceeding before UI effect cleanup, session-denial stale content and active-state handling
- Automatic barge-in inadvertently requiring manual unmute every turn

Each was represented by maintained or independent negative tests and rechecked; no remaining blocker was reported within audited boundaries. This is not a claim against every race or every browser implementation.

## Limits and handoff

Only synthetic provider/WebSocket/audio objects, deterministic hooks/callbacks/SSR, real isolated SQLite and actual local artifact bytes were used. No actual microphone, voice recognition, speaker identity, paid service, live provider quality, deployed app, external account or hardware was accepted. A fake completed Qwen input is not evidence that a real person spoke it; Gemini snapshots remain unfinalized.

The isolated Mac task currently tests source4e50841, with one platform approval pending and an empty React root under investigation before mounted scenarios. It has not accepted this voice batch or the previous search UI. No security bypass, original8832 restart or inferred user cancellation. Runtime cleanup is the only parent integration change; no new worker or dependency was added here.

Next selected-task change watches are still design/read-only preparation and excluded from this frozen source. They will be implemented after this payload is preserved. The broader request continues, without claiming dot/Muse/Grok Bot parity.

Root product/README/architecture/decision/handoff/work-log and focused voice design/contract are synchronized; all relative links are checked before publication, excluding the intentional generated-runtime credential reference which must never be uploaded. The inherited186-document intake and focused worker reading supplements remain valid.
