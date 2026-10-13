# Group 2 · Voice-to-Work interface verification

Date: 2026-10-13. Scope: the continuing 186-file-intake cloud engineering task, focused owner voice-input → reviewed goal → existing Work composer. No Git, provider, microphone, browser, external network, user-computer or hardware operation was performed by this interface worker. Source changes began only after the parent released the preceding search-validation freeze.

## Implemented interface

- `workspace/voiceWork/types.ts` consumes only server-normalized replacement events with session/segment IDs, increasing sequence/revision, bounded text and explicit provider-final versus unfinalized boundary. Assistant text, raw transcript display, tool arguments and turn-complete events cannot become candidates. Eight visible segments/4,000 codepoints/32 KiB UTF-8 bounds fail or visibly evict whole inputs, never select a truncated tail
- The visible owner explicitly selects one snapshot. An exact `{voice_session_ref,input_segment_id,expected_revision}` freeze request is acknowledged before the editable review opens. Repeated clicks deduplicate; failed freezes preserve the conversation and can retry the exact snapshot. Later input cannot rewrite the open editor. No freeze occurs merely by displaying a transcript
- “End voice and review work” closes speech only after successful freeze and explicit review. It copies the final edited goal plus metadata/reference, not a duplicate transcript. The composer defaults to deterministic mode only for this voice handoff. Evidence, retention, personal-context, sharing, destinations and effects begin unselected; the existing typed-chat mode preference remains
- Existing Work draft/unknown-request guards, exact operation-ID retry and search/detail freshness gates remain. Expired queued goals cannot discard unrelated drafts. Expired initial starts are blocked with an explicit notice; an already-pending exact creation request can still recover a committed receipt without a new voice connection
- Voice input and assistant display are separate; no combined display text is parsed. Unselected input/assistant display is cleared on voice end; an acknowledged child review survives for its bounded remaining expiry. Session/privacy/API-origin/configuration changes fence async results and clear candidates. Composer and freeze callbacks bind the original mounted epoch, so a captured old callback cannot dispatch in a new owner session before cleanup
- Explicit “Stop speaking” clears local playback and latches mute until “Hear speech again”. Ordinary provider barge-in only clears queued old output; it does not mute every normal Qwen utterance, and it cannot release an existing explicit mute. Audio transport checks current authority before capture sends, playback, socket-open and async startup continuations. Malformed/odd/oversized PCM closes resources without a later normal audio callback
- English/Chinese labels, escaped text, owner-only controls, provenance disclaimers and shrinking/overflow-wrapping CSS are implemented. This does not establish real narrow-screen layout, focus behavior or target-device performance

## Executed checks

Final commands run from `desk-companion/frontend`:

1. `npm test`: 169 passed, zero failures, including 17 new voice tests and the 152 existing tests; see [full output](frontend-tests.log)
2. `npm run build`: TypeScript no-emit checking and Vite production build passed; see [build output](frontend-build.log). Existing large-chunk warnings remain
3. Independent audit: actual reducer/component/hook/queue and real `VoiceAudio` methods run with deterministic protocol-fake I/O. Exact cases, counts, review findings and final hashes are in the [independent UI audit](../2026-10-13-voice-goal-ui-audit/). Its tests are not mounted-browser tests

New checked-in tests:

- `tests/voice-work.test.ts`: normalized-role/finality exclusion, immutable revisions, stale/foreign updates, capacity/UTF-8, exact freeze response and no added consent/evidence, Unicode/expiry alignment
- `tests/voice-work-lifecycle.test.ts`: explicit deduped freeze, exact retry, edited snapshot stability, dismissal, late owner/epoch/unmount rejection, safe mode defaults and stale pre-cleanup callback rejection
- `tests/voice-work-render.test.ts`: actual React server markup in both languages, no default selection, paired controls absent, escaped input, incomplete-transcription and provenance honesty
- `tests/voice-audio.test.ts`: real audio class methods with fake media/context/socket objects; explicit mute, ordinary barge-in, closed resources, late callback and invalid PCM negatives

One preexisting source-wiring assertion now checks `composeGoal?.text` and `composeGoal?.voiceOrigin` because the complete typed handoff object, rather than only a string, crosses the existing dirty-navigation boundary. The underlying dirty/fresh/unknown-request behavior is preserved and independently exercised.

## Review findings addressed

The independent reviewer identified and retested pre-effect audio privacy fencing, Unicode consistency, expired queued-goal behavior, malformed audio cleanup and stale freeze/Start callbacks. Root review identified automatic-interruption muting of normal Qwen replies; only the explicit owner stop now latches mute. A final local source check caught an active-state branch regression during refactoring; ordinary ready/audio events retain their active state, while only close/end/error transition to idle. Auth/session-expiry freeze failures immediately invalidate candidates rather than waiting for workspace polling.

## Not run / limits

No actual DOM mounting, dialog keyboard/focus test, narrow viewport inspection, real microphone permission, ASR, speaker attribution, paid provider, remote cancellation, Pi/iPhone or physical output test was run here. A hook harness executes real production callbacks but is not a browser. The independent Mac task remains a separate source-revision-specific acceptance record. No A1 asset, placement, DeviceApp layout, backend authority, provider credential, package dependency or physical stop control was changed by this UI worker.

Backend protocol/admission/real-file evidence is documented separately in [voice-work contract](../../../desk-companion/docs/voice-work.md). This UI evidence does not prove semantic speech understanding, general autonomous capability or provider-side deletion. Parent owns root documentation, aggregate release checks and any authorized publication.
