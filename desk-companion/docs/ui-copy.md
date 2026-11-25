# Group 2 · Interface copy and disclosure

## 25 November · A followed reply

On the task and in Chat, one card names the task and says a reply arrived. Say whether the source is the local mail sample or a connected mailbox. Offer Read the message, Check again, and Draft a reply. Show the draft editor only after Draft a reply. Say that saving the draft does not send it. After saving, say that nothing was sent. A failed check says it failed and is not a new confirmed reply.
## 25 November · Finding remind-later

On a Conversation finding, keep Sources and Got it. Add Remind me later for a one-hour deferral of that same cited finding. Do not imply mail was sent or a task was created. After the snooze ends, Alice may raise the finding again under the existing quiet-hours and delivery caps.
## 25 November · Home cue opens Conversation for Sources

When the Alice home cue is a proactive finding, offer View in conversation beside Got it. That control only expands Conversation so Sources stay available; it does not dismiss, send mail, or create a task. Got it on the cue still dismisses. Match the Inbox label View in conversation / 在对话中查看.
## 25 November · Inbox Dismiss for proactive findings

When an Inbox entry is an initiative notice, Dismiss clears that notice and the pending finding(s) bound to it, matching Conversation Got it. View in conversation still opens Alice without dismissing. Do not imply mail was sent.
## 25 November · Open a cited task from finding Sources

On a Conversation finding, Sources may include a task citation. Offer Open task with the existing title so the owner can open that task in Tasks. Do not dismiss the finding, create a follow-up, or imply mail was sent.
## 25 November · Open a cited memory from finding Sources

On a Conversation finding, Sources may include a memory citation. Offer Open memory with the existing fact text so the owner can open that fact in Memory. Do not dismiss the finding, create a follow-up, or imply mail was sent.
## 25 November · Open a cited calendar event from finding Sources

On a Conversation finding, Sources may include a local calendar citation. Offer Open calendar with the existing title so the owner can open that occurrence’s Event details. Do not dismiss the finding, create a follow-up, or imply mail was sent. Google preview citations stay labels until a separate import story maps them.

## 25 November · Workspace navigation and notices

On wide screens, give the current item a detail pane alongside the list. On narrow screens, show one level at a time and return to the same list, search or settings category. The sidebar or mobile navigation holds the Inbox count. Put a repeated check-in’s explanation, date and dismissal in its Inbox entry. Opening the Inbox preserves all receipts. Where an update cites another part of Alice, offer the relevant action inside the entry.

Use the page header for the primary action. Today shows upcoming events and tasks with a next step. Task details lead with the deadline and next action, followed by progress and editing. Settings presents one category at a time. In Connections, make app search and current access visible before the app’s account actions. Keep user-entered drafts on screen when navigating away would discard them. [Rendered examples and verified routes](../../output/qa/2026-11-25-workspace-redesign/verification.md).

## 23 November · Listening inside the conversation

While the microphone is active, the expanded Home conversation reserves one row for its current voice state and controls. The transcript uses the remaining height and keeps the reader’s position when a later caption arrives. Turning off the microphone returns focus to the text composer. The permission and wake controls stay available. On narrow screens they sit below the voice row.

A confirmed browser research task shows the status of its original job card. The same card presents its verified result or next action. An earlier “Research started” acknowledgement must disappear when the result is available. [Rendered desktop and phone checks](../../output/qa/2026-11-23-voice-layout/verification.md).

## 21 November · One order result per turn

Keep the ordinary home on Alice. A fresh quote offers a single way to open the review; a finished order fits on one line. In the conversation, render an order response once. Keep the active decision visible, place other orders behind one disclosure, and let the result itself expand to show the original payment, net amount and provenance. Eligibility questions and errors keep their own answer. Choosing a flight uses a short action label and opens a freshly checked price. A passive update must preserve an existing decision, focus and unsent text. [Before and after](../../output/qa/2026-11-21-quiet-order-followup/verification.md).

A proactive finding keeps Sources and Got it. Follow up on this is the explicit owner choice that opens a private task; status lines say Nothing was sent. Do not imply mail or purchase from that control. [Initiative follow-up](../../output/qa/2026-11-25-initiative-followup/verification.md).

## 17 November browser work in conversation

Use a compact task/site card with unchecked cloud screenshot consent; exact task details stay available in a disclosure. Use progress in the same conversation and current result evidence, without claiming an order or ticket. Generic pending-request copy says “action”, not “save”, because approval may have started a browser job. A recovery button appears after interrupted submission, not while that submission is still busy. The shared desktop/phone/device labels retain the same meaning. [Contract](conversation-browser.md).

## 9 November composer and file flows

The owner explicitly removed model/vendor branding and API-turn counts from ordinary composer/browser/file controls. Use Alice and concise cloud-processing descriptions while keeping the selected data, explicit consent, action approval and recovery clear. + adds local chat files; operation history is under More. A shared dark-control surface pairs foreground/background for buttons, fields, downloads and errors. See [chat attachments](chat-attachments.md).

2 November 2026: [desktop conversation](desktop-conversation.md) is the primary Web page, superseding the old modal/docked layout. Test zoom and window height in a separate QA tab.

1 November 2026. Owner feedback: pages contain too much explanatory text. This is an ongoing product requirement across web, phone and shared app components, not permission to remove Alice or the controls needed for informed actions.

## Default view

Show the user's content, the current state, useful results and the next available action. A heading does not need a paragraph that repeats it. Prefer “New work”, “Download” and “Results ready” to descriptions of persistence, verification infrastructure or output quality. Do not imply the whole goal is finished merely because a file exists.

Put operation IDs, hashes, call counts, versions, detailed activity, storage management and implementation explanations behind named disclosures. Optional configuration belongs in “More options”; empty optional sections need not appear. Avoid repeating the same caveat on every card. Keep errors, a necessary question, a blocked reason and its recovery action visible when relevant.

On a phone, selecting Work opens its detail in place of the list; “All work” returns through the existing guarded navigation. Desktop can retain a two-column list/detail. Alice and the phone's Plan/More navigation remain intact.

## Action-time information

Keep the affected item/destination and action clear before approval. Exact content remains reviewable. Explicit provider sharing and local retention are unchecked until selected; disclose that saved Work cannot currently be deleted. AI charges and retry consequences stay concise and visible when starting/retrying model work. Full access retains an explicit save action and its supported scope.

Import/share/backup details appear with the relevant controls. Sharing's recipients and expiry must be visible before creating a link. Privacy and permission policy, source identities, version checks, cancellation, unknown-result recovery and backend validation are unchanged by shorter labels.

## Implementation and checks

Reuse the current components, services, draft guards and request lifecycle. Native `details` keeps fields mounted while collapsed, so input survives disclosure changes. Do not add parallel state machines, extra polling, generic CSS that hides important content, or replace user-authored values to make a screenshot cleaner.

Review actual English desktop and Chinese phone rendering, keyboard disclosure, draft retention/closing, actionable errors, and the approval path. A lower text count is supporting evidence, not proof that the whole product is easy to use. The current [UI QA](../../output/qa/2026-10-31-ui-copy-cleanup/verification.md) records exactly which surfaces and flows were inspected. Native touch and software-keyboard acceptance remain separate.
