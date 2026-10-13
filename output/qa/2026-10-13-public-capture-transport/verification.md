# Exact public capture transport implementation

13 October 2026, Group 2. Same ongoing 186-document intake inherited; focused reading in `reading.json`. Only transport source, focused tests and this independent QA directory owned by this worker. Parent owns shared specification updates, application integration and Git publication.

## Delivered

- Shared `connectors/public_https.py`: original pinned TLS, single resolver semaphore, total-deadline reader/socket and conservative 16-KiB buffered header guard extracted once. Generic transport failures map to unchanged MCP `CONNECTOR_*` codes through the compatibility module. MCP request/response, JSON/SSE, session and cancellation protocol stays unchanged.
- `connectors/public_capture_transport.py`: `PublicCaptureClient.fetch(url: str, checkpoint, *, on_dispatch=None, deadline=None) -> CaptureResponse(raw: bytes, mime_type: str)`. URL/MIME admission uses the separately owned pure policy. Caller owns durable consent, lifecycle and dispatch-marker authority. Supplied deadline is capped at a further 20 seconds.
- Capture reuses exactly one resolver slot, checks every answer with explicit public-unicast flags (and checks mapped IPv4 where present), chooses one numeric address and directly opens that address without a second `getaddrinfo` or alternate-address retry. Default certificate validation and original-host SNI remain. TCP/TLS boundaries recheck authority and remaining timeout.
- Capture-only response parser checks raw CRLF status/headers before standard parser normalization and rejects all 1xx before `HTTPResponse.begin` can consume 100. Rejects folds, invalid field syntax, controls, parser defects, duplicate/absent required framing, all transfer encodings, compression, upgrade and unsupported MIME. Exactly one canonical nonzero Content-Length through 128 KiB required; truncation cannot return a saved prefix.
- One GET has fixed product headers, exact path/Host, no body, cookies, proxy, authentication, user headers or MCP cancellation. Redirect/auth/status failures stop locally. Socket/response cleanup includes parser failure before `getresponse` returns. Caller cancellation and deadline checks surround bounded reads and dispatch.

## Verification

- New byte-preserving socket/resolver tests: 77 passing, no live public DNS or network. These retain deliberately malformed bytes, unlike normal HTTP server libraries.
- Existing unchanged MCP suite: 56 passing. Includes original loopback MCP HTTP/SSE fixtures, cancellation, total header deadline, pinned TLS seam and resolver taxonomy. Loopback fixture traffic only, never a public request or live account.
- Ruff passes for all four owned source/test files. Combined final output is `pytest.txt`; lint output `ruff.txt`; frozen source identities `source-hashes.json`.
- Focused cases cover 100+200/101/103, auth/redirect/429/204, duplicate length/type/encoding, noncanonical/oversize/zero lengths, TE/upgrade, compression, missing MIME/length, non-CRLF, folded/malformed/control headers, truncation, exact 128-KiB body, header cap, read-ahead conservatism, public/mixed/private/multicast/mapped/scoped addresses, busy/blocked shared resolver, one pinned TCP/TLS endpoint, connection/certificate failure, cancellation before/after dispatch/TCP/during body, socket timeout and dripped total deadlines.

## Explicit limitations

The shared header guard includes buffered body read-ahead, so valid headers near 16 KiB can conservatively fail; the test uses uneven 3,000-byte chunks to demonstrate this and does not relax the guard. HTTP response completeness follows the sole accepted Content-Length frame; no EOF wait or second response is consumed after that frame. Raw headers/cookies are not retained in the result. Public-mapped IPv6 is accepted only if both the outer and mapped-address predicates pass on the supported interpreter; mapped private/multicast forms are rejected.

No live public URL, paid model, account, installation, real store migration, deployment or Git operation occurred. TLS assertions use controlled socket/context seams and do not establish live certificate negotiation. This worker does not claim source publication, lifecycle durability, mounted UI, browser save or complete workflow acceptance; those remain independent integration/review gates.

Subsequent independent review found the GET write could retain a pre-TLS timeout. The coordinator refreshes the remaining timeout immediately before request; the final321-case independent aggregate and eight-file hash stability passed. See [independent audit](../2026-10-13-public-capture-transport-policy-audit/review.md) for final superseding hashes and exact-frame (not EOF) semantics.
