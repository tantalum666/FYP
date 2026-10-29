# Assistant permissions and action UX · Group 2

29 October 2026. Current contract for the shared web, phone browser and Capacitor app. The owner requested contextual approvals and a Full access option across clients. [Design brief](../../planning/2026-10-29/assistant-permission-ux.md) and [local evidence](../../output/qa/2026-10-29-assistant-permissions/verification.md) distinguish implementation, browser operation and native acceptance.

## What the owner sees

- **Ask first** is the default. A proposed change appears in the conversation with its purpose, affected item, reviewable content and **Allow once / Not now**. File actions show running/stop, unknown-result checking and independently verified results in that same card.
- **Full access** is an explicit owner preference in Settings and beside the composer. New requests from an authenticated owner can apply supported calendar/task/memory changes and use already enabled bounded file tools without another approval click. The model still has no permission-setting or confirmation tool.
- Both controls use the same server preference. It does not enable executors, connect accounts, grant media capture, start a model session or authorize physical outputs. Background/internal/paired requests cannot borrow the owner's grant. Manually prepared activity forms remain deliberate review drafts.
- Changing mode never automatically executes an earlier pending action. Revoking Full access prevents still-queued automatic work from starting; it does not undo completed work or withdraw a separate one-time approval.
- Technical IDs, file names, byte counts and hashes are available under Details. Files and results in a task continue into the shared Alice conversation; they do not open another job-management dialog. Historical activity remains available on demand.
- Phone Calendar, Tasks and More use full-screen navigation with a back action and existing draft protection. Alice remains the home. Web and native use the same permission and action components.

## Authority and lifetime

`PermissionService` owns one `owner_permissions` row, initially `ask`, version 1. Owner-only `GET/POST /api/permissions` use the existing request and operation-ID controls. Enabling Full requires the exact current version. An explicit Ask request can revoke from an older version; every accepted decision increments the version, including Ask → Ask, so a delayed Full request cannot override that revocation. Retrying the same operation returns the current effective preference, not its historical mode.

A new owner request captures the policy version, current authenticated session, selected task and proposal/job sequence boundaries. The service rechecks session validity, current policy and cancellation before applying only newly prepared eligible actions. Existing pending/replayed/status-read actions fall below those boundaries and remain manual. A selected-task grant does not approve changes to a different task.

Software proposal kinds are `create`, `change`, `task_create`, `task_change`, `memory_save`, `memory_replace`, `memory_delete` and `memory_consolidate`. Physical output remains outside this list. A goal represented by a new task proposal follows the task rule; scheduled or manually prepared goal-close drafts have no automatic request grant. Accepted effects go through existing AssistantService, TaskService, MemoryService and JobService; there is no parallel queue or execution store. Task/memory provenance records `owner_policy`, and file authorization records its policy version. Automatic completion is not mislabeled as a manual click or external delivery proof.

File approval still binds the full intent hash, version, scope and expiry. Automatically approved jobs recheck the policy at claim and the pre-dispatch checkpoint. Revocation produces `PERMISSION_CHANGED`; explicit one-time approvals remain valid under their own checks. Execution, cancellation, restart and unknown-write readback keep the existing [job contract](computer-jobs.md).

## Recovery and current facts

HTTP receipt lookup, application and persistence are serialized by TextAssistant's existing lock. A cached reply refreshes its actual proposal/job outcome without a new grant. A committed business receipt is enough to recover and finish confirmation metadata after a crash; it does not repeat the effect or leave a false pending card. Realtime dispatch applies the same policy to eligible draft results and reports committed outcomes truthfully after interruption.

Forgetting removes matching cached reply bodies. A content-free retired-request marker in the existing operation ledger preserves the original request hash. Retrying that old request returns a localized cleared-response notice, without recreating a fact, calling a model or inserting the forgotten user text into a new RAM conversation. Changed input under the old key is rejected; an intentional new request can remember the fact again. This does not erase external provider logs or existing backups.

Permission saves use a stable request key independently of a pending business write. After a lost response the UI reads the effective policy. WorkspaceProvider accepts the authoritative receipt and rejects older in-flight snapshots. A failed file response therefore cannot block changing permissions. Inline action recovery reuses its original key and preserves unrelated unsent text.

## Limits and next work

Full access is bounded software delegation in this single-owner application, not unrestricted OS access. The existing HTTP loop still stops after one effect-producing tool result; this change does not add a second model loop or claim multi-step autonomous completion. Long-running mixed-action/partial-failure orchestration is separate work. All new model-path checks are offline/scripted; native build/visual evidence does not close native tap/soft-keyboard or real-device acceptance.
