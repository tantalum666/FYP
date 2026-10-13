# Exact URL capture planning QA

13 October 2026. Planning only; no implementation tests or live calls are claimed. The initial record below is historical to the first draft; the independent-review revision at the end supersedes its unresolved schema-policy note.

- Inherited the coordinator’s same-task 186-document reading evidence at `output/qa/2026-10-12-agent-kernel/reading-union-status.json`
- Read AGENTS, product, handoff and the prior public research design; inspected source/file-store/provider policy, MCP transport, browser boundary/worker, capacity, current publication checkpoint and upload UI seams. Truncated contract/design output was supplemented in bounded ranges
- Draft remained outside the repo until coordinator confirmed the frozen watch payload was captured (75 files; expected tree `7d008c23776314e1c876a76c8f17ecc1b04c63de`). Its reported test counts are not this planning task’s test results
- Changed only `planning/2026-10-13/exact-url-capture-implementation.md` plus this own QA directory. Existing research design, application source, root contracts, configuration, assets, runtime data and provider/network settings were not edited
- Proposal includes exact owner review/API, bounded lifecycle schema/dedupe, one-possible-dispatch marker, no-refetch recovery, late-cancel/publication fences, strict Content-Length-only GET admission, trusted source provenance, parser bounds, retained-history/source capacity and independent offline/UI/live gates
- Identified real caveats: review itself retains URL metadata; old `put` callback cannot expose a not-yet-created source ID; at-capacity recovery must not double-count an existing reservation; source cleanup is absent; additive database schema/version policy needs independent review before implementation
- Prior maintenance-first wording applies to broad/recurring release; bounded manual capture is explicitly permitted by that design. Exhausted/unknown source capacity and unusable preview/output are genuine gates, not reasons to weaken protection
- No model, account, price or public site claims were researched externally; this task made no DNS/HTTP/browser/provider request
- Internal link resolves to the existing research design. All code paths cited in the proposal exist at inspection time; new module names are clearly proposed
- Root owns independent review, shared product/handoff/decision updates and any future implementation/publication

## Independent-review revision

Read the full 77-line independent review at `output/qa/2026-10-13-exact-url-plan-review/review.md`. Revised only this proposal and own QA. No application tests, live requests, schema migration or source edits were performed.

- Added capture-only explicit public-unicast/mapped-address checks while preserving mechanical MCP extraction behavior
- Added capture-only status-line/raw-header admission before stdlib hides 100 Continue; byte-level tests and conservative header read-ahead cap retained
- Selected global schema 3; fresh fixtures versus separately authorized offline 2→3 migration, no watch-flag reuse, strict missing/partial-schema failure even disabled, staged schema-1 path
- Split final-link recovery: nlink=2 remains unknown/manual maintenance; single-link matching final bytes can receive existing independent fsync/readback
- Named minimal transaction-aware admission/key lookup; validate identity/hash/provenance, charge new reservations once, never rerun ingestion for reconcile, keep full-capacity/unrelated-corrupt-bucket recovery available
- Added fresh read-response privacy rechecks, scalar hidden cancel with damaged private JSON, conservative dispatch race wording, local-only cleanup, bounded parser checkpoints/Unicode line separators and explicit provenance preview
- Review findings are adopted as design requirements; reviewer probes remain evidence about current seams, not capture implementation acceptance
