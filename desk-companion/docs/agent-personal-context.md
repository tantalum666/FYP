# Personal continuity in retained agent work

31 October 2026 integration: read [current compatibility and migration rules](pr5-integration.md) first. Dated October 12–13 acceptance statements below remain historical; this integration preserves Alice/current Omni and the current task/job/permission core.
Updated 13 October 2026. This is the implemented bridge contract for explicitly selected personal context. Its focused tests use actual local SQLite and artifact files with scripted model responses and a fake browser protocol. They do not establish live-model usefulness, provider access or real browser execution.

## Explicit selection and consent

`RunCreate.personal_context` is optional and defaults to no selection. In model mode an owner may choose up to eight exact memory IDs and one saved conversation. Enabling general memory or history use does not select anything for a run. Starting work from chat does not automatically attach the current or any earlier conversation.

The run must already name an approved exact text-provider destination. Selected memory requires `use_memory_in_ai`; selected history requires `use_text_history_in_ai`. The owner must also submit the actual boolean `retain_derived_context: true`. This separate acknowledgement is necessary because persistent model decisions, plans, questions, reports and proposed changes may repeat a selected fact even though the input projection itself is not stored in the run.

The owner-visible selection catalog contains permitted memory IDs, versions, categories and at most 160 characters of summary; saved-conversation IDs, titles, versions and eligible-message counts; and selection limits. It is unavailable to forged, paired or expired identities and when private context is hidden. Disabled/unapproved categories have no choices. This catalog is UI data, not a provider payload.

## Metadata binding and ephemeral projection

`backend/desk/agent_context.py` supplies strict `RunPersonalContextSelection` and `RunPersonalContextBinding` types and `AgentContextBridge`:

- `catalog(session_hash=...)` reads owner-visible permitted choices without changing storage
- `bind(selection, run_id=..., session_hash=..., provider_destination_id=...)` creates a metadata-only binding
- `project(binding, ...)` freshly reads only bound, still-permitted records for an immediate provider call
- `validate(binding, ..., conn=...)` checks the same fence before accepting or replaying a result; an existing write transaction can make the check atomic with its local result commit

A binding pins the run ID, original authenticated session hash, exact provider destination, privacy revision, selected memory versions/content hashes, and the exact selected eligible saved-message IDs/content hashes. It contains no copy of memory or message text, no raw session cookie and no provider credential. The session hash is an existing authority reference, not a new bearer token, and is omitted from public run views.

The conversation's version at selection is informational. Only the newest eligible messages existing at selection are bound: at most 12 messages and 12,000 characters. Later appends and renames neither expand the input nor invalidate an otherwise unchanged binding. No automatic follow-the-conversation behavior exists. Up to 8,000 characters of selected memories can be projected; the complete serialized projection must also fit 30,000 UTF-8 bytes. The planner applies its separate combined-context ceiling, so a valid personal projection plus other evidence may still exceed a run's limit. Oversize contexts fail rather than silently expanding a budget.

The bridge creates no tables, receipts, embeddings or projection cache. Only content-free references/hashes are stored in the run. Its returned provider data is explicitly marked untrusted personal context, with no authority and no evidence status. Remembered instructions or past approvals cannot grant a tool, confirm a draft, create a source citation or prove completion.

## Invalidation, restart and retained outputs

Forget/correction, context-setting changes, revocation, hide/show, endpoint changes, missing/changed selected messages, and changed selected-memory versions fence further use. Off and back on still changes the privacy revision. Forget/correction preserves the existing conservative rule that all older saved messages become ineligible for future provider projection; this bridge does not alter that rule.

The binding is never refreshed during resume, steering or cached-decision recovery. Invalidated personal-context work requires a newly selected run. A different authenticated owner session also requires a new personal-context run; the single-owner prototype does not transfer the original binding to a newly signed-in session. Unchanged metadata can be restored after process restart and re-resolved, without retaining a private projection cache.

Previously and explicitly retained transcripts, model outputs, proposed business records and immutable artifacts remain separate retained material. Forgetting a fact does not remove its older mention from an inspectable transcript or already-created artifact. Those older outputs must not be fed back into the invalidated run through resume or decision replay. Existing application limits on runs/artifacts remain; there is no new retention expiry or total-disk bound. Hashes are repeat/integrity metadata, not anonymization. SQLite/WAL/backups, operating-system copies and provider-side bytes are not forensically erased or recalled.

The bridge cannot inspect the semantic contents of a fact for every possible secret. It never reads session cookies or configured provider credentials into the projection, but owners should not save credential material as ordinary facts or conversation text.

## Other destinations and evidence

Local derived-output retention does not authorize sending personal text to a browser app or connector. The integrated public browser brief accepts only a selected public catalog source and its same-run observation ID. Its title and note are code-owned, and it copies only the observed public excerpt. No model-supplied goal, memory, conversation, report, title or note is accepted by that public-only operation. Any future free-text external tool needs its own data-transmission scope.

Personal context is not inserted in `evidence`, `report_evidence`, event bodies or tool results as a source observation. A generated report may use a preference for presentation, but its source citations must still resolve to actually acquired source evidence. Independent structural outcome checks remain distinct from model semantic quality.

## Focused acceptance and boundaries

`tests/test_agent_context.py` exercises real SQLite selected-only projection, read-only behavior, metadata restoration, owner/session/destination gates, message watermarks, capacity/UTF-8 bounds, invalidation, strict retention acknowledgement and a blocked late response while forgetting remains usable.

`tests/test_agent_personal_context_integration.py` exercises actual run creation, scripted planning, pause/resume/restart, immutable output files, unchanged-thread continuity, no default inclusion, stale resume/steer and cached-decision rejection, late result exclusion, remembered instructions without authority, separate retained artifacts, and the private-marker absence from public browser prepare/dispatch payloads.

The bridge owns no model/network work and holds no privacy lock during provider I/O. The caller still owns every dispatch and publication fence. Focused coverage is not a claim that every unrelated service or all race interleavings were tested; integrated artifact publication and derived-draft confirmation boundaries need their own coordinator review. See the [focused QA record](https://github.com/tantalum666/FYP/blob/11dc2b84cebe6e8250b28ca4442fc91f0dfec676/output/qa/2026-10-13-agent-context-bridge/verification.md) and the broader [run contract](agent-runs.md).
