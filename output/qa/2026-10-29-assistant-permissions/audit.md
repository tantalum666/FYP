# Assistant interaction audit — before implementation

29 October 2026, Group 2. Scope: current phone/browser task → file action → permission/settings flow; native app uses shared components but was not newly exercised in this audit. Source screenshots below were captured and inspected in this run.

| Step | Current health | Finding and implementation direction |
|---|---|---|
| 1. Phone Your plan / task results | Functional but difficult to scan | [Phone](01-phone-plan-before.jpg) shows a tall generic modal, technical job identifiers/byte counts and repeated explanatory text. Treat Calendar/Tasks as intentional navigation pages, with readable result names and secondary technical details. Preserve Alice as the home and keep data/draft state intact |
| 2. Web task → separate computer-job modal | Adds unnecessary context switching | [Web review](02-web-job-panel-before.jpg) separates an action from its originating conversation, exposes creation/settings alongside its approval and duplicates task/results context. Put a shared action card in the conversation, with visible scope, exact-content preview, allow/decline, running/cancel and verified outcome. Keep a secondary activity/history view |
| 3. Workspace settings | No unified permission preference | [Settings](03-web-settings-before.jpg) has workspace/connection controls but no review-vs-full-access setting. Add one owner-controlled, server-enforced policy shared by all clients, with current mode visible near the composer. The screenshot also shows the old scroll position carrying into a new page; reset route scroll appropriately |

Strengths to retain: exact file readback, operation recovery, clear distinction between file success and user-confirmed task completion, owner/task isolation, focus/unsaved-draft guards, licensed Alice asset and shared components. These are functional evidence from the earlier journey, not reasons to retain its current presentation.

Accessibility scope: readable labels and operable controls are observable; nested dialogs and focus movement need rechecking after the navigation change. No complete VoiceOver/WCAG claim is made.

Design brief played back to the owner: consistent assistant-led web/application interactions, contextual approval cards, Ask first / Full access preferences for registered connected tools, intentional management pages and secondary technical metadata. No separate canvas/prototype or new visual brand is requested. Existing project styles/assets are the target. Product Design preflight found no saved user-context file.

References: [OpenAI permissions](https://learn.chatgpt.com/docs/permission-modes), [Muse design](https://introducing.muse.ai/), [Dot overview](https://learn.chatgpt.com/docs/dots). Source descriptions are comparative research, not direct UX testing of those products.
