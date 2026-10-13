# Active integration status · 2026-10-13

This is an in-progress engineering checkpoint, not completion or live commercial-agent parity.

## Root integration implemented

- Runtime initializes public browser and default-off MCP connectors before durable runs, installs the typed connector registry and the run-origin local mutation transaction guard
- Application lifecycle includes connector worker/shutdown; optional operator-owned JSON config uses DESK_MCP_CONFIG_PATH, empty by default
- Owner-only exact connector review routes use real session cookies, strict approval version/hash/public acknowledgment; metadata-only listing/cancel responses omit content
- Chat can explicitly hand a draft goal to Work without clearing the original chat text or starting a run; browser review routing is privacy-epoch fenced
- Run-origin artifact publication checkpoints occur at reservation and final link under a short write transaction; control/context revocation blocks publication and attempts cleanup only of the current unpublished temporary file

## Focused checks so far

- 90 existing artifact, owner HTTP and MCP protocol tests passed on the then-current development snapshot
- Root owner HTTP connector tests: 4 passed, covering default-off, unauthenticated rejection, exact approval hash/version/ack, no duplicate execution, metadata projection, hidden cancellation, session rotation and rejection of public impersonation of assistant confirmation receipts
- Root connector HTTP plus run publication/draft fence checks: 8 passed
- Root-modified backend files pass Ruff
- Worker and independent reviewer checks continue; aggregate build, exact candidate freeze, publication and live UI acceptance are not claimed here

## Environment facts

- No configured model credential or spending limit; owner clarified no model selection is final and prior GitHub research should guide candidates
- Official anonymous OpenAI docs MCP discovery was attempted by the connector worker, blocked by DNS before connection; no live descriptor or response was obtained
- The supported cloud browser is present. A self-checking loopback fixture returned HTTP 200 in its owning exec process before/during browser check; a fresh cloud tab received ERR_CONNECTION_REFUSED. This demonstrates failed reachability for that pairing, not a diagnosed topology or a FYP adapter failure
- No public exposure, DNS/VPN/security modification, private profile use, paid call, new credential, main merge or deployment

An intermediate aggregate backend run passed 639 tests; this preceded final dispatch/receipt fixes and is not release evidence. Independent connector and durable-run audits subsequently reproduced and rechecked their reported issues. Final integrated source freeze/checks remain pending here.
