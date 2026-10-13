# MCP connector implementation and verification

Date: 13 October 2026 UTC. Scope: new connector-specific backend package, focused tests, connector contract and this QA supplement. Parent owns runtime/routes, run-loop integration, frontend, repository-wide checks, publication and root handoff documents. No Git push, real accounts, credentials, installation, security-setting change, external write or live model request was performed here.

## Actual deliverable

- Explicit operator configuration and per-tool descriptor/schema/resource grants, empty by default
- Actual MCP initialization/tool discovery/revalidation/call over a bounded HTTP transport with JSON/SSE, original-host TLS validation/public-address pinning and no ambient credentials/proxy/cookie/redirect transport
- Local immutable owner-reviewed intents, stable operation dedupe, actual owner-session/privacy/provider fences, once-only durable dispatch, cancellation, restart fencing and unknown-effect handling
- Shared run-registry adapter with actual tool argument schema, immutable bounded untrusted evidence and full owner-only review/results
- Strict local JSON Schema subset, bounded request/result handling, local fixture exemption confined to test code, and no approval capability for the model
- [Implemented contract](../../../desk-companion/docs/application-connectors.md)

## Checks and their meaning

The builder's focused suite passed **56 tests**, with Ruff passing. These use a real HTTP fixture server in the same test process, actual serialized JSON/SSE and SQLite intent persistence; target state is inspected independently of the server response text. Fault-only clients are explicitly scripted. This does not demonstrate production TLS interoperability or a real third-party account/application.

An independent reviewer reran the connector, shared run-bridge and owner HTTP integration suites: **71 passed**. Three separate reviewer probes also passed. See [independent review](independent-authority-review.json) and [repro source](independent-authority-repros.py). The final formatted-source rerun passed **72 focused/integration tests plus three independent regressions**, recorded in `final-focused-integration-tests.log` and `final-independent-regressions.log`; source hashes are in `source-manifest.json`. These checks are narrower than the parent batch's full backend/frontend/CI acceptance.

Significant findings were fixed and negatively rechecked:

1. Remote metadata discovery under the parent run control lock could delay pause/cancel. Preparation now has zero network work; fresh discovery remains in background execution before the tool call
2. A near-node-limit tool result fit alone but overflowed the full ledger record, leaving `dispatching`. Full terminal-state validation now falls back to compact `unknown_effect` without replay
3. Continuous HTTP header drip evaded idle timeouts. Header/body socket reads now share an absolute deadline. A 50 ms test returned at about 51 ms
4. A verification timestamp changed on every poll, invalidating immutable evidence. Evidence now uses the persisted observation timestamp
5. Slow OS DNS is caller-bounded with one resolver slot and no late send/connect. The independent blocked-DNS probe returned around 64 ms, rejected concurrent unresolved work and observed zero late connections

Additional cases cover repeated approval, changed arguments/destination/schema/descriptor, malformed output, dishonest read-only/idempotence annotations, unsupported server capability requests, tool-list drift, cancellation before/during dispatch, privacy hide/show, logout, duplicate workers, restart, capacity, metadata-only listing, exact owner/data review, provider-forwarding scope, result integrity and post-reauth cancellation without new child authority.

## Actual external attempt

Official OpenAI documentation verifies `https://developers.openai.com/mcp` is a public documentation-only read service with anonymous access. A safe metadata inspection was attempted through this implementation, then stopped before connection at `CONNECTOR_PUBLIC_DNS_REQUIRED`. The read-only DNS diagnostic returned `gaierror`, errno `-3`, temporary name-resolution failure. See [attempt](public-docs-discovery.json) and [DNS diagnostic](public-docs-dns.json).

No live tool descriptor or server identity was obtained. The proposed harmless query, “Responses API streaming,” was not sent. No grant was fabricated and no network restriction, alternate resolver, proxy or security check was bypassed. Public documentation read through research tools does not count as this adapter successfully calling the external MCP server.

## Remaining gates

- Authorized-network production transport initialization/discovery and one harmless public-document query, with actual compatible descriptor and explicit temporary operator grant
- Application-specific independent read/verifier before promoting MCP write observations to verified external outcomes
- Authenticated/private-data connectors, credentials/OAuth, wider JSON Schema support, other MCP capabilities and real cross-application/model-quality acceptance
- Existing target-computer/LCU, browser and hardware gates remain separate

One OS DNS resolver may outlive cancellation but cannot dispatch. TCP/TLS connect uses short phase timeouts rather than a process-kill guarantee. Cancellation notification is best effort, not rollback. The generic adapter's returned success is an untrusted observation, not an independent outcome proof. No commercial-product parity or full project completion is claimed.
