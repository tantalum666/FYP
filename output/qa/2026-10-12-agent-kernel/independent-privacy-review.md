# Independent personal-context and routine review

Date: 2026-10-12. Scope: new memory, conversation, provider-context, routines and corresponding frontend. Review was read-only for implementation files; findings were fixed by their owning authors. This continues the current 186-file reading round, with changed source and personal-context/routines documentation reread.

## Defects found and resolved

1. **Privacy revocation blocked by provider I/O.** `ConversationService.send` held the privacy lock across the reply call. An independent Event-blocked provider reproducer showed settings revocation waiting until after the late reply returned. The author moved network work outside the lock, retained the durable reservation, added revision/session/visibility fences and one-in-flight-per-thread admission. The same reproducer now applies revocation before provider release, rejects the late reply with `PROVIDER_CONTEXT_CHANGED`, and leaves the volatile cache empty.
2. **Private temporary replies remained visible when concealed.** The original UI bypassed private visibility for a reply without a saved-conversation ID; voice transcript rendering was unconditional. The author now gates reply/transcript/proposal rendering and callbacks, clears transient content, closes voice on concealment, and uses an identity/session/privacy response epoch. The follow-up owner-to-paired and hide/show stale-result issue is covered by the response-fence behavioral regression.
3. **Rename editor lost-update protection drifted.** The title was captured on opening, but expected version followed live polling. The author now captures the original conversation/version alongside the title, allowing the server to reject a concurrent edit rather than silently overwrite it.
4. **Deleted calendar occurrences remained available in routine results.** A stored briefing still returned a cancelled single occurrence as available with its current title. The author now checks cancellation and whether the occurrence still belongs to the series. The independent recheck confirms both detail and claim return unavailable with an empty title. Historical counts remain explicitly labelled snapshots.
5. **Late routine claim could repopulate after hide/show.** Reveal callbacks initially checked current visibility only. They now capture owner/visibility scope epoch and reject results from an earlier scope. Read generations and selected-record checks remain separate.

A later independent executor review also found that the local `Save note:` parser bypassed a new owner/hidden-context job-draft route guard. Its author propagated the principal and added a check before task reads or draft creation; this review inspected that minimal change and reran the focused suite including its new denied-role regression. No source edits were made by this reviewer.

## Checks actually executed

- Independent before/after lock reproduction: `review-lock-reproducer.log`, `review-lock-recheck.log`
- Independent before/after removed-occurrence reproduction: `review-routine-cancel-reproducer.log`, `review-routine-cancel-recheck.log`
- `uv run --no-sync pytest -q tests/test_personal_context.py tests/test_routines.py tests/test_voice_context.py`: **74 passed**, one upstream Starlette/httpx deprecation warning. Log: `review-context-routine-voice-tests.log`
- Frontend `npm test`: **50 passed**. Log: `review-frontend-unit-tests.log`
- The final source snapshot hashes are in `independent-privacy-review-hashes.json`. Review-time counts are not claims about later edits.

No live provider, real personal data, external messages, microphone, hardware, deployment or paid API was used. No competing bundle build or source modification was performed. The UI findings were checked by source inspection and unit/helper regressions, not by a browser in this review; actual browser verification is a separate delivery gate.

## Remaining limitations and open checks

No remaining concrete blocker was found in the reviewed backend snapshot. Active facts, retained conversation content, provider projection, routine count and routine result history have explicit bounds. Content-free idempotency receipts, forgotten-fact tombstones and terminal draft metadata retain indefinitely; total disk growth is not bounded. The new personal-context documentation explicitly discloses this, along with logical rather than forensic deletion and the inability to retract provider data/backups. Naively pruning receipts would re-enable old operation replay and was not suggested as a safe fix.

Full integrated CI/build and browser verification belong to the release coordinator after source freeze. Browser acceptance should include temporary-reply concealment, owner-to-paired/session transitions, hide/show while a result is delayed, and an open rename editor while another tab renames the same conversation.
