# Independent capacity interface audit

Completed 2026-10-13 (UTC), on the cloud workspace only. Application source and repository tests were read-only for this reviewer. The existing 186-document intake was inherited; focused rereads covered AGENTS.md, product.md, handoff.md, the latest decisions and `../../2026-10-13-work-capacity-design/contract.md`. The UI owner confirmed the lifecycle source freeze before review and separately notified completion of the compact presentation refinement.

## Result

**33 independently authored executable cases pass; no unresolved finding.**

Run from the repository root:

`node output/qa/2026-10-13-work-capacity-audit/frontend/audit.mjs`

- [Executable audit](audit.mjs)
- [Results and exact production source SHA-256 values](results.json)
- [Post-test source stability check](source-stability.json)
- [English SSR fixture](capacity-full-en.html), [Chinese SSR fixture](capacity-full-zh.html)

## Finding fixed during review

A confirmed capacity authorization/privacy denial revoked the shared ResponseFence and masked private Work data on the next render, but previously rendered RunDetail linked-review callbacks could still call the parent proposal, browser-job and connector-intent handlers. Both RunWorkspace navigation boundaries used a captured `fresh` value without checking their captured shared-fence epoch.

Independent reproduction: load a private Work detail; retain its three linked-review callbacks; refresh capacity; reject that request with status 403 and PRIVATE_CONTEXT_HIDDEN; invoke the retained callbacks. Before the fix, all three parent handlers received the old private IDs. The first audit run was 22 pass / 1 fail.

The UI owner added `fence.accepts(epoch)` guards to both `go()` and `commit()`. The same independent case now passes, including callback invocation before relying on another render. The ordinary-capacity-failure case continues to preserve scope freshness, composer identity and existing action availability.

## Executed coverage

- Capacity hook opening and explicit refresh call only `/work/capacity`, introduce no timer/poll/provider operation, and reject malformed dimensions rather than inventing zero usage
- Reordered successes; reordered same-epoch access denial; old-identity denial after a new identity; A→B→A, hide→show, stale→recovery, offline/session/context events and unmount; stale refresh callbacks cannot revive counts or issue a new capacity request
- Actual auth/session/owner/private/context denial invalidates the shared private-view fence; ordinary unavailable/409/503/transport errors leave it intact and render unavailable
- Actual Work entry permits the private workspace only for a current visible owner; paired/display/device-agent/offline/stale entries cannot mount it; hidden owners retain their separate metadata/stop controls
- Work capacity-only failure leaves the same scope and composer key intact, without introducing unrelated scope requests or clearing the draft
- Actual composer preserves exact watched task IDs, scope revision and retention review through full/unavailable capacity; no provider or voice authority is inferred
- Actual PrivateWriteQueue and usePrivateMutation preserve the exact serialized body and X-Operation-Id for an unknown voice-origin creation retry after voice expiry; no fallback to a fresh typed-work operation occurs
- Actual source selection, retention and upload queue survive full/unavailable capacity. Selecting does not read/upload. Unknown retry sends the exact original body/key without rereading the selected file
- Actual RunDetail pause and independent cancel remain available. An unknown pause can be retried with its original key and does not disable cancellation
- Actual artifact preview/readback and byte/hash-verified download execute through fixture transports with no capacity gate; download bytes match the retained fixture
- Actual visible and hidden watch workspaces use their existing complete list count and do not request capacity. Cancelling a watch leaves 1/20 saved definitions and 19 slots remaining
- English/Chinese React SSR covers full, unavailable and over-limit states without NaN/null/false-zero meters; per-run figures explicitly remain limits rather than current usage; fewer-than-two output warning is advisory
- Native collapsed storage summary exposes full/unavailable/over-limit warnings before expansion; known sizes use KiB/MiB and retain exact byte counts when rounding would hide precision

## Evidence limits

The harness transpiles and executes current production modules using the already-installed TypeScript compiler. It supplies deterministic React hook slots, event targets and deferred HTTP transport fixtures; it does not replace the production capacity hook, mutation queues or callback logic with a copied algorithm. A test-only export exposes the existing RunWorkspace function without editing production source. React's actual server renderer produces the HTML fixtures.

This establishes software lifecycle, callback, rendered-copy and fixture-transport behavior. It does **not** establish real DOM interaction, 390px/desktop visual fit, actual browser download completion, real HTTP/backend operation success, model semantics or target-machine behavior. The CSS is wrap-friendly by inspection; visual acceptance remains separate. Existing Work/Watch polling remains, but capacity adds no polling loop. The endpoint/UI slice is global-only; no current per-run reservation usage is inferred from the selected artifact list.

No Git, Mac, live service, model, credential or application-source operation was performed by this reviewer. Root owns integration-wide verification, documentation and publication.
