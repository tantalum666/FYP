# Exact public URL capture: independent proposal review

13 October 2026. Planning review only, inherited ongoing 186-document intake. Application source, shared contracts, runtime databases, Git and settings were not edited. All executable evidence was offline with fictional bytes, mocked resolver answers and temporary fixture files. No live request, provider, credential, user data, installation or browser was used.

## Recommendation

Proceed with the **single owner-selected exact URL → retained static-text source → explicit ordinary Work selection** slice after the current frozen release. Keep the feature off by default. Do not add search, crawling, redirects, JavaScript, account access, model tools, semantic comparison, source reclamation or another planner. The review-record acknowledgment is a necessary improvement: even cancelled preparation retains the URL and consumes one of 200 history identities.

The proposed design is suitable for a narrow implementation, conditional on resolving the transport and schema points below before durable capture is enabled. Local software evidence must remain separate from public-DNS, mounted UI and actual browser-save acceptance. Current known UI/save gates do not prevent safe offline implementation; they do prevent claiming an accepted usable workflow.

## Required clarifications and seam fixes

### 1. Public DNS admission is not already sufficient for the capture policy

`connectors/mcp_transport.py:public_addresses` rejects `not ip_address(address).is_global` only. The checked interpreter and the actual helper admit multicast `224.0.0.1` and `ff02::1`. The plan specifically forbids multicast, so merely extracting the existing function does not implement that promise. This is an admission mismatch, not evidence that a successful multicast HTTP exchange occurred.

Keep exactly one shared resolver slot and one resolver attempt. After its complete result, the capture wrapper must apply explicit code-owned public-unicast checks to **every** answer, including IPv4-mapped IPv6 checks, before choosing any address. Preserve MCP's existing policy/error mapping during the mechanical extraction; any shared admission hardening should be an expressly identified, independently tested security change rather than smuggled into a behavior-preserving move. Do not solve it with another resolver, network bypass, host allowlisting of a rejected result or a duplicated transport. Resolve how shared helper errors map back to unchanged CONNECTOR_* codes in the extraction tests.

Evidence: `probes.json` shows the actual existing helper returning both multicast answers under mocked DNS, with zero network.

### 2. Strict framing needs a capture-only parser seam, not only post-response checks

The plan now rejects every interim response, transfer encoding, duplicate length, compression and close-delimited response. That deliberate narrowing is good. However, `http.client.HTTPResponse.begin()` consumes 100 Continue and its headers internally, returning only the final 200. A client that inspects only `response.status/getheaders()` cannot enforce rejection of the interim response. The offline probe supplies 100 + 200 and receives just status 200, final headers and `ok`.

Specify a small **capture-only** response/status-line hook that rejects any 1xx before the standard parser hides it. Do not change the MCP response class or its current JSON/SSE behavior. Inspect raw header multiplicity with `get_all`, require the single canonical length, and explicitly reject malformed/ambiguous header parsing and continuations according to a documented rule. Test this using a byte-level response fixture, not only a convenient server library that canonicalizes malformed headers.

The current `_DeadlineReader` counts bytes read into the buffered reader while `header_phase` is true. That can include up to a buffer's worth of body read-ahead. It is conservatively bounded but is not exact syntactic header accounting. Preserve MCP's guard, and either disclose conservative rejection near the 16-KiB edge or implement/test capture-specific exact accounting. Do not relax the guard to make a boundary test pass. Compare actual accepted body bytes to the declared frame length; never treat EOF truncation or reaching a read limit as complete capture.

### 3. Decide schema version policy before capture-service initialization

`Store` currently accepts existing schema 1 or current schema 2, validates the watch schema before journal/bootstrap writes, and uses `allow_watch_retention_migration` for its particular 1→2 migration. New capture tables cannot silently acquire compatibility/approval from that flag. `CREATE TABLE IF NOT EXISTS` alone also cannot distinguish a genuinely uninitialized extension from a damaged missing ledger whose loss would erase once-only barriers.

Recommended bounded policy: fresh fixture stores initialize schema 3; a recognized schema-2 store requires a separately named, explicit offline 2→3 opt-in with stop/verified-backup prerequisites. Create both capture tables, constraints/indexes and the global version in one transaction. Schema 3 requires both tables and valid structures, including when capture capability is off; missing/partial/incompatible capture schema fails closed rather than recreating empty history. Existing schema 1 should first take the existing separately authorized 1→2 path, unless a separately reviewed staged migration is deliberately added. Do not overload the watch flag or opportunistically migrate from Runtime construction. No user database migration is part of this proposal review.

Keep capture record format `policy_version=1`/intent format version distinct from global schema 3. Test fresh, v2-no-opt-in, v2-explicit, partial schema, wrong constraints, transaction failure and restart cases. Existing v2 binaries reject a future user_version=3, but historical binaries cannot be retroactively made safe; retain the current operational ban on old binaries touching migrated stores. This is one small migration, not a request for a migration framework.

### 4. Split the final-link recovery windows honestly

The current immutable writer creates a final hard link, then checks identity, removes `.pending`, fsyncs the directory and independently reads back. `_read_bytes` requires `st_nlink == 1`. Therefore:

- Before final link: temporary-only evidence stays unknown; no publication on reconcile
- After final link but before pending unlink: final and pending usually have link count 2, so existing recovery rejects FILE_READBACK_MISMATCH; retain unknown, counted evidence and do not unlink/repair it automatically
- After pending unlink, before fsync/readback/association: exact single-link final bytes can be independently checked and fsynced by existing recovery

