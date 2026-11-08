# Operator-reviewed MCP application connectors

8 November2026 update: private Google/Microsoft account connections now have a separate bundled [OAuth application contract](connected-apps.md). The generic MCP adapter below retains its public/synthetic restrictions; it does not inherit these account tokens or gain private-data access. The owner-facing app catalog is shared, but provider availability and actual operations are reported separately.

31 October 2026 integration: read [current compatibility and migration rules](pr5-integration.md) first. Dated October 12–13 acceptance statements below remain historical; this integration preserves Alice/current Omni and the current task/job/permission core.
Updated 13 October 2026, Group 2. This is an extensible tools adapter, not an authenticated app marketplace or a claim of consumer-agent parity. It supplements the existing [run service](agent-runs.md), [computer jobs](computer-jobs.md), and separately scoped [browser workflow](browser-workflow.md). Default configuration contains no external endpoints or grants.

## What is implemented

A configured MCP server can expose additional application tools through the same run-tool registry, without another hard-coded planner workflow. The operator approves a server identity, exact HTTPS endpoint, full tool descriptor digest, explicit effect classification, bounded argument schema and resource scope. A model sees only tools explicitly selected for its run and their actual operator-approved argument schemas.

Every call, including a declared read, first creates an immutable local review. The owner sees the complete arguments, exact MCP endpoint, tool/server identity, destination scope, descriptor/grant hashes and data notice. The owner's separate public/synthetic acknowledgment and approval bind the exact intent and version. The model has no approval, endpoint-registration, credential, shell or installation tool.

Preparation performs no network requests and does not hold run controls across discovery. A background worker negotiates and rediscovers capabilities immediately before a reviewed call, checks the pinned identity/descriptor and both remote and operator input schemas, and durably reserves the call before sending. Unsupported or changed metadata rejects execution before the tool request. An unconfigured tool or a server's `readOnlyHint`/`idempotentHint` cannot grant authority.

A returned MCP result becomes `observed_result`, with `verified: false`. It proves the server returned those bounded bytes. It does not independently prove a document was saved or another external outcome occurred. Required writes without an application-specific independent verifier remain unmet in the parent run. This generic adapter deliberately does not turn a server's success claim into verification.

## Operator configuration and admission

The runtime reads an explicitly supplied `DESK_MCP_CONFIG_PATH`; absence leaves connectors off. The file is a JSON array of at most eight connector configurations and at most 64 KiB. It must be a regular, singly linked, non-symlink file that is not group/world writable. The loader does not expand environment references, URLs, secrets, commands or headers. Invalid configuration fails rather than switching to another target.

Each connector has:

- `id`: lower-case stable name, at most 40 characters
- `endpoint`: exact HTTPS hostname/path, default port 443; no credentials, query, fragment, explicit port, IP literal or redirect
- `server_name`, `server_version`: exact values observed through separate operator-only metadata inspection
- `tools`: at most 32 explicit `ToolGrant` entries

Each grant has:

- `tool_name`: exact case-sensitive MCP tool name, at most 128 characters
- `descriptor_sha256`: digest of the entire canonical tool descriptor, including annotations and schemas; not merely the name
- `effect`: explicitly reviewed `read` or `write`, never inferred from remote annotations
- `input_schema`: bounded operator restriction, including constant/enumerated targets where the tool accepts resource/destination identifiers
- `destination_scope`: a human-readable exact resource/destination description for review; prose alone does not constrain a permissive schema
- `data_policy`: `public_or_synthetic` only in this implementation

Tool IDs are `mcp.<connector id>.<tool name>` and are looked up as complete strings. No substring becomes a URL, path, command or authority. Discovery returns untrusted metadata for operator inspection; it never installs grants. Operator inspection can use `inspect_endpoint(endpoint)` to obtain server/tool fingerprints without making a tool call. The returned inspection client is not exposed for execution. Inspecting an endpoint does not make it trustworthy or prove its claimed effect semantics.

Only the public/synthetic data slice is admitted. Run-linked connector calls cannot be combined with selected private files, task/calendar records, memory or conversation history. They require separate consent to send returned public tool results to the run's exact configured and approved text-model destination. The immutable review includes `provider_destination: {id, kind, provider, endpoint}` for that onward transfer; direct owner-only calls have `null`. The service rechecks this destination before approval/dispatch. The model's `public_only` argument is a proposal, not proof that text is public: the real owner must review and acknowledge the actual complete data.

