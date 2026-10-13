# Find retained work and files

Implemented 13 October 2026. `POST /api/work/search` searches local retained run,
source and artifact metadata. It helps the owner choose an exact saved item; it
never resumes work, selects data for a model, previews content or downloads a
file automatically. Lexical matching is not semantic or full-text retrieval.

## Read-only owner boundary

The endpoint uses the normal owner cookie, allowed-origin boundary and
`X-Desk-Request: 1`. A paired controller, display or device-agent identity is not
an owner. An actual unexpired owner session is checked inside the service before
reading and again in a fresh SQLite transaction immediately before returning.
The settings version and personal-context epoch fence delayed responses,
including hide → show and privacy-consent changes during a read. A current
hidden setting, revoked session or elapsed expiry blocks the response.

The query is a JSON body, not a URL query parameter. The service does not write
queries, results, an index, operation receipts, coverage, audit rows or store
revisions. It does not read file bodies, reconcile status, call a model/tool,
start a worker or acquire new access. Both database connections enable SQLite
`query_only`; service construction creates no tables or files. The app returns
`Cache-Control: no-store`.

## Request and compact result

`WorkSearchInput` rejects unknown keys. Its fields are:

- `query`: string, default empty, trimmed, at most 200 input Unicode characters
- `kind`: `all` (default), `run`, `artifact` or `source`
- `limit`: integer 1–50, default 20; booleans and numeric strings are rejected
- `offset`: integer 0–600, default 0
- `snapshot`: optional lowercase 64-character hex fingerprint; required whenever
  offset is nonzero

Empty or whitespace-only queries browse the bounded corpus by recency. Query
text is NFKC normalized, casefolded and whitespace-normalized. Expansion caused
by normalization is supported rather than silently truncated. Unpaired Unicode
surrogates are rejected at input. Quotes, `%`, `_`, regex-like strings and HTML
are ordinary literal text, never operators or executable instructions.

The response is `{items,total,snapshot,next_offset,search_scope,ranking,
file_status_basis}`. `next_offset` is null at the end. The fixed scope labels are
`local_metadata`, `lexical_v1` and `last_recorded` respectively.

Every item contains `kind`, exact `id`, `title`, `timestamp` (UTC or null),
`matched_fields` and `match_reason`. The additional whitelisted fields are:

- Run: `state`, `version`, `mode`, `plan_revision`, `source_names`. The title is
  the run's current goal, not a historical goal
- Source: `format`, `byte_count`, `recorded_status`, `revision: 1`. The title is
  its display filename; timestamp is its acquisition time
- Artifact: `format`, `byte_count`, `recorded_status`, `run_id`,
  `current_linked_goal`, `output_membership`, `source_names`. Timestamp is its
  creation time

`recorded_status` is `verified` or `unknown`; reserved or malformed states become
unknown. Missing/malformed optional legacy fields are represented by an empty
title, null scalar, empty names or unknown state/membership rather than string
coercion or a guessed association. File titles cannot become host paths. Table
identity overrides any inconsistent identity embedded in JSON metadata.

The projection omits session hashes, operation keys, request hashes, full
reports, source bodies, evidence, tool payloads, memory, conversations, provider
configuration and host filesystem fields. Search hits are distinct types and
must not be cast into full source/artifact records.

## Complete bounded snapshot and pagination

All run and file rows are read in one explicit SQLite read transaction. SQL
projects only the admitted JSON keys; it does not load the broad run `_view()`.
JSON `->` extraction preserves the distinction between booleans and integers
(SQLite JSON operators, available in SQLite 3.38 and later).

The admitted complete corpus is at most 100 runs, 100 source reservations and
400 artifact reservations. Each kind is checked with one extra row, including
when a filter is selected. Failed/unfinished reservations still count. An
over-cap corpus returns `WORK_SEARCH_CAPACITY_EXCEEDED` (409), never a partial
result labelled complete. Malformed/non-object JSON, invalid exact record IDs
or a projected metadata object exceeding 64 KiB returns
`WORK_SEARCH_METADATA_INVALID` (409). No row is silently dropped to manufacture
a complete result. The app's existing capacity and file-management policies are
unchanged; search does not delete or repair old records.

