# Saved conversations and selected Work context

Integrated 31 October 2026. This is the explicit retained workspace, alongside ordinary Alice/Omni conversation. [Integration and migration contract](pr5-integration.md) is authoritative where the original PR5 design differs from the current application.

## One fact store, distinct retention choices

Current owner facts remain in `owner_memories`, with their existing correction history, expiry, supersession, aliases and deletion behavior. `PersonalMemoryAdapter` supplies fresh retained-context views of those same facts; it does not create another fact table or silently copy them. Both entry points use the current memory editor. The bound is 200 active facts and 1,000 characters per fact. Categories from original PR5 imports are preserved as attribution, not authority.

The **Saved-work privacy** dialog controls four default-off choices for this retained workspace:

- `save_text_history`: create saved threads and append explicitly sent text to a selected thread.
- `use_text_history_in_ai`: include a bounded projection of the selected eligible saved conversation.
- `use_memory_in_ai`: include confirmed current facts in retained chat; Work still requires selecting exact fact IDs.
- `share_business_context`: allow the configured retained-chat provider to read task/calendar context. Work independently selects exact records.

Configured text/voice destinations are displayed without their keys. Approved destination IDs bind channel, provider and endpoint. Selection does not call a provider or establish account availability. Normal Alice/Omni chat keeps its current context, permissions and temporary replay contract; these retained-work choices do not silently replace them. Global private-hide and authentication still govern both surfaces.

## Retained text API and UI

`POST /api/assistant/retained-messages` accepts message, language, optional task ID and optional saved `conversation_id`. It requires a visible owner. Ordinary `/api/assistant/messages` and the Omni socket retain their existing ephemeral IDs and behavior. A saved-thread ID is never passed into the live replay store.

The owner explicitly enables saving and creates/selects a saved thread. Sending then records the user/reply pair. Turning saving off leaves prior transcripts readable/deletable but refuses additional sends to a selected saved thread. It never silently changes a saved send into a temporary one. Temporary sends through this endpoint use a bounded volatile reply cache plus durable content-free send barriers, so an uncertain or expired retry does not rerun a provider or business tool.

Limits are 30 conversations, 120 characters per title, 200 messages per thread, 3,000 input characters and 4,000 saved reply characters. One turn per saved thread can be active. Reads, writes and late results are fenced by owner/private visibility, provider destination and context revision. Network I/O does not hold the privacy mutation lock. Retries preserve the original operation ID; source/identity changes do not create replacement effects.

Provider dispatch reuses the current `TextAssistant.generate` and adapters. Task/calendar/note effects use the existing assistant and job services. Retained chat only prepares effects; the same owner review cards apply them. A voice transcript is never automatically appended to a saved thread, and Work is never started by an invented provider control tool.

## Memory changes and forgetting

Fact corrections, expiry and deletion are immediately reflected in fresh retained projections. Canonical fact writes also invalidate retained-context epochs in their SQLite transaction. Corrections/forgetting exclude earlier saved messages from future context; the retained transcript itself remains inspectable until the owner deletes that conversation. Work binds only references and hashes, and rechecks selected facts before dispatch and result publication.

Deleting a fact scrubs its current body, prior revision bodies and relevant local cached copies. Memory-operation retry barriers keep a digest in place of the retired plaintext request. Repeating the original key returns current/redacted state and cannot recreate the fact; a different request under that key conflicts. Expired/cancelled memory drafts lose their payload and invalidate retained reply reuse. Confirmed business receipts remain separately inspectable until applicable forgetting cleanup; they are not a second chat transcript.

Deletion is not a forensic wipe of SQLite pages, WAL, backups, browser downloads or provider-retained data. Previously sent bytes cannot be recalled. Retained derived reports/conversations are separate resources, with explicit retention notices and their documented deletion limitations.

## Projection and API boundaries

Retained chat uses at most 8,000 fact characters and the last 12 eligible saved messages / 12,000 history characters. Work selects at most eight exact facts plus one saved conversation, with its own bounded binding and explicit derived-retention acknowledgement. Personal context is untrusted background data, never source evidence or a permission.

Owner-only endpoints remain under `/api/assistant`: `GET/POST /context-settings`, `GET/POST /memories`, `POST /memories/{id}/actions`, `GET/POST /conversations`, `GET /conversations/{id}`, and `POST /conversations/{id}/actions`. These map to current facts or the explicit retained-thread service. Current `/api/memory` endpoints remain unchanged in purpose. The normal memory editor is reused instead of maintaining two editing flows.

Current-main stores need the explicit schema 1 → 2 → 3 procedure, but no fact copy. Original PR5 stores additionally use the stopped-store memory conversion in [the integration contract](pr5-integration.md). No actual user store was converted during integration.

Tests cover retained history/restart/delete, live-current fact projection, old fact conversion/conflict rollback, consent revocation, late responses, duplicate confirmations, fresh facts and privacy fences. Protocol fixtures are not live-model, microphone or account acceptance. The full dated evidence is [here](../../output/qa/2026-10-31-pr5-repair/verification.md).
