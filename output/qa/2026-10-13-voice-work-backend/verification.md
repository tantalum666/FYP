# Voice-to-Work backend verification

Date: 13 October 2026. Scope: the same continuous FYP implementation task, inheriting the parent 186-file full Markdown intake. This is backend protocol-fake/local-data evidence; not microphone, live model, UI browser, paid-provider or hardware acceptance.

## Implemented

- New transient `VoiceWorkLedger` and strict owner freeze request in `backend/desk/voice_work.py`
- Adapter-owned input normalization, server session/segment/revision identity, exact owner/privacy/provider/model/destination binding, bounded immutable selected snapshots
- Owner-cookie HTTP freeze route; no provider tool start/approval/retention/control surface
- Optional strict voice reference in `RunCreate`, boolean-only retention, minimal server-derived origin metadata, hash-only durable one-run-per-draft claim
- Existing committed create receipt lookup precedes ephemeral resolution; an original lost-response retry recovers after expiry/restart. Another operation cannot duplicate the same draft
- Transaction-bound final session/private/scope/context admission, no silent typed fallback, no original/unselected/assistant transcript persistence
- Voice disconnect preserves independent retained work; failure-safe memory-only ledger teardown, dual-clock expiration, UTF-8 refusal before state mutation

The implementation contract is [voice-work.md](../../../desk-companion/docs/voice-work.md). Parent owns Runtime's existing-tick cleanup hook and root documentation/Git; frontend and independent boundary audits are separate workers/artifacts. No source/test/config changes were made before the parent explicitly released the frozen search batch at 06:46 UTC.

## Regression first

Before changing admission source, `test_creation_rechecks_privacy_after_preflight_before_commit` changed hide-private immediately after the existing preflight authorization. The old create implementation wrongly saved the run and receipt and failed the expected rejection. Numeric `retain=1` also passed the old `Literal[True]`; the negative test failed. String `"true"` already failed validation. The narrow final transaction fence and actual-boolean validator make both retained regressions pass.

An independent reviewer additionally reproduced:

1. An exception from newly added ledger teardown stranded the voice slot/socket by bypassing cleanup
2. A one-hour backward wall-clock change extended plaintext retention past five real minutes
3. An unpaired UTF-8 surrogate advanced sequence/removed the previous segment before failing encoding

All three were fixed and corresponding maintained tests added. Independent reviewer reported 20/20 authority/TTL/claim/rollback/cleanup probes passing after fixes. See [independent audit](../2026-10-13-voice-work-authority-audit/verification.md) for its exact files and evidence.

## Final focused checks

From `desk-companion/`:

`./.venv/bin/pytest tests/test_voice_work.py tests/test_voice_context.py tests/test_voice_google.py tests/test_tool_dispatch.py tests/test_agent_runs.py tests/test_agent_context.py tests/test_agent_personal_context_integration.py -q`

Result: **170 passed**, one existing FastAPI/Starlette TestClient deprecation warning, 54.98 seconds. [Captured output](focused-tests.txt). This includes **44 new maintained bridge cases** covering actual fake-socket interruption/end, standalone fake protocol events, SQLite exclusion/recovery, real artifact readback, scripted provider-payload isolation, malformed input, limits and negative owner/session/config/privacy routes.

`./.venv/bin/ruff check backend/desk/voice_work.py backend/desk/voice.py backend/desk/agent_runs.py backend/desk/agent_run_schemas.py tests/test_voice_work.py`

Result: all checks passed. [Captured output](ruff.txt).

The earlier 166-case pre-final run is superseded by this final 170-case run. Aggregate full-repository validation belongs to the parent's subsequent source freeze, not this focused report.

## Current boundaries

Capture/freeze may linearize at a short read snapshot just before a concurrent hide/sign-out. Frontend private epoch fences prevent a stale returned payload from repopulating the current private view; new retained admission always rechecks under an immediate SQLite transaction. No write transaction is held across provider/network I/O. An immutable acknowledged draft is not a verified speaker, authority, selected evidence or effect approval.

Run outputs use the existing structural byte/source/effect checks. The deterministic test does not mean a model understood speech. Scripted planning does not measure real semantic quality. No microphone, credentials, external grants, paid call, account, hardware, deployment or Git write was used by this worker. Existing A1/DeviceApp art, school files and physical-output/proposal-cleanup boundaries remain outside this change.

Reading evidence: [focused reading](focused-reading.json). Owned file hashes/byte counts: [manifest](owned-manifest.json). The manifest excludes this verification and parent-owned Runtime/root/UI files; root's aggregate manifest captures the complete integrated revision.
