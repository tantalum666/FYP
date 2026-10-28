# Group 2 · Software maintenance contract

28 October2026. The current checkpoint follows merged Grok/PR60 integration and fixes older-memory continuity and shared memory browsing. Selected-task context and interaction recovery remain in place. The owner requests focused documentation reading, maintainable implementation and GitHub publication of meaningful milestones.

## Frontend responsibilities

| Module | Responsibility |
|---|---|
| [MemoryPanel](../frontend/src/workspace/MemoryPanel.tsx) / [MemoryFactList](../frontend/src/workspace/MemoryFactList.tsx) | Panel owns requests, versions and draft protection; list owns fact rendering and transient local search. Searching does not write or fetch. During correction, the search and competing fact actions are disabled so the same draft stays visible |
| [PhoneApp](../frontend/src/phone/PhoneApp.tsx) | Compose the phone surface, selected panel/task, native route intents and user notices; it does not implement each management page or duplicate the calendar polling machinery |
| [PhoneHome](../frontend/src/phone/PhoneHome.tsx) | Alice scene, renderer fallback, Plan/More entry points and upcoming-event presentation |
| [PhonePlan](../frontend/src/phone/PhonePlan.tsx) | Day/month calendar and tasks; refuse a section change while its form/progress draft is dirty or busy |
| [PhoneManagement](../frontend/src/phone/PhoneManagement.tsx) | More navigation and existing memory/style/settings/activity/connections panels, inside their draft-guard scope |
| [usePhoneCalendar](../frontend/src/phone/usePhoneCalendar.ts) / [calendar-reader](../frontend/src/phone/calendar-reader.ts) | One scoped refresh lifecycle for home and selected dates; reuse the home query when it already covers the selected day, read independent ranges concurrently, coalesce bursts and discard superseded/closed-scope results |
| [usePhoneEnvironment](../frontend/src/phone/usePhoneEnvironment.ts) | Viewport, foreground, modal and reduced-motion state; listeners and timer have one cleanup owner |
| [useCalendarEditor](../frontend/src/components/useCalendarEditor.ts) | Shared web/phone new/edit state and defaults. A late event read cannot reopen an editor after its detail was closed. `newEvent()` is a no-argument UI callback; explicit-date intents use `newEventOnDate(date)` |
| [LoginView](../frontend/src/components/LoginView.tsx) | Shared sign-in/pairing UI; phone does not import the desktop App to obtain it |
| [useWorkspaceSession](../frontend/src/useWorkspaceSession.ts) / [session](../frontend/src/session.ts) | Shared initial and expired-session handling. Only server-enabled local preview bootstraps an owner cookie; recovery keeps mounted unsent work and never retries a write automatically |

Calendar results are tied to both range and session. Leaving a range/screen discards future commits from its old reader; it does not claim to cancel an already-sent native HTTP request. Failed reads remain retryable. Polling/assistant activity reads stop while the relevant phone surface is suspended or hidden.

A phone panel owns its form guard. A draft in the underlying assistant does not prevent opening/closing a read-only plan; it does prevent changing the selected discussion. A progress note inside Tasks blocks Calendar/Tasks switching. Close offers Continue or explicit Discard. Notices for a blocked action render inside the modal footer, not behind the top layer.

## Selected task and AI context

The selected task ID is sent in the initial WebSocket handshake. The server validates its type/length, requires an owner principal, and reads the real task through the existing TaskService, including its private-display policy. It supplies only id, version, title, status, next step, deadline and timezone as explicitly untrusted context. A client-supplied title/version does not define the task.

Omni replay is bound to both owner login and selected task. Reusing a conversation ID for another task, or switching from a task into general chat, returns`CONVERSATION_SCOPE_CHANGED` before opening a provider connection. A missing/invalid/hidden task or insufficient principal also fails before a provider connection and releases the active slot.

The snapshot refreshes at connection start, before each text submission and on explicit context refresh. It is a discussion reference, not proof of completion or authority to mutate. The model must read current task details/version before preparing changes; existing proposal review, confirmation and operation IDs remain authoritative. Voice does not gain an untested live task-subscription guarantee.

Changing the selected discussion closes the old media connection, drops its resume handle, and preserves visible messages/unsent input. The next explicit input starts the new context. There is no automatic paid reconnection. The old bounded RAM entry expires under the existing policy; this does not promise deletion from a provider.

Qwen Omni remains the tested integration baseline, not the only/final model choice. The new behavior was tested with scripted providers and actual local services, not new hosted-model quality/latency experiments. Existing alternative adapters and future comparison work remain separate.

## Validation and publication

The [current QA](../../output/qa/2026-10-28-native-memory/verification.md) records459 backend/89 frontend checks, Ruff/types/build, desktop/phone browser interactions and a fresh native build/install/launch. Native touch/soft-keyboard acceptance remains open: the current input automation did not deliver a reliable app transition. The earlier450/89 integration and303/65 #60 results are historical. Historical real-model results are not counted as new passes. Product acceptance gates and the next integrated journey are in [delivery readiness](delivery-readiness.md).

The branch retains main's Vite8.3.5 dependency. Validation runs locally: backend lint/tests, frontend tests/build and scoped interaction checks, with models and executors disabled unless separately authorized. The owner does not want GitHub CI; the workflow was removed. Do not recreate it or treat Actions/account limits as unfinished work. Relevant local checks remain mandatory before publication.

Before another substantial change, read the focused contract and relevant implementation, preserve the user's data/dirty work, use the existing service boundaries and validate the affected behavior. Add abstractions only where they clarify a real responsibility or remove duplication; line count alone is not quality. Update this contract when ownership or lifecycle changes.

## Active memory projection

MemoryService owns `active_facts()`, a model-safe current snapshot of all active facts under the existing200-fact cap; deleted, superseded and read-time-expired rows are absent. `for_model()` keeps the recent40 prompt window. Query tools rank the whole active set but return at most8; draft version checks and exact local forgetting also use the whole set. Owner checks remain at the calling boundary and confirmations recheck versions.

Conversation revision hashes that whole snapshot, while the initial prompt stays at40. Older facts can enter replay through search, so removal/expiry outside the prompt window must also invalidate RAM replay and recall focus. This reuses the existing Conversations lifecycle, without a second cache/store or automatic provider call.

## Integrated review invariants

- WorkspaceProvider owns the principal-transition boundary. A changed principal kind/id remounts private views and clears stale pending data; a same-principal preview renewal preserves input. Late replies cannot restore an unmounted identity.
- SSE transport owns framing and completion acknowledgement. EOF alone retains the original operation; recovery uses the same endpoint/key and updates only the matching conversation/draft.
- The existing Conversations pool owns temporary context. HTTP/realtime views and recall focus reuse it; no duplicate global transcript table or second model loop. Durable principal-scoped receipts are separate from login/task-scoped history.
- Shared tool validation preserves omitted fields. Read tools recheck current state; effects keep durable idempotence. Forgetting redacts/tombstones matching historical copies without deleting execution keys.
- Backup apply checks owner authority before cached results. Stored job requests are fully validated, all three executor families round-trip, and imported folders pass normal path/fingerprint controls.
- Current notification/proactivity services reuse existing preferences and scheduler. Advanced memory UI is disclosed on demand instead of expanding mobile primary navigation.
