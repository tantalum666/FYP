# Independent voice-to-Work backend authority audit

Date: 13 October 2026. Scope: the ongoing voice continuity slice, supplementing the inherited 186-file intake. The audit changed only this QA directory, not implementation, maintained tests, Git refs, user runtime, or assets. Synthetic provider events, in-process fake sockets and isolated SQLite/files only; no live provider, credentials, microphone, network, hardware or UI acceptance claim.

## Findings and disposition

1. **Terminal cleanup regression, fixed and independently rechecked.** The initial `VoiceService.run` finally block called the new database-dependent ledger `end` before stopping dispatcher acceptance or releasing the active voice slot. Injecting a SQLite operational failure there stranded `active=True` and skipped socket cleanup. The implementation now makes ledger end in-memory-only and protects transport cleanup against unexpected ledger failures. The independent test still forces `end` itself to fail and confirms active-slot release and socket closure. Before evidence: `cleanup-failure-before.txt`.
2. **Wall-clock rollback extended transient retention, fixed and independently rechecked.** A one-hour wall-clock rollback with 301 monotonic seconds elapsed retained the frozen transcript under the initial wall-clock-only expiry. Drafts now carry an internal monotonic deadline and expire on either deadline; retry does not refresh expiry. The public expiry timestamp remains human-readable metadata. Before evidence: `ttl-surrogate-before.txt`.
3. **Malformed UTF-8 mutated state before failing, fixed and independently rechecked.** Appending an unpaired surrogate raised `UnicodeEncodeError` after advancing the sequence and removing the prior segment. Text and correlation keys are now checked before mutation; malformed input leaves prior sequence/segments intact. Qwen also validates transcript before computing its fallback digest or advancing the adapter sequence. Before evidence: `ttl-surrogate-before.txt`.
4. **Previously identified admission TOCTOU and nonboolean retention, independently rechecked.** Hiding private content after run preflight but before the write transaction rejects creation with no run, origin claim or receipt retained. `retain` rejects numeric 1, floating 1.0, strings, false and null; actual boolean true remains required.

No unresolved blocker was found in the audited boundaries after these fixes. This is a bounded software review, not proof against every race or proof of live speech/model quality.

## Independent acceptance

`test_independent_authority.py` contains 20 passing cases, recorded in `pytest-independent-final.txt`:

- Committed same-operation recovery after draft expiry and process restart, changed-operation payload conflict, and second-operation rejection
- Concurrent different-operation submissions claim one draft once; a forced precommit save failure rolls back run, receipt and origin claim, allowing a safe same-operation retry
- Server-issued segment identity, immutable frozen text, final dedupe, contradictory-final invalidation and stale sequence rejection
- Eight-segment and 32 KiB UTF-8 ceilings; oversize content never becomes a selectable tail
- Real session requirement, forged/paired/agent denial, cross-session denial and provider-model change invalidation
- Gemini remains unfinalized across assistant completion; no inference of speaker identity or authorization
- Raw selected and unselected transcript markers absent from durable fixture files before retention; only the deliberately edited reviewed goal is retained after creation
- No origin metadata, raw selected input or voice-provider metadata in the Work planner payload
- Draft TTL, no retry extension, exact expiry rejection without typed fallback, monotonic rollback bound, and voice-end independence from a queued retained run
- Strict retention/provenance schema, privacy admission fence, and terminal cleanup under forced ledger failure

The initial `pytest-initial.txt` includes one audit-fixture mismatch: it attempted a second active ledger after implementation gained the intended single-session bound. That was corrected in the audit fixture; it was not an implementation defect.

## Lock and authority review

- Creation uses run lock → personal-context lock → ledger lock → SQLite write transaction. Privacy mutation paths use personal-context → SQLite and do not enter the run/ledger lock.
- `Store.operation` calls `guard_operation` with its existing transaction. Its `publication_checkpoint` and `AgentContextBridge.validate(conn=...)` do not acquire the run, personal-context or ledger lock. This avoids a SQLite-write → personal-context reversal. No real reversed edge was found, so no speculative deadlock probe was introduced.
- Scope reread under admission uses local source/catalog reads, configured connector metadata and browser readiness checks. The reviewed path performs no discovery, provider call or network I/O while admission locks are held.
- Ledger observe/freeze are server-owned code paths. The HTTP freeze schema accepts only the voice session reference, segment ID and expected revision and uses the real cookie; provider tools cannot register a callback, provide origin metadata, retain work or approve it.
- Durable origin claims store a reference hash and request/run identifiers. Run data stores the reviewed goal and minimal server-derived provenance, not the draft reference, raw transcript, neighboring speech, audio or cookie. The atomic transaction rolls back the claim if run persistence fails.
- Receipt lookup precedes transient draft resolution, under current owner/private read authority. A committed creation survives draft expiry or restart without paying for a new voice/model session. A new creation still requires a valid same-owner/privacy/config-bound draft.
- Voice terminal cleanup does not control the retained run lifecycle. Runtime's added periodic ledger cleanup is last in the existing tick, and the ledger owns no network calls.

## Evidence and limits

The focused maintained regression command covers `test_voice_work.py`, `test_voice_context.py`, `test_voice_google.py`, `test_tool_dispatch.py`, and `test_agent_runs.py`; final output and source hashes are stored alongside this report. Existing paired voice/tool behavior, tool cancellation and physical-stop priority remain covered by those inherited suites. Exact final count and hash stability are recorded in the final result below.

This audit did not change root product/handoff/decision/work logs; the parent owns those coordinated updates. Frontend mounted interaction, live provider transport, real microphone/speaker attribution, hardware, user UI acceptance, wider aggregate CI and publication remain separately evidenced stages.

## Final result

At 07:01 UTC, 20 independent audit tests passed and 126 maintained backend voice/run/tool regression tests passed. One existing FastAPI/TestClient deprecation warning was reported. Five audited implementation file hashes (`voice_work.py`, `voice.py`, `agent_run_schemas.py`, `agent_runs.py`, `runtime.py`) were identical before and after the final regression run; see `source-hashes-before.txt` and `source-hashes-after.txt`. No Git mutation occurred.

Capture/freeze use a read snapshot and may linearize before a concurrent global hide/signout that does not take the personal-context lock. A response can therefore arrive later than that independent action; frontend epoch fencing remains necessary. This was reviewed and is not reported as an admission escape: no stale new run passes the final write-transaction fence. Adding write transactions per input chunk would add contention and would not eliminate the post-commit/pre-delivery interval.
