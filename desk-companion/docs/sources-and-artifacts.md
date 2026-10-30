# Selected sources and immutable artifacts

31 October 2026 integration: read [current compatibility and migration rules](pr5-integration.md) first. Dated October 12–13 acceptance statements below remain historical; this integration preserves Alice/current Omni and the current task/job/permission core.
Implemented local infrastructure for owner-selected TXT, Markdown, CSV and JSON
snapshots, and actual generated report files. This service does not browse,
execute code, call a model, send external messages or upload selected files to a
provider. A source selection is not provider-sharing consent. The run coordinator
owns explicit source/destination grants and checks those before transmission.

## Authorization and retention

Every service boundary accepts the persisted SHA-256 reference to a real owner
session (`session_hash`). It checks the existing sessions table, expiry and Hide
private. A fabricated owner dictionary or unknown hash is not authority. Routes
also use the application's owner dependency. Session cookies are not stored in
source/artifact records; only a validated hash is passed internally by the run
coordinator. Private-hide, expiry or sign-out blocks reads and new publication.
Run-origin publication additionally validates generation, session, privacy and selected personal-context bindings at reservation and in a short SQLite write transaction at the final link point. If that fence rejects publication, this invocation attempts to remove only its own unpublished temporary body. Cleanup failure and earlier crashes may leave bytes; existing final artifacts remain separately retained. No rollback, forensic erasure or provider recall is promised.

Selecting/importing a source explicitly persists a private snapshot. Creating an
artifact persists a separate private result. There is no delete/forget endpoint
in this slice and no automatic cleanup. Unknown reservations count toward
capacity and are never silently purged. This does not claim forensic erasure,
provider recall or retention behavior that has not been implemented. UI must
explain persistence and mask cached content when hidden/offline/stale/signed out.

## Source ingestion and line coverage

`SourceService(runtime)` is exposed as `runtime.sources`.

- UTF-8 only, nonempty text, no NUL, at most 1 MiB per source
- Formats: `text`, `markdown`, `csv`, `json`; matching `.txt`, `.md`/`.markdown`,
  `.csv` or `.json` filename suffix required; paths/control characters rejected
- The display filename is metadata only, never a filesystem path
- Every logical line must fit 12 KiB in UTF-8; very long minified files must first
  be split/formatted by their owner, not silently truncated by ingestion
- CSV requires unique nonblank headers, 1–40 columns, consistent row lengths,
  and at most 10,000 data rows; source cells remain unchanged as untrusted data
- JSON rejects malformed/duplicate object keys, nonfinite values, depth over 12
  and more than 20,000 nodes
- 100 retained source reservations and 64 MiB total per desk; the run coordinator
  additionally limits a selection to 12 sources and 4 MiB
- Original accepted bytes are preserved exactly; SHA-256 is over those bytes

Sources get generated opaque IDs, revision 1, acquisition timestamp, byte count,
MIME, line count, hash and status. `untrusted=true` means their text is data,
including any instructions inside it. Source metadata explicitly reports
`provider_sharing=not_granted_by_selection`.

Internal API:

- `ingest(SourceInput(name,format), body:bytes, key, *, session_hash)` returns
  `{source, operation_id}`
- `listing(*, session_hash, limit=50, cursor=None)` returns sources, next cursor
  and limits; maximum page size 100
- `metadata(id, *, session_hash)` verifies the current exact stored bytes before
  returning metadata; a missing/corrupt source remains `unknown`
- `read(id, *, session_hash, selected_ids, start_line=1, max_lines=200,
  max_bytes=12288, coverage_id=None)` returns metadata plus content,
  start/end lines, total lines, `truncated` and `reader=source_read`
- `read_all(id, *, session_hash, selected_ids, coverage_id=None)` returns the
  full bounded source for a deterministic local parser, labelled
  `reader=local_parser`, `provider_ready=false`
- `from_artifact(id,key,*,session_hash)` snapshots a verified existing artifact
  as a selected source without a client re-upload. It retains parent artifact
  ID and the same byte digest, with the same source validation/limits

