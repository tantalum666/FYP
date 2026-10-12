# Browser workflow UI verification

Date: 12 October 2026 UTC. This is the second-batch local implementation record, not live StackEdit acceptance or publication evidence. The first published checkpoint is `546734273c9c8305cf6226e96a8e07854ba5c0b1`; this additive UI has not been pushed by this worker.

## Scope delivered

- Dedicated English/Simplified Chinese **Browser workflow** button and modal; no new long browser section inside the chat transcript
- Backend-owned fixed Python documentation source catalog, current capability readiness, explicit unavailable/experimental state, bounded real observation title/heading/excerpt/time/hash, title and public/synthetic note form
- Exact immutable review of title, generated document name, source, destination, environment identity, adapter/catalog version, full Markdown and intent SHA-256; owner approval includes current job version/hash and explicit public-only scope
- Job list pagination, selected job detail, persisted state transitions, review expiry, cancellation, unknown outcome, independent read-only verification and verified Markdown download
- Byte verification is distinct from workflow completion and process cleanup. An unknown workflow with verified existing bytes can offer its export without claiming overall success or replaying editor actions
- Independent volatile mutation queues for preparation/approval, cancellation and read-only verification. An unknown approval response does not block stopping or checking the existing result
- Owner/session/selection response fences; current-owner/private-visible/fresh UI gates; paired screens cannot inspect private work or approve. Explicit hiding/session changes clear drafts; a transient offline/stale state masks and preserves the same-owner unsent draft in memory
- Guarded modal dismissal and job switching, preserved draft on a newer external review request, bounded plaintext previews and no executable Markdown rendering
- Export reads only the code-owned job export route, streams at most 65,536 bytes, compares recorded length and SHA-256, and rechecks current visibility/session/selection before opening or native export
- Narrow parent-approved `api.ts` change: `/browser/observations` gets a 75-second HTTP wait to accommodate the backend's 60-second supervised public read. Other existing request timeouts are unchanged

No source URL input, user browser profile, account login, provider call, arbitrary desktop action, inferred success from clicks or model confirmation was added. Browser jobs remain a separate public/synthetic experiment. This batch does not link them to the private-source/model-driven agent run workflow; optional selection callbacks are unused integration seams.

## Checks actually executed

- [Frontend suite](browser-ui-frontend-tests.txt): **75 tests passed**, including **12 browser-focused regressions**
- [TypeScript and Vite production build](browser-ui-build.txt): **passed**; existing large-chunk warning remains
- Focused tests cover unavailable/stale capabilities, target mismatch, approval expiry/version/digest shape, incomplete result receipts, byte-vs-cleanup semantics, independent cancellation, guarded navigation, exact catalog links, private response fences, real UTF-8 byte/hash verification, executable MIME rejection, oversized streamed responses, privacy revocation during streaming, volatile writes/plaintext previews and the observation timeout branch
- Independent review inspected privacy/selection/download handling and identified the final cleanup-envelope change, which the UI now matches. This record does not replace the parent’s final integrated backend review
- [Supplemental reading ledger](browser-ui-reading.json) inherits the earlier full-project reading gate and records relevant changed contracts; [owned source manifest](browser-ui-source-manifest.json) binds the frozen UI files to hashes

These tests are policy/transport/helper and source-contract regressions, not a mounted React DOM or live-browser acceptance test. The cloud browser's known launch restriction was not retried or bypassed. No installation, credentials, account access, paid provider, hardware, merge, deployment or source push occurred.

## Cancellation and retention caveats

Closing the modal does not stop a server-side approved job. Cancelling an HTTP wait is not cancellation of the supervised operation. Public observation has a bounded read lifecycle, while job cancellation uses the dedicated cancel endpoint. Stopping cannot undo an edit/export that already occurred. Recovery resends only the same immutable operation ID while its memory-only queue remains available; after closing/reloading, inspect saved state rather than recreating an uncertain write.

Downloaded files are deliberate user exports and are no longer covered by in-app hiding. Browser request routing is explicitly described as `routing_only`, not a complete OS/network sandbox. Runtime configuration admission is separate from real application acceptance; the UI makes neither claim implicitly.

## Real UI acceptance still required

In the already authorized isolated acceptance environment, verify English/Chinese, narrow/wide layout, keyboard focus and modal dismissal; disabled runtime with no calls; owner vs paired/hidden/offline views; dirty source draft navigation; double approval, stale expiry/version, unknown receipt and independent stop/check; download revocation and saved bytes. Only after the FYP-owned adapter produces a genuine StackEdit UI export should actual source observation → review → approval → export be recorded as accepted. Do not use fixture pages or directly generated final files as that proof.

Parent owns root README/architecture/handoff/work-log updates, final integration, publication and aggregate evidence. Backend worker owns `docs/browser-workflow.md` and has received the UI/operator semantics above.
