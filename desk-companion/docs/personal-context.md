# Owner-controlled personal context

This local prototype adds editable facts, optional saved text conversations and shared, bounded context for the configured text/voice providers. These are application features, not a dot product API implementation. No live provider, microphone, hardware or paid API call is required to run the automated tests.

## Defaults and setup

All four switches default off:

- `save_text_history`: allow the owner to create saved text threads and append messages to a selected thread
- `use_text_history_in_ai`: allow a bounded projection of an explicitly selected saved thread
- `use_memory_in_ai`: allow a bounded projection of confirmed personal facts
- `share_business_context`: allow saved tasks, progress and calendar context, including a selected task, model-facing task/calendar/computer-job tools and optional background task advice

Configuring a provider does not turn these on. In the owner assistant settings, review the configured provider and its exact validated endpoint, select the desired switches and save. Approval stores destination identifiers derived from channel, provider and endpoint. It never stores or returns the provider key in these settings. An invalid endpoint is not offered for approval. A changed destination requires renewed approval for that destination. `authorization_current` reports whether the current configured destinations are all approved; each actual channel independently checks its exact destination approval.

Consent changes do not make a provider request. Provider calls still require an operator-configured supported provider and the existing user action or separately enabled background-advice feature. Turning on memory does not imply permission to share tasks/calendar, and display visibility does not imply permission to send any saved context to a provider. The current user message is necessarily sent when using the configured AI chat; these switches govern *additional saved context*.

Owner authentication and visible private context are also required. Paired display/controller and agent sessions cannot read memories, saved conversations or their settings, and receive no personal or saved business projection through voice. Local calendar/task views and local rule-based assistant actions remain available under their existing permissions. Text with unavailable saved business context receives a truthful permission/unavailable notice rather than an invented empty calendar/task result.

## Facts and permission boundaries

The owner can directly create a fact, preference or decision, edit its content/category with an expected version, or forget it. Every model-generated memory change is a draft; only the separately authenticated owner decision endpoint can confirm it. There is no model confirmation tool. Sources are server-assigned `owner` or `confirmed_assistant`, not model-provided evidence claims. Facts never grant capabilities, approve an action, override a policy or establish a verified observation.

Without a configured text model, `remember: ...` or `记住：...` prepares a memory draft for review. Other language understanding remains the existing limited local-rule mode; it is not presented as a model call.

Limits are 100 active facts, 1,000 characters per fact, 30 saved conversations, 120 characters per conversation title and 200 stored messages per conversation. A text exchange stores two messages; input remains capped at 3,000 characters and saved reply text at 4,000. Capacity returns an explicit error, with no silent eviction. Only one send may be in flight per saved thread. Different-operation concurrent sends return `CONVERSATION_BUSY`.

## Retention and deletion

Temporary chat is the default. It does not persist general user/assistant text through this feature. Its reply may remain in a bounded volatile process cache (at most 100 responses) for safe immediate retries. A process restart, cache eviction or context invalidation can remove that reply.

Selecting an explicitly created saved conversation persists the text pair locally in SQLite. Turning off saving keeps older threads readable/deletable, but rejects new sends with a conversation ID. It does not silently downgrade a selected saved thread to temporary chat. A temporary chat has no conversation ID and is not attached to an arbitrary prior thread. Optional use of existing saved history is a separate switch and can remain enabled when new saving is off.

Deleting a thread deletes its local messages and invalidates cached replies; creation/delete receipts replay only current state and cannot restore deleted text. Renames and edits require current versions. Forgotten facts have their content cleared; corrections replace the content. Both corrections and forgetting invalidate derived reply caches, scrub pending memory drafts, and exclude *all earlier stored conversation messages* from future AI-history projection. This broad exclusion is intentional and conservative because an earlier assistant reply may have repeated a fact. New messages can subsequently be eligible under the owner's consent.

**Saved transcripts remain separately readable until their conversation is deleted.** Forgetting a fact does not claim to erase its earlier mentions from a saved transcript. Resolved or expired memory drafts are scrubbed. Requested task/calendar/job proposals and confirmed business records retain their existing separate review/recovery behavior, even when the surrounding chat is temporary.