Credentials, OAuth, account login, custom headers, ambient cookies, system proxies, local/private-network endpoints, stdio/shell transports and automatic secret inheritance are unsupported. Production does not contain a switch to admit loopback HTTP. The local test subclass replaces the connection only inside tests. New authentication or private-data support requires separate design, authority and acceptance; setting a model key cannot enable it.

## Protocol subset and limits

The client implements MCP **2025-11-25** initialization, initialized notification, tool listing/pagination, tool calls, bounded JSON/SSE responses, session/version headers and best-effort request cancellation. It advertises no roots, sampling, elicitation, tasks or experimental client capabilities. Unsupported server requests fail closed. List-changed notifications invalidate the in-flight catalog rather than silently adding tools. Unsupported protocol versions and task-required tools are rejected.

Per request: 32 KiB serialized request, 128 KiB response, 16 KiB admitted header bytes, 20-second monotonic budget and at most three-second socket phase waits. Header and body reads both enforce the total budget, so continuous drip traffic does not reset it. DNS resolution uses one bounded daemon resolver slot and a caller deadline/cancellation fence; a blocked OS resolver may outlive the caller, but cannot subsequently send a request, and a second request is refused while that slot remains occupied. This is not an OS-wide process-kill guarantee. Cancellation delivery is a separate best-effort bounded request, so total worker teardown may include that additional request.

Public DNS admission rejects the entire result if any address is non-global, including loopback, link-local and benchmark ranges. The selected public address is pinned for the connection while TLS certificate validation/SNI retain the original hostname. No alternate resolver, proxy, redirect, certificate bypass or network-allowlist change is attempted. Connect/TLS work stays on the calling thread with the remaining timeout; late DNS results never own dispatch authority.

Discovery admits at most four pages and 64 unique tools per server; repeated cursors/names fail. Tool descriptors and schemas are bounded to 16 KiB, schemas to eight nesting levels, JSON values to 16 levels/4,096 nodes and finite numbers. Supported schema constraints cover typed objects, fixed properties/required fields, arrays/items, scalar types, enum/const, length/count and numeric bounds. Unknown properties are always rejected. References, regex, union/combinator schemas, schema fetching and coercion are rejected rather than ignored. This intentionally supports fewer schemas than the complete JSON Schema specification.

Results support text blocks and structured JSON, with optional output-schema validation. Image/audio/resource-link/embedded-resource results and oversized/invalid data are unsupported; nothing is auto-fetched or executed. Full bounded normalized results are owner-only. The planner receives content-free hashes/status plus at most 1,800 UTF-8 bytes of explicitly untrusted evidence, a stable observed timestamp and disclosed truncation. It does not receive the entire server response by default.

## Durability, cancellation and unknown effects

`connector_intents` lives in the existing single-host SQLite store. It retains up to 1,000 immutable intents and terminal receipts; there is no silent deletion or automatic archival. Capacity blocks new work while existing cancellation remains usable. These records are not a distributed queue, an encrypted vault or a complete external-service backup.

States are `review → queued → preflight → dispatching → observed_result`, with `rejected`, `failed`, `expired`, `cancelled` and `unknown_effect` outcomes. Review lasts five minutes; approved execution has a 60-second expiry. A stable operation key and canonical request digest deduplicate preparation. Repeated approval/dispatch does not create another call. MCP has no universal idempotency-key guarantee; local operation keys do not make an external write idempotent.

Owner session validity, private visibility, privacy revision, exact grant, intent hash and cancellation are rechecked before dispatch and result publication. Only session hashes are persisted. Hide/show or sign-out invalidates old authority. Model-data transfer consent cannot be inherited from selecting a tool. UI detail/list projections omit exact data while hidden; metadata-only listing and individual detail can be requested even while visible; cancellation can also return metadata only. The routes use an explicit metadata allowlist, including for a linked intent outside the latest listing page.

Cancellation before dispatch prevents a call. Cancellation after dispatch may leave an actual external effect and is classified conservatively. The client sends a best-effort MCP cancellation notification when it stops waiting for an issued request; delivery or remote cooperation is not guaranteed. No rollback is claimed. Late results cannot overwrite a cancelled, shutdown or replacement-service claim.

