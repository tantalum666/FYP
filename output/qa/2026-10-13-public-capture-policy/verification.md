# Exact URL and static-text policy verification

13 October 2026, ongoing cloud continuation. Owned changes only: new policy module, focused tests and this QA directory. Shared contracts, lifecycle, transport, schema, source writer, UI and Git remain their respective owners' responsibility.

- Revised implementation-plan SHA256 verified: `8ca6025fb7dee4b5c7f05f3756aa433fea7b364b3a1a9be71641f9d35184eee9`
- Focused suite: 96 passed; Ruff passed on both owned Python files
- No network call, credential, actual user record, model, new dependency, browser, runtime enablement or Git action

## Implemented contract

`validate_url` returns immutable exact URL/host/path without normalization or DNS. Strict immutable request models reject extra fields, coerced boolean/integer acknowledgments, control-bearing labels and unsupported literals. Code-owned intent binds capture ID, generated filename, original session/privacy revision, URL, label, retention, disclosure, extractor and network policy; canonical digest is stable. URL validity remains syntax only, not proof of public access or absence of a private token. Known credential-link patterns are conservatively rejected.

`validate_mime` admits plain/Markdown/HTML with absent or UTF-8 charset only. `extract_static_text` accepts bytes and an authority checkpoint, returns immutable extracted bytes and a frozen acquisition record with independently tested raw/extracted hashes/counts and static-only/raw-not-retained limitations. Capture identity, exact URL and received time are intentionally added only by the service's trusted provenance adapter. No client request accepts provenance.

HTML uses the standard-library parser with a strict balanced stack, explicit HTML void tags, suppressed hidden/head/script/style/template/noscript subtrees, no link/attribute fetch or rendering, and no browser-style optional-close repair. Nonvoid self-closing tags, mismatched/truncated tokens and malformed declaration/attribute/end-tag cases fail. Block boundaries become LF; HTML horizontal whitespace collapses, while plain/Markdown text and qualifiers are preserved. All output lines terminate with LF, whose byte counts are included in the 1,024-byte cap. Unicode wrapping never splits a codepoint and prefers the last fitting whitespace; U+0085/U+2028/U+2029 and CR/CRLF become LF. Other control separators fail. Total raw/output/depth/events remain 128KiB/24KiB/64/20,000. Input validation/parser feeds are checkpointed per 1,024 characters, parser events per 32 events, wrapping per line/segment, and return is checkpointed. A focused small-input test confirms cancellation inside the event loop.

## Limitations and gates

Strict HTML deliberately rejects many browser-repaired documents. CSS-hidden text, generated content, login/paywall meaning and completeness cannot generally be established. A short fixed set of recognized challenge markers fails closed; this is not comprehensive authentication detection. Input schemas and acquisition types are pure policy, not owner authorization or durable lifecycle enforcement. Production HTTP/TLS/DNS, lifecycle/storage publication, source/Work integration, aggregate tests, mounted UI and real public acquisition remain separate evidence gates.

## Independent audit correction

The independent reviewer reproduced visible-prefix success when HTML ended with an unterminated quoted tag or comment, including 120KiB tails. Python HTMLParser.close repairs/discards these tails, and this interpreter also privately queues incomplete-token chunks. The extractor now feeds each already-bounded chunk directly through standard-library non-EOF parsing and checks the remaining lexical tail before close. It fails closed on incomplete tags/comments/entities rather than publishing a prefix. Nine new regressions cover the failures and complete 120KiB attributes/comments, which still parse successfully. Revised focused suite: 96 passed; Ruff passes. Independent recheck is separately owned.

Subsequent independent review also found HTMLParser's direct comment path bypassed declaration checks. The coordinator added a strict parse_comment override and nine permanent regression cases; the final321-case transport/policy audit passed with stable hashes. See [independent final audit](../2026-10-13-public-capture-transport-policy-audit/review.md) for superseding source hashes and precise scope.