Application deletion is not a forensic wipe of SQLite pages, WAL files, backups, browser copies, operating-system memory or provider-side data already transmitted. Existing data already sent to a provider cannot be recalled. Revoking/hiding context prevents further local projection and discards late text results; active voice sessions are fenced by the voice service and must be reopened after context changes. This does not promise retroactive provider deletion.

Content-free operation metadata is retained indefinitely in this prototype: operation ID, request hash, resource IDs, status/version/revision metadata; forgotten-fact tombstones and terminal draft metadata also remain. These tables have no count/age bound yet. Bounded active facts/history and bounded model projection are **not** a bounded-total-disk claim. Simply deleting old receipts would let reused operation IDs repeat effects and is deliberately not implemented. Request hashes are repeat-detection metadata, not anonymization or encryption.

## Repeat and interruption behavior

New personal mutations use hash-only request receipts and current-resource references, instead of copying private request/response text into the legacy business-operation table. Replaying an earlier fact creation after correction returns the current fact; after forgetting it returns no content. Memory confirmation is transactional and repeat-safe, including concurrent confirmations.

A send reserves a content-free receipt before model/tool work. A repeated completed send can use a matching volatile reply, or recover saved reply text and message/evidence IDs from an unchanged retained thread after restart. An uncertain pending send, evicted temporary response or invalidated context returns `ASSISTANT_REPLY_NOT_RETAINED` (410). The same operation does **not** rerun the provider or tool. Inspect saved threads/proposals/jobs to establish current state before deciding on a new request. The frontend keeps retry IDs in volatile memory, not persisted plaintext request bodies.

Provider I/O does not hold the privacy mutation lock. Revoke, edit and forget remain usable while a model request is pending. Text checks context revisions before and after each provider turn, and saved replies are rechecked for visibility, session validity, thread existence, capacity and the same context revision before persistence/cache publication. Changing privacy off and back on is still a revision change. A late result is discarded with `PROVIDER_CONTEXT_CHANGED` or `PRIVATE_CONTEXT_HIDDEN`; this is not cancellation of remote billing or rollback of already completed external work.

## Context and evidence

The shared projection includes at most 8,000 characters of facts and at most the last 12 eligible messages / 12,000 characters from the explicitly selected thread. It is intentionally incomplete, deterministic and data-only. Voice currently receives permitted facts, but no arbitrary saved-thread selection and no automatic audio/transcript retention. No background fact extraction or embeddings are used.

Stored text messages retain role, text, time, actual reply mode and optional proposal ID/kind. Proposal status is joined from current server state, not inferred from assistant language. A recovered reply does not reconstitute an old action as newly executed. `ai` and `local_rules` remain distinct. A model reply, an accepted draft and verified real-world completion remain different evidence levels.

## API and implementation

Owner-only routes under `/api/assistant`:

- `GET/POST /context-settings`
- `GET/POST /memories`; `POST /memories/{id}/actions`
- `GET/POST /conversations`; `GET /conversations/{id}`; `POST /conversations/{id}/actions`

Existing `/messages` accepts optional `conversation_id` and reports `history_saved`, the conversation ID and persisted message IDs when applicable. Existing proposal routes filter personal drafts by owner visibility and require an owner-visible decision for memory changes. The workspace snapshot exposes only `personal_context_visible`, never the private records themselves.

Implementation: `backend/desk/context.py`, `memory.py`, `conversations.py`, integration in `assistant.py`, `assistant_routes.py`, `text_ai.py` and `runtime.py`. Background routines have a separate deterministic implementation and do not gain model permissions from memory.

## Automated acceptance coverage

`tests/test_personal_context.py` covers defaults; temporary plaintext exclusion from durable receipts; saved-thread restart/recovery/deletion; saving disabled without deleting history; stale versions; forgetting without receipt resurrection; explicit owner approval and concurrent confirmations; cancel/expiry scrubbing; exact destination/role/session/privacy gates; context bounds and old-history exclusion; mocked provider payload inspection; no voice-history writes; late privacy changes and off/on fences; owner-only HTTP routes; capacity and one-in-flight ordering; and revocation while a mocked provider is blocked. `tests/test_tasks.py` explicitly grants business-context consent in its provider/background fixtures. All provider responses in this coverage are synthetic; they do not establish live model quality or microphone/provider connectivity.
