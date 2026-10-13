# One exact public URL capture

Implemented as an off-default experimental application capability, 13 October
2026. Offline fixture checks are evidence for local software behavior, not live
public-DNS/TLS acceptance, rendered-page completeness, actual mounted UI, saved
browser downloads or model quality. The [implementation proposal](../../planning/2026-10-13/exact-url-capture-implementation.md)
and [independent seam review](../../output/qa/2026-10-13-exact-url-plan-review/review.md)
provide the selected boundaries. Schema migration is separately controlled; this
feature does not upgrade an actual runtime database during initialization.

## Owner workflow and retention

1. The owner enters one exact credential-free public HTTPS URL and an optional
   local label, explicitly acknowledging indefinite local review-record retention
2. Prepare validates syntax and local authority/capacity only. It does not perform
   DNS, connect, HEAD, GET, preview, favicon or any other network activity
3. The returned immutable review names the exact destination, generated text
   filename, disclosure, strict GET/extraction policy and current advisory usage
4. Approval binds the exact review/version/hash, original unexpired owner session,
   privacy/settings revision, public-only assertion and local snapshot retention
5. One bounded worker may perform one GET. The retained extraction is inspected
   through the existing plain-text source preview and explicitly selected in Work

No capture starts Work, selects a source, grants provider sharing, calls a model,
searches, follows links, executes instructions, authenticates, retries a request,
follows redirects, renders JavaScript or contacts another destination. Remote
text and embedded claims of approval remain untrusted data. A fresh capture of
the same URL is a distinct approval and another possible retained source.

Review, cancellation, failure and unknown states all consume one of 200 lifetime
capture identities. There are at most 600 operation receipts: one successful
prepare, approve and cancel per capture. Sources retain the existing 100-source,
64-MiB aggregate and 1-MiB per-source limits. Unknown reservations count. Neither
cancellation nor reconciliation deletes bytes, frees a slot or proves that the
website received nothing. This slice has no source or capture deletion control.

## API and response privacy

All routes require an actual owner session; paired/display identities do not
substitute for that session. Existing same-origin and `X-Desk-Request: 1` controls
apply, and every mutation takes an original `X-Operation-Id` of 1–100 non-whitespace printable ASCII characters.
The prefix is `/api/public-research`:

- `GET /capabilities`: enabled flag, history limit 200, `source_cleanup:false`
- `POST /captures`: `{url,label?,retain_capture_record:true}`; returns
  `{capture,operation_id,review}`
- `GET /captures?limit=20&cursor=...&metadata_only=false`: `{captures,next_cursor}`;
  at most 50 records per page, stable opaque-ID cursor, no URL query parameter
- `GET /captures/{id}?metadata_only=false`: `{capture}`; a retained review state
  also includes its current code-owned `review` so it can be reopened
- `POST /captures/{id}/approve`: `{expected_version,intent_hash,public_only:true,
  retain_snapshot:true}`; 202 with the current capture
- `POST /captures/{id}/cancel`: `{expected_version}`; always returns the safe
  metadata-only capture, including for a visible owner
- `POST /captures/{id}/reconcile`: `{expected_version}`; returns the current
  capture and `verification:source_verified|source_unknown|no_final_source`

Strict input models reject extra fields and numeric/boolean coercion. A same-key,
same-kind, same-target and same-payload retry returns the original capture's
current state. A collision is rejected before any unrelated target lookup or
new admission. Different-key repeats of an effected approve/cancel transition
are read-only no-ops, not new receipts. Reconcile performs local readback and has
no accumulating receipt journal, but cannot reuse a retained mutation key.

Visible captures include URL, label, generated display name, intent digest,
source ID/status and acquisition. Hidden metadata includes only opaque handle,
lifecycle state/version, timestamps, dispatch possibility, safe error code and
cancel availability. Hidden reads and stop select bounded scalar columns and
never deserialize private intent/acquisition JSON. Corrupt private JSON therefore
does not remove the ability to stop a known valid control record. Invalid control
identity, generation, receipt or timestamp fails closed.

Private list/detail/reconcile responses capture the current request's real owner
session and privacy/settings revision, then recheck after projection and any file
I/O. An old worker's approval is never used as read authority. Logout, expiration,
hide→show or settings changes invalidate an in-flight response. A newly signed-in
owner can inspect retained records but cannot inherit an old execution approval.
Metadata listing is last-recorded status, not fresh byte verification.

## Durable lifecycle and worker boundaries

`PublicCaptureService(runtime, enabled=False, client=None, monotonic=...)` does
not start a worker or network request. Construction invalidates old review and
active authority without replay. `start()` explicitly creates one daemon worker;
`run_one()` supports deterministic offline checks. `stop(timeout=1)` sets an
in-memory stop fence, revokes durable active claims, wakes and boundedly joins.
A failed database revocation is reported; wake/join still runs. An unexpected
worker-control failure disables new capture admission rather than automatically
retrying an uncertain operation. The physical worker slot is shared across
service instances, preventing replacement while an old call remains blocked.