Line numbering is one-based over Python UTF-8 text `splitlines(keepends=True)`.
Chunks contain whole lines only. `max_bytes` can be reduced, e.g. to 1,800 for a
model evidence excerpt. If the next line alone exceeds that budget, the read
fails with `SOURCE_LINE_EXCEEDS_READ_BUDGET`; no partial line or coverage claim
is recorded. The caller must not trim the returned excerpt while retaining its
full line coverage. Omitted earlier/later lines set `truncated=true`.

Passing `coverage_id=run_id` records the exact returned ranges, separately for
`source_read` and `local_parser`. A full local parse does not establish that a
model received or reviewed the file. Coverage proves what this reader returned;
actual provider dispatch/consent/usage is separate run evidence. Range coverage
is unioned for validation and limited to 1,000 entries per scope.

## Artifact content and provenance

`ArtifactService(runtime)` is exposed as `runtime.artifacts`.

`ArtifactInput` has `format`, `display_name`, `content`, `provenance`,
`authorship` (`deterministic|model|owner`) and optional `supersedes_id`.

- Markdown/text content is a nonempty UTF-8 string
- CSV content is `{columns:[string], rows:[[scalar,...],...]}`; unique nonblank
  headers, up to 40 columns/1,000 rows, exact row widths, finite numeric cells
- JSON content is a JSON-compatible value with the same depth/node bounds;
  serialization uses UTF-8, indentation and no NaN/Infinity
- Artifact size at most 256 KiB; four reservations/1 MiB per run;
  400 reservations/64 MiB per desk. Uncertain reservations consume limits
- Revisions create new IDs; `supersedes_id` links an existing private artifact
- Every filename is generated ID plus a fixed format extension

CSV is written with the standard CSV writer, correct quoting and CRLF record
separators. String cells that can begin spreadsheet formulas (`=`, `+`, `-`,
`@`, including leading whitespace/zero-width prefixes) or start with tab, CR,
LF or BOM are prefixed with an apostrophe. Genuine numeric cells stay numeric.
`csv_string_escaping=apostrophe_prefix` discloses this intentional change. Source
CSV bytes are not rewritten; escaping applies to generated CSV output.

Each structured provenance entry is `{source_id, source_revision:1, start_line,
end_line}`. Publication checks that the source exists, is selected and verified,
and the range exists. For run output, ranges must have recorded coverage in that
run. Model-authored output requires `source_read` coverage; deterministic/owner
output can also cite a local-parser read. Canonical provenance adds the actual
source SHA-256 and `acquired_at` timestamp. Empty provenance is allowed for output
based on separate task/calendar evidence retained by the run coordinator.

These checks validate structured references, not arbitrary prose hyperlinks or
whether a claim follows from its citation. They are not semantic fact checking.
The manifest always reports `quality=not_semantically_checked`; authorship remains
explicit. The run verifier separately checks required sections/columns/outcomes.

## Publication, crashes and independent readback

`file_store.py` shares the durable byte-object mechanism without exposing host
paths. The operator's runtime directory is the trusted root. Source/artifact
subdirectories are private owner-only directories opened with `O_NOFOLLOW` and
`O_DIRECTORY`. Every file access is relative to that held directory descriptor.
Checks reject symlinks, hardlinks, nonregular files, changed inode identity,
wrong owner, nonprivate file modes, size mismatch and digest mismatch.

Publication order:

1. Validate content/provenance and reserve immutable ID, metadata, request hash,
   byte count/digest and operation key in SQLite before disk effects
2. Exclusively create a generated private temporary filename with no-follow
3. Write bounded bytes, flush and fsync the file
4. Revalidate the owner session/private mode and temporary inode; for run-origin output, validate the trusted coordinator checkpoint again under the final publication write transaction
5. Atomically hardlink to the final generated filename, failing if it exists;
   unlink only the verified matching temporary inode
6. Fsync the directory and independently reopen/read the final bytes
7. Record `verified` only on matching bytes and completed durability barriers

