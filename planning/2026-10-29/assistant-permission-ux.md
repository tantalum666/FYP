# Group 2 · Unified assistant actions and permissions

1 November 2026 continuation: [concise interface copy](../../desk-companion/docs/ui-copy.md) supersedes verbose default explanations. Optional details remain accessible and all approval/draft/recovery behavior is retained. The dated results below are historical; current UI evidence is in the [cleanup QA](../../output/qa/2026-10-31-ui-copy-cleanup/verification.md).

29 October 2026. **Implemented and locally verified; native input acceptance remains open.** Owner direction: correct the approval/navigation experience across web and app clients, learn from Codex/Muse/Dot-style interaction, and offer full access in settings. Existing Alice, API/services, safe file executors and verified task continuity remain the base.

## Implemented user-visible behavior

1. The conversation is the place to ask, inspect an action, allow/decline, see running state, cancel, and receive a verified result. File approvals must not require a trip through an administrative job form. Existing calendar/task/memory confirmations become consistent with that presentation.
2. Keep a current-permission control by the composer and the same preference in Settings. Two modes: **Ask first** and **Full access**. Full access means delegated execution of supported software actions through already connected tools; the scope is visibly listed. It does not create an arbitrary shell, new app account, microphone/camera grant, physical-motion capability, or a provider budget.
3. Default to Ask first until the owner explicitly saves another mode. The model, paired displays and background work cannot edit this preference or acquire the owner's automatic grant. Do not enable full access on the user's existing runtime merely to demonstrate it.
4. Full access must actually apply eligible actions, report real saved/queued/failed outcomes, and keep receipts. Old pending cards do not silently execute when the preference changes. Reuse existing version/expiry/idempotency and verification gates. The model still proposes; the owner's persisted policy is a separate authority.
5. Calendar, Tasks and Activity remain useful organizational views. Phone management becomes deliberate full-screen navigation with a real back action, preserving drafts and Alice's home. Web route changes start at the top. Avoid a full page inside another generic modal.
6. Lead with action purpose, affected item/destination and outcome. Exact content is reviewable; operation IDs, hashes, byte counts and executor details belong in secondary details. Keep English/Chinese labels and keyboard/draft guards.

## Implementation boundaries

- One versioned server permission service, with owner-only GET/write routes and no model tool for changing it. Use normal request/operation/version checks and record policy changes/use.
- Capture an authenticated owner grant for a new user request; recheck the current permission/version before applying an effect. Requests from paired displays, internal callers without an owner principal and background agents retain manual review.
- Apply software proposal kinds and bounded file jobs through existing AssistantService/JobService, not a parallel action store. Physical-output proposals stay explicitly reviewed. Automatic receipts must not falsely say the user clicked a one-time confirmation; preserve their authorization source.
- A lost response or cached old reply must resolve existing action status without redispatching writes or retroactively granting an old pending action. Queued automatically authorized jobs must respect permission revocation before dispatch; already-written files retain truthful results.
- Share job action rendering/controller behavior across conversation and secondary activity views. Reuse existing status reads; do not add a poll per card. Preserve selected-task ownership/version and normal principal-change clearing.

## Acceptance checks

- Ask first: request creates a card without effect; allow once applies exactly once; decline and expiry do not write.
- Full access: owner can deliberately enable it; new eligible software actions apply without another approval card; real file result remains independently verified. Unsupported/unavailable tools stay unavailable.
- Permissions: stale policy versions, paired/background callers, revocation, simultaneous requests, cached responses, service restart and cancelled/expired actions cannot gain unintended authority.
- All clients use the same setting and action status. Switching mode does not start media, a model connection or old pending work. Unsent input and selected task survive the intended navigation paths.
- Web and phone actual UI checks cover mode selection, inline review/result, task/activity navigation, narrow layouts and errors. Native build/visual checks and actual touch/keyboard acceptance are recorded separately.
- Local tests/build/lint and staged secret/source checks only. No CI. Update product, decision, maintenance, handoff and work log before publishing the final coherent change.

## Reference basis and audit

[OpenAI Permissions](https://learn.chatgpt.com/docs/permission-modes) separates an access boundary from approval handling and places the current mode near the composer. [Muse design](https://introducing.muse.ai/) describes ongoing conversation, visible activity, structured approval cards and adjustable defaults. [Muse's separate permission authority](https://research.meta.ai/blog/security-and-safety-for-ai-agents-our-approach-with-muse) informs the service boundary, not a claim of equivalent infrastructure. [Dot](https://learn.chatgpt.com/docs/dots) informs continuity across clients and separate connected-tool grants. Current Grok-specific controls were not verified; no exact clone is claimed.

Current capture-based findings are in the [audit](../../output/qa/2026-10-29-assistant-permissions/audit.md). Existing project styles, source components and Alice are the visual target; no new brand or disposable mock app is needed.

## Delivery result

The shared components and independent versioned PermissionService are implemented. Default Ask first, automatic Full access on new eligible owner requests, revocation/cancellation/recovery, readable task results and full-screen phone navigation have local evidence. Manual activity drafts, scheduled goal-close drafts and physical proposals remain reviewed. HTTP still stops after one effect-producing tool; this is not unrestricted autonomous execution.

[Final QA](../../output/qa/2026-10-29-assistant-permissions/verification.md) records489 backend/89 frontend checks, actual web/phone journeys, file readbacks and current native build/visual delivery. Native mirror taps still did not cause a reliable navigation transition; keyboard/real-device acceptance stays open. Current preview is Ask first. [Permission contract](../../desk-companion/docs/assistant-permissions.md) is the implementation authority.