Restart recovers interrupted dispatched work as `unknown_effect`; interrupted preflight as rejected. It never retries an uncertain tool call. Result-validation/storage-limit failure also records a compact terminal uncertainty instead of leaving a job dispatching indefinitely. Read-only operation lookup binds the persistent run ID, operation key, exact tool/arguments, immutable intent hash and normalized result hash. It can recover/cancel the same child after the parent obtains a fresh owner session, without rebinding the child's original execution authority.

There is no generic reconciliation button that replays a write. An application-specific independently scoped read/verifier is needed to establish an unknown external outcome. Until then it stays unknown; a new operation ID is not an automatic recovery strategy.

## Integration contract

`build_connector_service(runtime, configs=())` constructs `McpConnectorService`; `connector_adapters(service)` returns adapters for the existing run registry. `catalog_for_run()` returns explicitly configured tool metadata and a scope fingerprint without network activity. `ConnectorToolAdapter.argument_schema(runtime)` exposes the exact grant parameters inside the reviewed call envelope.

The service provides `catalog`, `discover`, local `prepare`, `prepare_for_run`, `approve`, `detail`, `listing`, `cancel`, `lookup_operation`, background `advance_one` and `shutdown`. Approval is only a host-authenticated owner route, never a planner tool. Approved work is advanced off the HTTP request path. Run recovery and cancellation use the same registry hooks as the browser bridge; this package does not implement a second planner.

Owner routes are `/api/connectors/capabilities`, `/api/connectors/intents/{id}`, and the corresponding `/approve` and `/cancel` operations. Approval requires `expected_version`, `intent_hash` and explicit `public_only: true`. Cancellation accepts version checking for active requests and remains idempotent after stopping. Listing, individual detail and cancel responses support `metadata_only=true`; the frontend lists metadata first, then loads an explicitly selected visible review. A linked intent can be fetched and stopped directly even when it is outside the latest 50 results. The actual application route and UI tests, full-suite checks and publication are recorded in the parent batch's evidence rather than inferred from connector unit tests.

## Actual evidence and remaining gates

Focused tests use a real in-process loopback HTTP fixture server with fictional Unicode data and separately inspected server state. They cover initialization/session headers, bounded JSON/SSE, no effect before approval, exact target/schema/descriptor checks, one call after repeated approval, independent fixture storage, disconnection, cancellation, restart fencing, result/ledger limits, dripped headers, blocked DNS, owner/hidden-state and planner-bridge behavior. They also include deliberately scripted clients for fault injection. A local HTTP fixture is protocol/storage evidence, not external application or TLS acceptance.

An actual production-transport metadata inspection of the officially documented anonymous OpenAI docs endpoint was attempted on 13 October 2026. It stopped before connection with `CONNECTOR_PUBLIC_DNS_REQUIRED`; the read-only diagnostic was `gaierror`, errno `-3`, temporary name-resolution failure. No live tool descriptor, search call, external result or configured live grant was obtained. The proposed harmless query was “Responses API streaming”; it was not sent. No DNS/network workaround was used. Evidence is in [connector QA](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/output/qa/2026-10-13-mcp-connectors/verification.md).

Next live gate: in an already authorized network environment, inspect the public endpoint through this adapter, review its actual descriptor/schema and identity, configure one temporary read-only grant, approve the exact harmless query, and check the returned documentation. Separately test a genuinely needed application and independent outcome verifier before claiming cross-app writes. Authenticated accounts, generic desktop/LCU control, private data, real-model planning quality and consumer-product parity remain unproven.

## Primary sources and research basis

Official MCP pages were checked on 13 October 2026: [tools and untrusted annotations](https://modelcontextprotocol.io/specification/2025-11-25/server/tools), [Streamable HTTP](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports), [lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle), and [cancellation](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/cancellation). They define a protocol, not application permission or independent outcome verification.

OpenAI's [Docs MCP guide](https://developers.openai.com/learn/docs-mcp) describes documentation search/read at `https://developers.openai.com/mcp`; its [MCP connections guide](https://developers.openai.com/api/docs/guides/agents-api/tools/mcp) explicitly identifies anonymous access. This docs-only server does not confer model API, account, consumer dot or private application access.

The existing [Muse](../../research/2026-10-12-personal-agents/muse-capability-gap.md), [dot](../../research/2026-10-12-personal-agents/dot-capability-gap.md) and [Grok Bot](../../research/2026-10-12-personal-agents/grok-capability-gap.md) studies motivate reusable mediated tools and durable results. This adapter reuses their public design lessons; it neither copies private implementations nor converts model/API support into consumer-product equivalence.
