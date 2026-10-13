# Independent offline text-preflight audit

Completed 2026-10-13 08:27 UTC. Audit-only worker; no application source edits, network calls, provider/model calls, credential/account activity, installations, Git operations or actual runtime data access.

## Result

No blocking defect found in the frozen implementation or its claims. A combined isolated run passed **190 tests**: 138 implementation/adapter/policy tests plus 52 independent adversarial checks. This is offline software evidence only, not live provider/model acceptance, semantic quality, account eligibility, draft persistence or a billing guarantee.

Command from repository root:

```sh
env -i PATH=/usr/bin:/bin desk-companion/.venv/bin/python -I -m pytest \
  -c desk-companion/pyproject.toml \
  desk-companion/tests/test_text_trial_preflight.py \
  desk-companion/tests/test_text_response_bounds.py \
  desk-companion/tests/test_provider_policy.py \
  output/qa/2026-10-13-text-preflight-audit/test_independent.py -q
```

Exact result: [test-result.txt](test-result.txt), 190 passed in 5.57 seconds. [Independent checks](test_independent.py) and [focused reading/source fingerprints](read-and-freeze.json) are retained. This continues the existing 186-document intake; it is not a new full-repository audit.

## Independently checked

- Both provider payloads are byte-for-byte and SHA-256 identical to direct production `TextAssistant.generate` using the same fixed system/context/narrow schema and a separate mock transport
- Socket construction, connection, DNS resolution, default HTTP transport, environment credential loading, personal/business projection and reply dispatch are forbidden by sentinels while both previews still pass
- SQLite connection may only be `:memory:`; production runtime is not constructed; reports say zero network requests and no persisted task/draft
- Twenty-two hostile endpoint variants, ten invalid model forms, and six malformed/secret-bearing CLI cases reject before capture and without echoing the marker; no key/live option exists
- Re-entrant invocation admits no second fixture response; extra attempts fail closed; no redirect or retry in production serializer path
- Exact 16 KiB request accepted, one-byte-over rejected before response; actual 1600 output-token caps and streaming/thinking protocol values are checked
- Exact 128 KiB streamed raw response accepted, one-byte-over rejected and stream closed; malformed responses, oversize bodies, compressed bodies, timing checks and HTTP errors fail without retry
- Fixed title, UTC and strict false follow-up arguments only; malicious provider fixture tools fail before dispatch; per-call checkpoint state restored on failure
- Supervisor uses empty child environment, `-I`, no stdin, discarded stderr; actual timeout test confirms blocked worker killed and reaped
- Documentation accurately limits the 45-second guarantee to the supervised child, acknowledges process/OS latency, and explicitly excludes arbitrary-code sandboxing, live quality, provider cancellation, billing caps and actual persisted drafts

## Scope and remaining gates

No requested fix was necessary. CLI success reports a local serializer/guard preview with fixed mock output. A future live runner remains separately reviewed and needs provider/model/destination, exact data and spending approval, eligible account and secure credentials. This audit does not authorize those actions. The public `offline_preflight` function and internal `--offline-worker` mode intentionally lack an external watchdog when called directly, as documented.

Application/user-facing documentation and project handoff updates remain with the implementation/coordinating worker. This audit wrote only its QA directory.
