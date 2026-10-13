# Independent exact-URL transport and pure-policy audit

13 October 2026. Ongoing 186-document intake inherited; relevant full-text supplement recorded in `reading-supplement.json`. This reviewer edited only this QA directory. Implementation owners and the coordinator made the source corrections below. No Git, installation, real user store, credential, model/provider call, external DNS or public request. Parent expressly allowed isolated synthetic loopback HTTP fixtures; the unchanged MCP suite uses those. Byte-socket fixtures are not live TLS acceptance.

## Result

**Pass within the transport/pure-policy scope after three reproduced corrections.** Final focused aggregate: **321 passed**, comprising 83 independent fixtures, 77 transport tests, 96 policy tests, nine coordinator regression tests and 56 unchanged MCP tests. One pre-existing MCP pytest warning concerns an empty exception-message regex, not a test failure. Ruff passed. Eight source/test files have identical before/after SHA256 values in `frozen-before.json` and `frozen-after.json`; `hash-stability.json` records the comparison.

The lifecycle, schema migration, immutable-file publication, API response privacy and mounted UI are independently owned and are not certified by this review. No feature was enabled here.

## Reproduced findings and corrections

1. **Unfinished HTML lexical tails silently became successful prefixes.** Original policy hash `0bf69ad9…` returned `visible\n` for `<p>visible</p><p a="xxx`, an unfinished comment, and an unfinished quoted attribute with 120,000 trailing characters. HTMLParser EOF repair discarded these tails; this interpreter additionally defers incomplete-token chunks. The policy owner changed bounded feed to non-EOF standard-library parsing and rejects remaining lexical data before close. Independent tests now reject all such tails and allow complete large attributes/comments. Original small observed outputs are faithfully recorded in `initial-defect.txt`; the first independent pytest run happened after the owner had already corrected the defect.
2. **GET write inherited the pre-TLS timeout.** Original transport hash `b23832c8…` retained a three-second socket timeout when a simulated TLS handshake left only 0.1 seconds of a three-second total budget. `send-timeout-probe.txt` records the failing independent assertion. The coordinator refreshes timeout after dispatch/check and immediately before the fixed GET. The regression passes. TCP→TLS refresh, TLS failure cleanup and cancellation at TCP/TLS/send/header/body phases also pass. This does not promise forceful termination of stuck OS operations.
3. **Malformed comments bypassed declaration checks.** The revised parser still accepted leading `>`/`->` comment text and noncanonical `--!>` closes. The coordinator's initial declaration-only check was insufficient because this HTMLParser directly calls `parse_comment`. A direct strict comment override now enforces canonical termination before the permissive parser can repair it. The three definite malformed forms and 30 feed-boundary permutations fail closed. Ordinary embedded `>` and a single trailing-hyphen comment remain valid. `comment-and-send-probes.txt` preserves the earlier failures. The coordinator added nine production regressions. No reviewer source edits occurred.

## Transport evidence

- Every resolver answer is checked for capture public-unicast admission before selecting the pinned address. Mixed private/global, benchmark, multicast, scoped, malformed and mapped-private answers fail. Public mapped IPv6 requires both the outer and mapped address checks. One shared DNS slot is verified across capture and MCP; blocked/cancelled resolution does not produce a late connection or unbounded replacement queue
- Capture uses numeric socket.connect, avoiding the implicit second resolver pass. Fixture evidence independently verifies selected address, original Host/SNI and certificate-validating default context construction. It is not evidence of a real certificate handshake
- Fixed one-GET request bytes have no body, ambient cookie/auth/proxy data or owner label/context. Failure and cancellation produce local close only; no retry, second GET, redirect, alternate address or MCP cancellation notification
- Raw status/header fixtures verify all interim statuses are rejected before normalization, CRLF is required, folded/invalid fields fail, duplicate framing/MIME/encoding fields fail, every transfer encoding/upgrade fails, and disallowed encoding/MIME/charset/length/overflow/truncation fails
- The conservative shared 16KiB read-ahead guard remains. Near-boundary valid headers can be rejected because buffered body bytes also count during the header phase; this is deliberate and not exact syntactic-header acceptance
- Slow-drip headers/body respect checkpoints and monotonic budget. TCP/TLS/write/read phases have finite timeouts capped at three seconds and refreshed from remaining budget at their boundaries. All exercised terminal paths close local socket/response resources
- The mechanically extracted MCP behavior remains distinct: POST/JSON/SSE, original CONNECTOR error codes, server-notification restrictions and best-effort cancellation are preserved. The unchanged 56-case loopback/protocol suite passes; an independent byte fixture confirms MCP still accepts 100 Continue followed by valid JSON while capture rejects it

