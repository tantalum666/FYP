# Group 2 · Mail follow-up and official capability audit

17 November 2026. Source branch codex/mail-thread-followup-20261117, based on a88e1a1c / PR127. Owner paused Pi power work, resumed personal-agent development and asked to avoid rebuilding official OpenAI capabilities.

## Result

Selected Gmail/Outlook thread metadata can be explicitly followed for seven days, associated with one task and acknowledged/stopped in the shared owner UI. New incoming IDs append evidence and coalesce notices. Proper replies use the original source/thread with the existing reviewed sender and durable no-resend behavior. [Behavior contract](../../../desk-companion/docs/mail-thread-followup.md).

The [official reuse audit](../../../research/2026-11-17-official-capability-audit.md) verifies Live/Responses, managed Agents, Automations and current MCP prerequisites. It corrects stale “managed off” text, restricts the new mail worker to deterministic source synchronization, and records the older primary text AgentLoop as the next migration gap. No official Automation resource or replacement generic planner was created.

## Local verification

| Check | Result |
|---|---|
| Full backend pytest | 2,471 passed, 2 skipped, 537.56 seconds |
| Skips | Two Linux systemd dependency-graph checks; systemd-analyze is absent on this Mac. No Pi/hardware test resumed |
| Final focused regressions | 44 passed, including stronger Full-access consent capture, pause-before-read and pause-during-read; backend production code unchanged after the full run |
| Frontend node tests | 393 passed |
| TypeScript and Vite build | Passed; existing large-chunk advisory remains |
| Ruff on affected Python files | Passed |
| git diff --check | Passed |
| Actual browser | Installed Chrome via Python Playwright; desktop 1440×1000 and Chinese phone 393×852 |
| Page identity / nonblank / overlay | Desk Companion, meaningful UI, no framework overlay |
| Runtime/console | No page exceptions. Expected net::ERR_FAILED from deliberately dropped POST replies; software WebGL screenshot ReadPixels performance warnings recorded |
| Rendered flow | Review → same task update → acknowledge → task discussion → source-bound reply → lost acknowledgement → same operation recovery; Chinese review/cancel and stop recovery |
| Delivery boundary | Local source/fixture acceptance only; normal runtime, native binary and Pi not promoted |

No Browser plugin/skill was listed, so the frontend-testing-debugging fallback used the installed Playwright/Chrome without installing dependencies. Private scripts, screenshots, fixture databases and raw logs remain in ~/.config/desk-companion/mail-thread-followup-20261117/. Sanitized counts and hashes are in [validation-summary.json](validation-summary.json).

## Behavior checked

- Explicit unchecked background consent is required even in Full access. A preview has no task/subscription effect.
- A message arriving between preview and confirmation is counted against the original baseline.
- Incoming changes remain with one task. Repeated IDs, changed labels and outgoing messages do not create duplicate updates. Multiple unread arrivals share one outstanding notice.
- Quiet hours retain the same pending notice across service reconstruction. A stop during publication suppresses delivery.
- In-flight stop/hide/account replacement/disconnect/task closure and old-worker completion cannot publish stale results. Task pause and expiry prevent reads; browser-session expiry alone does not revoke the explicit bounded background grant.
- Stale acknowledgement cannot clear a newer observation. Source failures preserve prior evidence.
- Graph uses fixed OData scope/immutable IDs; nextLink, duplicate/mismatched IDs and oversized threads fail closed without following a returned URL.
- Bulk long message IDs stay within the existing 2,000-character task-evidence backup limit. Portable task restoration creates no live mail grant.
- No background AgentLoop/text generation occurs. Live's official Responses setup exposes the same owner mail functions and no confirm tool; paired scope excludes them.
- Reply-To/original recipient, decoded exact subject and source ID are rechecked before dispatch. Header/target changes, ambiguous recipients and oversized identity fields cannot silently alter a reply.
- Gmail MIME/thread payload and Graph reply/202 response were tested through synthetic transports. Unknown sends block repeated confirmations and another draft to the same target. Acceptance is not delivery proof.
- Desktop final browser journey produced exactly one synthetic provider send despite a dropped HTTP acknowledgement and same-key recovery. The reply carries In-Reply-To/References for m2 and the original thread ID.
- Chinese phone stop lost its first HTTP reply; recovery reused the same key. A later injected message caused zero provider reads and no new notice; the task/history remained.
- Both sizes showed escaped untrusted subject text, no horizontal document overflow and readable controls.

## Repairs found during verification

1. Large message-ID batches could exceed the existing portable evidence length. Keep a bounded pair of IDs plus total/omitted count in task evidence.
2. Mail panel and file panel initially shared a React key, duplicating the mail section on refresh. Give the mail panel a distinct task-scoped key; repeated actual navigation now shows one panel.
3. The existing pending-list disappearance heuristic could claim “expired without changes” after a successful send, particularly with client/server clock skew. Remove that inference; render recovered decisions from their server receipt for all proposal kinds.
4. A child-panel recovery could leave the surrounding web/phone pending banner stale. Subscribe the existing banner to the existing recovery/session event; final screenshot shows the accepted receipt and no stale banner.
5. Early private test harnesses assumed a nonexistent Outlook auth attribute and an incorrect unauthenticated status, and used the home input placeholder inside a task discussion. They were corrected against actual adapters/UI; these were test-harness failures, not live service results.

## Limits and publication

No new paid call, real mailbox monitor, real send, order, ticket, CI, firmware change or hardware connection occurred. A3, existing user data/grants and the installed release were not modified. Closed paid budgets remain closed. Microsoft FYP registration/consent and broader official Gmail MCP/Work IQ prerequisites remain unaccepted. Native touch/keyboard, actual incoming-mail timing and real model choice of the new tools need separate acceptance.

Source is prepared as a separate PR stacked on127; pushing, merging, deploying and live activation are distinct states. The next orchestration step is to move the OpenAI primary text path onto official Sessions/function execution, retaining these business handlers and existing approval/receipt rules.