The opaque snapshot digest binds normalized query, kind filter, actual owner
session, privacy revisions and the complete compact metadata projection.
`limit` and `offset` can change within that snapshot. Projected status/title/
linkage/timestamp changes invalidate pagination even if another hit changed.
Nonsearchable report/tool payload changes do not invalidate it. A mismatched
snapshot returns `WORK_SEARCH_CHANGED` (409); the caller must explicitly refresh
from the beginning. A new session cannot reuse the previous session's pages.

The corpus is an internally consistent snapshot. A concurrent work update can
occur after that snapshot; exact selection must still fetch current detail.
The final authority check is deliberately outside the old snapshot, so current
revocation/privacy cannot be hidden by SQLite's consistent historical read.

## Deterministic lexical ranking

Every whitespace-separated query term must occur in an admitted field. An
unspaced Chinese phrase is one literal substring. There is no translation,
fuzzy correction, synonym expansion, semantic ranking or inferred memory.

Ranking, strongest first:

1. Exact own opaque ID
2. Exact own display title/current goal
3. Full phrase in an own field
4. All terms in own fields
5. A match requiring linked metadata

Only then come newest timestamp and stable kind/ID ordering. An older exact
match therefore outranks a newer weak match. Runs search current goal, ID and
selected source names; artifacts search display name, ID, current linked goal
and provenance source names; sources search display name and ID. A source name
is linked only through an actual selected/provenance source ID present in the
same corpus, never an inferred filename similarity.

`matched_fields` uses `id`, `title`, `source_name`, `current_linked_goal`.
`match_reason` is `exact_id`, `exact_title`, `phrase`, `all_terms`,
`linked_metadata`, or `browse`. Duplicate names remain separate exact-ID choices.

## Honest artifact association and recorded file status

The associated goal must be labelled **Current linked goal / 当前关联目标**.
Steering overwrites a run's current goal; neither timestamps, filenames nor
`supersedes_id` can reconstruct an artifact's original goal or revision.

`output_membership` is:

- `current`: the exact artifact ID belongs to a present valid
  `current_artifact_ids` list
- `earlier`: the exact ID belongs to a valid `artifact_ids` history and is absent
  from a present valid current list
- `unknown`: missing parent, missing/malformed membership, invalid parent scope
  or the publication window before the run records its output linkage
- `unlinked`: no parent run ID was recorded

A current membership can be known even when legacy history is missing. An
artifact linked to an existing run can show that run's current goal while its
output membership remains unknown. No historical-goal or plan-revision claim
is inferred from that relationship.

Search only reports last-recorded byte status. A file can be missing/corrupt
while its search result still says last-recorded verified. Opening the exact
`GET /api/sources/{id}` or `GET /api/artifacts/{id}` performs the existing fresh
readback; both return bare full records. Preview and download use their existing
exact-ID byte/provenance contracts. A subsequent failed read can update recorded
status to unknown and therefore invalidate pagination. Fresh detail/preview/
download evidence is separate from metadata discovery.

## Interface and acceptance boundary

The private Work workspace explicitly submits a query/filter; it does not search
on every keystroke or the run poll. The interface fences submitted query/filter,
request sequence and identity/privacy state, clears private results when
hidden/offline/stale/signed out, keeps search state out of browser storage and
URLs, and requires a choice among duplicate matches. Opening work respects the
existing dirty-draft guard and fresh versioned controls. Existing file preview,
download-digest and safe-text behavior remains authoritative.

Service tests use actual isolated SQLite databases and fixture files. They cover
all admitted 600 records, ranking/Unicode/literal data, deterministic pagination,
malformed legacy values, exact relationships, recorded-versus-current bytes,
strict projection, origin/owner protections, delayed revocation/hide-show and
zero search effects. These tests do not establish actual mounted-browser
behavior, live-model quality, semantic recall, or general cross-application
capability. See [backend verification](../../output/qa/2026-10-13-work-search/backend-verification.md)
and the aggregate/frontend evidence linked from the current handoff.
