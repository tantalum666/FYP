# Independent task-watch frontend audit

Date: 2026-10-13. Scope: cloud source and deterministic execution only. No application source edits, Git operations, Mac/browser use, live provider, external account, microphone or hardware actions.

## Result

20 independent executable production hook/callback/SSR scenarios pass. The existing 14 voice-work regressions also pass. No remaining reproducible blocker was found within this audit's coverage. The implementer's separate tests and whole-project validation remain separate evidence.

Run from repository root:

`node --experimental-strip-types output/qa/2026-10-13-task-watch-ui-audit/audit.mjs`

Results: [results.json](results.json), [stdout.txt](stdout.txt), [voice-regression.txt](voice-regression.txt). [source-hashes.json](source-hashes.json) identifies inspected source bytes; [reading-ledger.json](reading-ledger.json) inherits the same 186-document intake and records focused reads.

## Findings and retests

1. **Fixed: current-task denial failed to clear enclosing private workspace.** Originally a PRIVATE_CONTEXT_HIDDEN response while inspecting a task only set a child error; parent titles, draft and fresh controls could remain until a later poll. The API request layer did not invalidate the session globally. The fix synchronously fences denied/redacted responses and propagates them to the parent, forcing private-view removal and mutation/draft cleanup. Independently executed the real child hook plus real parent callback for both 403 denial and successful redacted projection; both pass.
2. **Fixed: authoritative task status missing from inspection.** The receipt named Status as changed, but the inspector showed other watched values without status. It now shows bilingual task status independently of watch status. Actual component callback/render test with a completed task passes.
3. Implementer also hardened stale selection callbacks while this audit ran. Independent retest captures old receipt callbacks, navigates to a new draft, then invokes the old callbacks. They cannot acknowledge, compile or open the old task.

## Independently exercised

- Owner-only entry; paired principal disabled; session event, offline and hidden transitions remove the private workspace; hidden owner entry remains available for stop controls
- RESPONSIBILITY_CONTEXT_CHANGED 409 on both read and explicit acknowledgment mutation immediately invalidates private view and clears retry authority; no repeat operation is offered
- Late responses after owner, hide→show, offline and selection changes cannot restore old results
- Hidden response projects private row fields out before React state, fetching no catalog/detail; transient errors retain same-view drafts as stale, while later parallel privacy denial clears them
- Exact IDs/fields, current scope token, explicit local retention, UTC future expiry and integer budgets are required; missing enrolled IDs never silently shrink evidence scope
- Reading/mounting do not acknowledge; explicit acknowledgment sends exact review version; unknown response retries preserve the original serialized body, endpoint and operation ID
- Old navigation callbacks cannot act on newer selection; dirty/unknown-operation guard becomes active
- Actual Work composer starts with new deterministic draft, exact enrolled IDs and no inherited voice origin, source/event/browser/connector selection, memory/conversation, provider sharing or mutation proposal grants
- Work requires independent retention, then review, then Start; outgoing scope revision is current; changed scope blocks Start; unavailable exact selections block rather than filter
- Bilingual paused/cancelled and review labels, coalescing/current-record disclosures and independence of acknowledgment versus Work
- Existing voice tests preserve origin expiry, one-origin admission/unknown retry semantics and bounded input behavior

## Evidence limits

The hook harness executes production hooks and callbacks using deterministic React hook slots and deferred transport responses. SSR checks use actual React server rendering. These are not mounted-DOM interaction, visual layout, focus/keyboard, real browser download or screenshot acceptance. Actual product UI acceptance remains pending separately. No claim is made about live model quality, broad autonomous work, real audio, owner pairing, target hardware or production rollout.

Only this audit directory was written. Root product/handoff/decision/work-log updates belong to the integrating parent and implementer.
