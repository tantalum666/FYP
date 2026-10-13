# Exact public URL capture: independent interface audit

13 October 2026. Same ongoing 186-document intake, supplemented by `reading-supplement.json`. This auditor wrote QA files only; application fixes belong to the implementation owner. No Git, live public GET/DNS, browser, user database, actual account, settings or migration was used.

## Findings and disposition

1. **F1: local review approval had only a wall-clock guard.** Actual production hook approved a review after the browser wall clock moved behind its original observation. Reproduced in `audit-initial.log`. The server's independent clocks remained authoritative; the finding does not establish an unauthorized external GET. Fixed by a per-ID/intent non-extending browser review window, maximum five minutes, using wall and monotonic clocks with irreversible rollback/expiry. The approval callback checks the window at invocation; reopening cannot renew that window. Independent rollback and frozen-wall/elapsed-monotonic regressions now pass.
2. **F2: a reordered source-preview denial could leave newer private content visible.** Actual SourcePreview callbacks: page-one success, page-two pending, return to page one, newer success, older 403. Previously the sequence filter ignored the denial. Reproduced in `audit-second.log`. Fixed by live same-epoch denial revocation independently of response ordering, clearing preview data and masking metadata/provenance; paging callbacks and request entry check the original mount epoch. Independent regression now passes.
3. **F3: acquisition display omitted retained-extraction evidence.** The real backend fixture's extracted SHA-256 did not appear in capture details, despite being validated and stored. Reproduced by actual React server rendering in `render-initial.log`. Fixed with compact plaintext capture ID, HTTP/charset, extracted digest/count/lines, accepted static coverage and explicit freshness/authenticity/rendered completeness limitations. Independent real-fixture bilingual SSR now passes.

A related draft hint now names upload/capture preparation and original-operation recovery. The hook also synchronously binds its privacy epoch so old state cannot be exposed before effect cleanup when its epoch changes.

## Executed coverage

`audit.test.ts` runs the actual production capture hook and component callbacks using a minimal deterministic React hook harness and synthetic API promises. It includes 13 original owner scenarios plus six independently added scenarios; no regex-only substitutes for lifecycle execution. `render-audit.test.ts` runs actual React SSR, with only the API hook replaced by fixture state: four original scenarios plus the independently added full real-wire provenance check.

- Capability defaults off; disabled capability still permits retained history, local reconciliation and stop
- Volatile URL/label and explicit local review retention; separate exact URL/public assertion and snapshot retention; duplicate-submit lock
- Original prepare and approval operation recovery, identical body/key, no automatic replacement, no automatic source selection or Work creation
- Hidden scalar-only list/detail/stop, reject private extra fields, no private URL/source/acquisition projection or preview/reconcile
- Queued refresh issues only a saved-status GET; no second approval or new operation key
- Session/privacy/offline event revocation, A→B→A epochs, stale freshness, unmount, old reordered access denial and invalidated review callbacks
- Visible cancellation strictly decodes metadata-only output and rereads private details only while the same visible authority remains valid
- Dual clocks and non-reviving review expiry; cancelled capture state kept independent of verified retained-source status
- Both languages, escaped hostile label, no anchor/image/iframe/script/link element from capture content, unknown provenance fails closed
- Acquisition shows service-owned exact URL/received time/MIME/charset/HTTP/raw and extracted evidence, no raw archive, unknown rendered coverage and no invented freshness
- SourcePreview remains plain pre/text, with the independently exercised late-denial fix

`wire-fixtures.py` invoked the actual backend service with a synthetic injected transport and real temporary SQLite/source files. It generated prepare, queued approve, verified detail, list, reconcile, metadata-only and cancellation responses. All tested client decoders accept these actual service shapes. Exactly one synthetic client GET was recorded. This is not public-network evidence or an independent HTTP route test.

## Integration and remaining acceptance

Read the full changed RunPanel, RunComposer, SourcePreview, local types and CSS. Capture intake sits beside existing upload; history is available in the main Work panel and metadata-only hidden mode. Existing source selection remains explicit, and draft guards compose capture/upload/Work dirty state. Parent identity includes owner/session, API origin, settings revision and private/metadata mode with keyed remounting. CSS retains wrapping/min-width behavior. No A1/DeviceApp source is part of this frontend change manifest.

This audit does **not** establish mounted-browser layout, focus/keyboard/touch behavior, narrow EN/ZH geometry, actual A1 overlay interaction, actual browser-save output, public DNS/TLS compatibility or model quality. Those remain separate acceptance gates. Whole-project protected-asset hashes and backend aggregate tests are owned by the coordinator.

## Final verification

Final frozen hashes, command results and before/after stability are recorded in `verification.json`. The initial failing logs are intentionally retained. QA scripts use repository-specific absolute paths and synthetic bytes only.