### Exact frame versus socket EOF

The accepted representation is **exactly the single Content-Length frame**. Four independent fixtures append extra bytes, a second complete response, NUL or CRLF after that frame: capture retains only the declared body and closes locally. It does not wait for or validate connection EOF, and does not certify absence of surplus/pipelined bytes. Truncation before the frame completes fails. This is a deliberate narrow HTTP framing statement; documentation must not describe it as complete wire-stream equality or surplus-byte rejection. No extra request is issued and no following response is interpreted.

## Pure-policy and parser evidence

Strict URL grammar rejects credentials/userinfo, ports, encoded/numeric hosts, reserved/private forms, ambiguous paths, query/fragment and unsupported characters without DNS. Known secret-link patterns are defensive heuristics, not proof the URL contains no secret. Frozen strict request/intent/acquisition models reject coercions and extra authority fields. Independent digest tests vary capture identity, URL, label, session and privacy revision separately.

Golden extraction covers strict UTF-8, Unicode-codepoint line wrapping, LF-included 1,024-byte limits, U+0085/U+2028/U+2029/CR/CRLF citation alignment, 24KiB output and 128KiB raw caps, depth/event bounds, hidden/script/template/attribute content, malformed syntax and ordinary negations/qualifiers. Remote instructions and links remain untrusted text; fixtures forbid DNS/socket calls during extraction. No implicit approval/link-following path exists in these pure modules.

`parser_stress.py` exercises 11 adversarial inputs up to 131,072 bytes: long whitespace, complete/incomplete attributes/comments, repeated attributes, slash tokens, huge entity names, quote/backtracking-shaped text, event overflow and output overflow. Final measured maximum elapsed time was **0.643 seconds**, maximum observed checkpoint interval **0.146 seconds** on this cloud interpreter. Large complete tokens succeed; malformed/event/output cases fail appropriately. Separate fixtures cancel during large-token parsing after validation has completed. No hang was reproduced. These measurements are not a general linear-time proof or target-device latency guarantee: standard-library regex work for an individual accumulated token is bounded by the raw-input cap rather than forcibly preempted inside a regex. Input cap/chunk/event checkpoints must not be relaxed on the strength of these fixtures.

## Evidence and rerun

- `test_independent.py`: 83 independent scenarios
- `final-tests.txt`: final 321-case aggregate and warning
- `parser-stress.json` / `.txt`: exact measured timing/checkpoint results
- `ruff.txt`: source and QA Python lint
- `pre-corrections-hashes.json`: superseded intermediate freeze
- `frozen-before.json`, `frozen-after.json`, `hash-stability.json`: final scope stability
- `collection-path-error.txt`: one test invocation chose the repository root config and could not import desk; corrected with explicit project config and PYTHONPATH before final execution. This was a harness collection error, not a product failure

Rerun from repository root with existing environment only:

    PYTHONPATH=desk-companion/backend desk-companion/.venv/bin/pytest -q -c desk-companion/pyproject.toml desk-companion/tests/test_public_capture_transport.py desk-companion/tests/test_public_capture_policy.py desk-companion/tests/test_public_capture_review_regressions.py desk-companion/tests/test_mcp_connectors.py output/qa/2026-10-13-public-capture-transport-policy-audit/test_independent.py

The coordinator owns shared product/handoff/decision/work-log updates and any publication. This audit supplies evidence; it does not claim public-site success, usable-release acceptance, rendered-page completeness or mounted UI validation.