SQLite and filesystem are not one atomic transaction. Concurrent readers cannot
promote temporary-only bytes. Reconciliation of a reserved/unknown final file
must validate exact bytes, then itself fsync file and directory before promoting
it. If fsync fails it remains unknown. Readback never writes content or publishes
an unfinished temporary file. Missing, partial, changed or unsafe files remain
unknown and are not automatically repaired, overwritten or deleted.

Same operation key and canonical request hash returns the original reservation.
Changed content/metadata under that key returns `OPERATION_ID_CONFLICT`. A crash
before final publication can therefore leave an unknown reservation permanently;
blind retry will not produce another effect. The coordinator must present that
uncertainty, rather than call a new operation successful. Original temporary
objects remain bounded by reserved capacity and require explicit future
maintenance policy, not broad cleanup.

Internal artifact API:

- `publish(payload,key,*,session_hash,selected_source_ids,run_id=None,step_id=None)`
  returns `{artifact,operation_id}`
- `detail(id,*,session_hash)` and `reconcile(...)` perform safe current readback
- `listing(*,session_hash,run_id=None,limit=50,cursor=None)` is bounded metadata
  paging; its status is the last recorded result, not a fresh filesystem proof
- `read(id,*,session_hash)` returns `{artifact,content,truncated,
  preview_kind:plain_text}`, with a 32-KiB UTF-8-safe preview
- `download(id,*,session_hash)` returns `(artifact, bytes)` after current readback
- `import_download(payload,key,*,body,expected_sha256,session_hash,
  selected_source_ids,run_id,step_id)` accepts only actual Markdown/text export
  bytes supplied by the trusted browser adapter. Digest and payload serialization
  must match those exact bytes; storage does not generate a substitute export

A browser-download origin is an integration assertion, not proof that this file
service itself operated a browser. The adapter must retain its real UI/export
receipt and independent original-file inspection. No model-provided host path
is accepted by import or any other service method.

## HTTP interface and safe rendering

Owner/private routes require the existing authenticated owner cookie. Writes
require `X-Desk-Request: 1` and `X-Operation-Id`.

- `POST /api/sources/upload?name=notes.md&format=markdown`: raw UTF-8 request body,
  streamed and rejected as soon as it exceeds 1 MiB; no multipart dependency
- `POST /api/sources/from-artifact`: JSON `{artifact_id}`
- `GET /api/sources`, `GET /api/sources/{id}`
- `GET /api/sources/{id}/content?start_line=1&max_lines=200`
- `GET /api/artifacts?run_id=...`, `GET /api/artifacts/{id}`
- `GET /api/artifacts/{id}/content`, `GET /api/artifacts/{id}/download`

Source-list response is `{sources,next_cursor,limits}`; artifact-list response
is `{artifacts,next_cursor,limits}`. Artifact metadata includes ID, run/step IDs,
format, display name, MIME, bytes, hash, creation time, version, canonical
provenance, authorship, origin, status, error code, verification and quality.
`verification=byte_readback` is present only for a verified record; otherwise it
is `unverified`. There is no client-controlled artifact publish route.

Previews are JSON text strings, not rendered HTML/Markdown. Clients must render
with text nodes/pre, never raw HTML, remote images or automatic link execution.
Downloads use fixed MIME and generated-name attachment disposition with
`nosniff`, no-store and restrictive CSP. Raw HTML inside a Markdown document is
untrusted source text, not executed by the service or preview UI.

## Verification evidence

`tests/test_artifacts.py` uses real temporary SQLite and filesystem directories.
It independently opens produced Markdown/CSV/JSON files and recomputes hashes,
parses CSV escaping, checks actual bytes, provenance/range/coverage, selection,
capacity, safe previews/download headers, and session/private denial. It covers
same-key concurrency and replay, fault-injected boundaries, actual child-process
exit/restart, fsync failure, source corruption, symlink/hardlink/FIFO/path attacks,
and existing-artifact reuse. This is real local storage evidence, not a claim
of live model quality, successful browser control or completed remote uploads.