Approval has a five-minute wall/monotonic review deadline. Backward wall time,
restart, a changed privacy revision or another session cannot revive it. The
worker has a sixty-second execution ceiling; transport receives at most twenty
seconds and uses bounded blocking phases. Checkpoints fence owner, privacy,
claim, generation, policy/intent identity and deadlines before network phases,
during extraction, at source reservation/final link and before verification commit.
No in-process timeout claims it can kill a blocked operating-system call.

The dispatch transaction records that the one request **may** have been sent,
then transport checks authority again before issuing GET. DNS/TLS may already
have disclosed connection metadata. The marker is not a network receipt: a crash
immediately after it can leave zero actual GETs and an unknown outcome. Later
cancellation cannot recall already emitted packets. There is no automatic replay,
restart resume, alternative-address attempt, proxy or browser fallback.

Capture tables are part of schema 3 and must already be valid even while the
capability is disabled. Store owns validation, fresh initialization and the
separately named explicit offline 2→3 migration gate. Runtime construction never
creates missing capture tables or repairs lost once-only barriers. See the
operator's migration instructions for stopping, verified backup and old-binary
exclusion. No real user-store migration was performed for this implementation.

## Immutable extraction provenance and source publication

The network/extractor code owns MIME/framing, strict UTF-8 and static extraction
limits. Output is plain `.txt`, at most 24 KiB, with deterministic LF logical lines
at most 1,024 UTF-8 bytes including LF. Full raw response bytes are held only in
bounded worker memory and never saved. Static extraction can differ from the
rendered page; CSS-hidden/generated/paywalled coverage is not guaranteed.

Each source has `provenance_kind:public_web_snapshot`, capture ID, exact URL,
policy version and a nested `acquisition` object containing:

- Capture ID, exact URL, UTC received time, HTTP 200 and generated total line count
- Admitted response MIME, UTF-8 charset, raw SHA-256/count and extracted SHA-256/count
- `extractor_version:static_text_v1`, `coverage:complete_accepted_static_extraction`
- `raw_retained:false` and `rendered_coverage:unknown`

No remote filename, server timestamp, arbitrary header or cookie becomes trusted
provenance. The generated display name is `capture-<capture-id>.txt`; it is not a
host path. A digest is an acquisition integrity receipt, not an authenticity or
factual-accuracy claim. Existing selection and provider-sharing gates remain.

The source key is exactly `capture:<capture-id>:source:v1`. Acquisition is durably
saved before calling the existing `ImmutableFiles.put` pipeline; the returned
source ID is associated afterward. Checkpoints never pretend to know a newly
allocated file ID. Exact-key lookup validates SQL identity, bounded metadata,
complete canonical request digest and expected capture/acquisition fields. Both
the actual and expected canonical digests are checked, preventing `true == 1`
from making different metadata appear identical.

Source admission uses the existing transaction and corruption-aware source-only
scalar accounting. Only a fresh reservation adds prospective count/bytes. Final
link and original-key recovery do not double-charge an already counted row.
Original recovery, hidden stop and exact local reconciliation remain usable at
full capacity or with unrelated corrupt accounting; an invalid exact reservation
still fails closed. A racing upload can consume capacity after GET and before
publication, yielding a clear capacity failure without a fabricated source.

The shared writer retains its file/directory fsync, no-follow, inode, owner,
permission, size, hash and single-link checks. Readback/status commit now accepts
the existing trusted checkpoint, so cancellation after linking but before final
verification does not silently promote source status. Existing callers without a
checkpoint retain their ordinary behavior.

## Recovery distinctions

- No reservation: reconcile reports `no_final_source`; it never runs extraction
  or ingest to manufacture the missing source
- Reservation/temporary only: source remains unknown and counted; no rename,
  linking, repair or temporary cleanup is performed by reconcile
- Final plus pending with link count two: remains unknown, even when bytes match;
  reconcile does not unlink either name
- Exact final single-link bytes after pending unlink: local readback may establish
  file/directory durability and verify the original source
- Cancellation after final link: retain the cancelled lifecycle independently;
  only a separately requested current-owner readback may establish verification
- Corrupt identity, request hash, provenance, acquisition or required receipt:
  fail closed; never adopt by URL/hash similarity or make another request

The lifecycle can remain unknown/cancelled while its original source is separately
verified. This is intentional: source verification does not replay or rewrite the
history of an interrupted capture.

## Offline evidence and open acceptance

`tests/test_public_captures.py` covers lifetime bounds, same/different-key repeats,
concurrent approval, original collision ordering, owner/epoch/deadline/restart,
hidden corrupt metadata, post-I/O privacy, stopped/blocked workers, source quota
races and exact recovery. Real temporary file tests include reservation, temporary,
link-count-two, post-link cancellation and verification-commit races.

A controlled loopback HTTP fixture injects only the test connection seam into the
production capture client. It independently records one GET, target and headers,
checks exact extraction/raw hashes, explicitly selects the source in ordinary
deterministic Work, then downloads and hashes both real generated artifacts.
It does not weaken production DNS admission, perform public HTTPS or prove real
website/TLS acceptance. Transport/policy/schema suites and an independent
lifecycle audit cover their own failure matrices. Current test commands and
counts are recorded in the [lifecycle QA](../../output/qa/2026-10-13-public-capture-lifecycle/verification.md).
