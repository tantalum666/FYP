# Group 2 · Managed public-browser research

17 November conversation update: the shared `browser_research_draft` tool can propose the explicitly configured managed engine. The owner must approve the shown scope and screenshot sharing before it reaches this executor. `browser_research_status` reopens the saved report/evidence and does not claim a resumable session. Local protocol tests cover this path; new paid FYP/voice acceptance remains pending. [Conversation contract](conversation-browser.md).

16 November2026. An optional official Agents API executor shares FYP's existing `computer_jobs`, review/Full-access permission policy, cancellation and task/version/session checks. The local Chromium executor remains the default. This is public research/comparison, not authenticated checkout or general access to the owner's desktop.

## Responsibilities

- `managed_browser_client.py`: one official hosted session, SSE terminal-event handling, exact origin approval, authentication refusal, bounded activity/time, final-answer retrieval, explicit cancellation/deletion. Uses the existing HTTPX dependency and OpenAI-only proxy; the API key stays on FYP's backend. No planner, second queue, automatic input retry or local agent SDK environment is added.
- `managed_browser.py`: reuses the public-browser owner/privacy/provider admission. The existing job worker executes it, stores a private session ID before input, and verifies saved final-report bytes against a separate evidence hash.
- `ComputerUseInput.engine`: `local` by default, `managed` only when explicitly selected and enabled. Old stored requests without this field keep their exact bytes/hashes. Executor identity and scope must match the selection. Managed sessions cannot use local fixture URLs or claim browser-state continuation.
- The existing form exposes **Cloud research** under More options only when configured. Results are plain escaped text in the job card; no broken screenshot/owner-takeover/Continue control is invented when the API provides none. Provider names remain outside this ordinary flow.

## Configuration and limits

`DESK_MANAGED_BROWSER_ENABLED=1` opts in on a backend already configured for OpenAI/GPT6.1Sol. Default is off, including this round's normal runtimes. A user-prepared job still needs explicit cloud-sharing intent and owner approval or the existing Full-access setting. Enabling the adapter is not authorization for an agent to spend test credit.

One job admits at most8exact HTTPS origins. The hosted environment is small with desktop enabled, restricted network domains, computer-use tool only and multi-agent disabled. Origin requests outside the admitted list are denied; authentication requests are cancelled and the session closes. Hosted origin approvals are not per-payment approvals, and instructions are not a programmatic transaction firewall. Do not attach private accounts, credentials, payment data, or claim merchant transaction support through this adapter.

Active work is limited to45seconds including creation; cleanup gets a separate12-second budget. Observed browser activities are bounded by `max_steps`; this is not a provider-internal model-call ceiling. One session reserves one existing daily provider-attempt slot, but can contain multiple internal calls. There is no claim of an account-wide dollar cap. Missing provider usage stays unknown, not free.

Closing SSE is insufficient: interruption sends cancellation, then DELETE and GET404 readback. Cleanup has priority over another billing read. API deletion confirmation does not establish the physical cloud resource's exact teardown time. Uncertain creation/deletion persists `cleanup-required` and stops new managed admission. Never retry create/input automatically or clear the marker just because FYP restarted. Inspect the saved session ID and the provider's resource state before operator cleanup; old metadata/restore is not an executable live session.

`quality=not_goal_completion` remains mandatory. “Ready for review” means the completed provider report and deletion evidence were saved/read back; it is not independent proof that every page assertion is correct, or that an order/ticket exists. The frontend shows only the final answer, not intermediate commentary.

## Actual acceptance

The separate owner-approved live trial used one session on Books to Scrape, read two titles/prices and chose the cheaper book; an independent HTML read matched. Four browser activities,51.731seconds, DELETE then GET404. Usage was null; the USD1 round is closed with the entire amount reserved. No further paid call was made. Live cancellation did not fit the one-session time cap and was not claimed.

The FYP adapter was subsequently tested locally with the captured API shapes: approval, refusal, cancellation, idle-without-terminal-event, missing usage, uncertain creation/deletion, no replay, evidence tampering, legacy intent/backup compatibility and actual desktop/phone UI flow. **This integrated FYP path has not had another paid end-to-end trial.** Conversation/voice tool admission is now wired as described above, while live spoken admission, authenticated takeover/return and merchant payment/ticketing remain unaccepted. [Original QA](../../output/qa/2026-11-16-agent-runtime/verification.md), [official-source review](../../research/2026-11-16-official-agent-runtime.md).