The proposal's “final link before directory fsync ... may recover” is not false because it says “may,” but should name the two distinct windows so an implementation/test does not broaden the existing no-repair rule. The probe recreates these two windows and confirms mismatch at link count 2, exact readback at 1.

Cancellation after the link is already a possible retained source even if ingest throws due to lost session/privacy before returning the ID. Do not mark it absent or successful automatically. Persist cancellation independently from source verification, resolve the exact private-file key only under current authorized local reconciliation, and keep no-refetch semantics.

### 5. Make the private-helper and checkpoint adaptation explicit

The proposal correctly recognizes that `ImmutableFiles.put` invokes the first checkpoint **before** looking up/inserting the reservation and does not pass a newly generated source ID to it. Its later checkpoints again receive only the transaction. `SourceService.ingest` has no checkpoint/provenance parameter today. `WorkCapacityService._files` and file `_row`/`_read_bytes` are private helpers, not ready-made public capture APIs.

Use a minimal internal source admission helper receiving the existing transaction, plus a minimal exact `(kind, operation_key)` lookup validating SQL identity, canonical request hash and bounded immutable capture metadata. Avoid calling `snapshot()` or a service method opening another connection from inside the checkpoint. Do not duplicate the source writer or use URL/hash-only searches. Keep normal upload/artifact provenance unavailable to client-supplied fields.

Inside the reservation transaction, first identify and validate an existing exact operation. For a new one, validate all source count/byte accounting and charge prospective count/bytes once; at final linking the already-reserved row is already charged. Do not attach the new ID atomically by pretending the checkpoint knows it. Store acquisition hash/count before put and attach its returned ID afterward; uncertain return uses exact local key lookup. Original-operation reconcile does not rerun ingest or regenerate extraction, and cannot be blocked by a full history/source quota or unrelated corrupt accounting bucket. It still requires valid identity and file integrity, so “recovery bypasses new admission” must not mean “recovery accepts a corrupt row.”

## Implementation acceptance details to retain

- Owner authority: code-owned immutable URL/policy/retention hash, original owner session, privacy/settings epoch, service claim/generation and execution deadline checked before DNS, connection dispatch, between bounded reads/parser work and under the final-link write transaction. Hide→show never restores old execution authority. A dispatch-possible marker is conservative, not proof of server receipt; its transaction is the local dispatch boundary, not a guarantee that no packet can occur after a later cancellation.
- Read privacy: list/detail/reconcile responses also need fresh current-session and captured privacy-revision checks before returning private URL/acquisition fields. Do not rely only on React response fences or the file store's current-visible check. Hidden stop must use a small scalar allowlist and remain possible even if private intent JSON is corrupt; cancel must not need to parse an untrusted URL/body. A fresh owner can inspect/reconcile without rebinding an old worker approval.
- Cleanup: capture sends no MCP cancellation notification and does not reuse `McpHttpClient.request`, which sends a separate best-effort cancellation request on failures. Close response/socket locally only; no second public request, retries or replacement worker while a stuck worker/resolver slot remains occupied.
- Bounded receipts: 200 lifetime capture rows and at most one successful prepare/approve/cancel receipt each are enough. Handle original operation collisions before unrelated target access and before new-capacity admission. Returning current state on same-key recovery must not silently reuse approval for a new session. No-op repeats create no extra receipt.
- Provenance: immutable generated filename, exact source/capture identity, received time, admitted MIME, raw and extracted hashes/counts, pinned extraction version and disclosed raw-not-retained/static-only coverage. Remote text, embedded links and claims of approval remain untrusted. No auto-selection, model invocation, transmitted goal/label/private context, cookie, proxy, alternate address, redirect or browser fallback.
- Extraction: strict UTF-8, bounded event/depth/output budgets, explicit void/hidden/malformed behavior and deterministic Unicode-safe line wrapping. Check parser work in bounded chunks/events; do not call one unconstrained parser pass then check authority only at the end. Golden tests must include qualifiers, negation, hidden nesting, malformed tokens, multi-byte boundary and line-separator behavior matching SourceService line numbering.
- UI: add the compact intake beside existing upload, show static acquisition provenance explicitly (current SourcePreview only shows filename/ID/hash/lines), use existing plain `<pre>` output, retain the original unknown operation, and let the owner explicitly choose ordinary Work sources. Reopen/list is not freshness verification. Do not auto-link URLs or preview remote images. Capture output remains evidence compilation, not a feature comparison.

## Suggested next stage and stopping gate

1. Mechanical shared transport extraction with unchanged MCP protocol/error/security tests, plus a separately identified capture-unicast policy and capture-only framing hook; one shared DNS slot
2. Pure URL/extraction policy plus fresh-store fixture lifecycle/source adapter once the explicit schema policy is chosen
3. Independently recorded fixture GET count, failure/cancellation/restart/capacity matrix, exact retained source bytes and ordinary Work output readback; then the compact gated UI

The schema decision and the three observed seam mismatches above must be resolved before claiming implementation acceptance. No general platform architecture is needed. Broader repeated capture/source reclamation and semantic comparison remain separate. Public live acceptance, actual browser mount and saved-output verification remain accurately open.

## Evidence and limitations

`probes.py` ran successfully through the existing project virtual environment. `probes.json` contains three focused evidence groups: multicast admission, hidden interim response and hardlink recovery windows. These are tests of existing seams, not tests of an implemented capture service. No complete application test suite, TLS handshake, live GET, UI or migration was run during this proposal review. The parent owns shared documentation changes and any publication after its frozen aggregate.
