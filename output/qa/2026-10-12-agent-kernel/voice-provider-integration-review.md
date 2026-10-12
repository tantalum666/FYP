# Provider and voice context verification

12 October 2026 UTC. Base: `50e174f50a4130b3c666f836f666f6aa4cde4b32`. This covers the provider/voice worker’s changes and an independent bounded-executor review. Final commit/publication and integrated browser checks belong to the parent checkpoint.

## Delivered

- Exact provider/channel/host/path policy; malformed URLs, model identifiers and credential headers fail closed
- HTTP/WebSocket redirects and implicit environment proxies disabled; connection-time voice validation; no paid fallback or automatic reconnect
- Owner-only, explicitly approved, destination-bound bounded memory projection in initial voice instructions, encoded as untrusted JSON data
- No voice memory-mutation tools; no automatic voice transcript retention or saved text history in voice
- Task/calendar/computer-job tool advertisement and invocation require owner-only business-context permission for that exact voice destination; paired and agent principals cannot export these saved records
- Context/privacy/destination revision pinned to the voice session. Changes, including an off/on consent transition, stop subsequent provider sends, provider event delivery and pending tool delivery; the idle watchdog checks every second. Session revocation also fences owner sends/events. A new session is required; no automatic reconnect
- Already-transmitted context cannot be recalled. Stopping prevents subsequent use but does not establish provider-side deletion. An in-flight send can precede observation of a change
- Immediate physical-output stop remains independent; memory edits and business writes still require the existing owner review/confirmation flows

Owned implementation files are in `provider-voice-owned-files.json`. The M0 changes to `text_ai.py` were released before its context-worker integration and are not exclusively owned by this worker. The frontend worker owns the translated `VOICE_CONTEXT_CHANGED` message.

## Actual checks

- M0: 115 focused tests and 232 then-current full backend tests passed; historical log/result retained separately
- Voice/provider integration: 123 focused cases passed, including owner/default/unapproved/hidden/paired/agent contexts; JSON escaping; absent/invented memory tools; business-tool consent; changed memory/consent/destination; idle and next-turn fences; and off/on consent transitions
- Final integrated backend rerun: **358 tests passed**, one upstream Starlette/httpx deprecation warning, 43.86 seconds (`voice-integration-full-backend-tests.txt`)
- Changed-file Ruff passed. No paid provider request, real credential setup, real microphone capture, hardware action or user-computer access was used

## Independent application-executor review

Read all of `application_executor.py`, `executor_registry.py`, `demo_application.py`, `jobs.py`, `test_application_jobs.py`, and the standalone check script. Reviewed the final owner/private-hidden route supplement. No release-blocking defect found within the explicitly fictional-data, single-host loopback demonstration scope.

Independent rerun: **86 tests passed** (`application-review-tests.txt`), including the original 34 note cases and the application/hidden-private regressions. Independently ran `check_application_executor.py` on test-owned port18843: separate HTTP process, zero application records before approval, one independently read SQLite record afterward, exact content/title/intent/instance verification, no duplicate after retrying preparation, owned process stopped and temporary data removed (`application-independent-http.json`).

This proves an application API effect, not GUI/browser/desktop control. The demo’s Host/Origin/header checks are not authentication against malicious same-host processes. The target remains loopback-only and fictional-data only. Unknown dispatched outcomes are never automatically retried; read-only reconciliation can establish a late success without claiming rollback. These limitations are accurately disclosed in the executor documentation.
