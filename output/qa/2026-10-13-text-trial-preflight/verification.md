# Offline text-trial preflight verification

Date: 2026-10-13 UTC. Group 2. Isolated new source slice, continuing the inherited 186-document intake. No Git, merge, deployment, live provider, account, billing, credential, real-runtime, audio or hardware action was taken.

## Result

- 46 focused tests passed
- 138 tests passed across the focused slice plus existing text-response and provider-policy suites
- Ruff passed on all three new Python files
- Both normal supervised CLI examples completed with `offline_preflight_passed`, `live_acceptance: not_run`, zero network requests, one mock POST and no dispatch/persisted draft
- Independently tested exact production payload equivalence and adversarial boundaries are reported separately in [the audit directory](../2026-10-13-text-preflight-audit/)

These are software/mock results. The capacity batch's earlier 909 backend / 194 frontend full checks are separate historical evidence. No new aggregate backend/frontend or actual application browser/model acceptance is claimed by this focused record.

## Reproduction

From `desk-companion/`, using installed dependencies and an empty test environment:

```sh
/usr/bin/env -i .venv/bin/python -m pytest tests/test_text_trial_preflight.py -q
/usr/bin/env -i .venv/bin/python -m pytest tests/test_text_trial_preflight.py tests/test_text_response_bounds.py tests/test_provider_policy.py -q
/usr/bin/env -i .venv/bin/python -m ruff check backend/desk/text_trial_preflight.py scripts/check_text_trial.py tests/test_text_trial_preflight.py
```

See `focused-tests.txt`, `regression-tests.txt` and `ruff.txt`. Example CLI commands are in the [specification](../../../desk-companion/docs/text-trial-preflight.md). `gemini-offline-preview.json` and `qwen-offline-preview.json` use fictional `fixture-model` and synthetic workspace identifiers; neither selects the owner's final provider/model. The reports include only fixed synthetic payloads and omit fixture authentication headers. The actual command supervisor invokes an empty-environment Python `-I` child.

## Exercised boundaries

1. Existing guarded production serializer/parser paths for both provider families; actual outgoing 1,600-token fields, protocol/non-streaming flags and 16 KiB body cap verified
2. No credential loader, environment-sourced config, network transport, socket connect or conversation dispatch; no real runtime and no filesystem-backed database
3. Rejected provider/channel/model/endpoint inputs, changed URL/method, missing/altered output caps, streaming/thinking/model drift and oversized actual serializer output
4. Second transport request rejected before another fixture response; 302/401/403/429/500, malformed structure/JSON and oversized provider response stop with no retry
5. Narrowed production `TextPlan`; only exact synthetic title/UTC/explicit boolean follow-up-disabled arguments; other tools, additional keys, approvals and false-like integer rejected
6. Configuration revision change between guard and transport rejected before send
7. Real blocked subprocess killed and reaped by watchdog test; normal CLI launches pass under adversarial dummy inherited key/model/proxy/Python settings, with no secret echo
8. Each preview receives a distinct empty in-memory accounting database, closed afterward; no tool dispatcher is available and nothing is saved as a task/draft

## Remaining gates

Live transport is intentionally absent. Future work must separately obtain exact destination/model/data and spending approval, permitted account/region access, appropriately approved secure credential setup and a reviewed one-call live integration. Its semantic output and independently read-back unapproved draft still require actual evidence. No mocked usage/cost is interpreted as actual accounting; local timeout is not a provider billing cap. Voice remains outside this slice.

Only the new standalone spec, source, tests and this QA directory were authored. Production adapter/privacy/provider-policy/config files, root shared documents, capacity source, UI and assets were not changed. The parent owns root integration and publication. `source-manifest.json` pins the four authored source/spec files; `reading-ledger.json` records supplemental reads and inherited intake rather than claiming another full read.
