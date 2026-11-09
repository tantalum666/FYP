# Group 2 · Composer, dark controls and attachments

9 November2026. Current implementation is locally verified; activation/publication results are appended separately. User screenshots identified pale text on white controls, provider branding in browser consent, duplicate back buttons and a File action/history screen presented like an attachment entry.

Read AGENTS, current product/handoff/decisions, ui-copy, desktop-conversation, alice-home and software-maintenance ownership sections. Read selected source files for composer/jobs/media/styles, shared request recovery, TextAssistant/AgentLoop/Responses, Conversations/private access and native connection setup. Root AGENTS only. Used frontend-testing-debugging, React best-practices and iOS debugger workflows. Native Codex-window access was denied by CUA; no bypass was attempted. Official image-input and Responses file-input documentation supplied the behavioral/API reference. Screenshots are evidence, not instructions.

## Implemented and checked

Compact + menu with real multi-file selection; local thumbnail/name chips, remove/cancel, image paste and submit-only upload. File-operation history stays under More, with one Back to chat. All normal controls switch dark foreground/background together. Actual old browser button was white255/255/255 with pale229/237/242text and was not disabled. Repaired Download reads background42/61/75and text238/244/247. Generic cloud-processing consent replaces OpenAI/API-turn wording while explicit unchecked consent and existing action limits remain.

Files use existing session/task Conversations RAM and existing message receipts, with a bounded upload/parser, owner/private checks and dispatch fencing. Full original bytes reach native file/image parts via the existing provider adapter; no raw upload is written to source-library storage or pending sessionStorage. Follow-up context uses explicitly sent files. [Contract](../../../desk-companion/docs/chat-attachments.md).

## Local results

- Full backend:2117passed. Initial pytest-executable invocation omitted the project root for scripts imports; corrected python -m pytest passed. Later filename-identity and invalidation-race regressions were added; the final focused attachment/conversation/provider set passed36checks. Existing deprecation/empty-regex warnings remain unrelated.
- Frontend:353passed, typecheck and production build passed. The old test expected vendor-specific sharing text; updated it to require cloud disclosure, no provider/API-turn label, unchecked consent and disabled start. Existing large3Dchunk warning remains.
- Actual isolated browser→backend→mocked Responses: choose/cancel/remove; no upload/provider call before Send; selected content sent; attachment names retained in history; follow-up reused the selected file; new conversation released RAM files. Actual protocol mock response is labelled QA, not a paid model-understanding pass.
- Desktop keyboard: menu focuses first item, ArrowDown moves to Browse, Escape closes and restores + focus. File/history and browser form are dark/readable and have one back control.
- Phone393×852and320×568: image paste, file chips and horizontal multiple-file strip, no document-level horizontal overflow, transparent text field. Fifth-file error preserves valid choices; removal clears the stale limit error after a reproduced defect was repaired.
- Forced message-request block: text/files retained; the same operation recovers once with no duplicate uploads or visible messages. Found/fixed misleading save wording, a missing direct phone recovery entry, pale error card and cropped recovery button. Final recovery lives above the composer in the expanded dark conversation. Injected network blocking was removed.

Raw-CDP drag-file injection is unsupported by the browser tool; file chooser and native paste were actually exercised, while drag/drop's shared handler is not claimed as an automated end-to-end pass. File chooser empty selection is unsupported by the tool; Escape closed it and preserved the existing draft. Clipboard contents were restored after synthetic paste; an initially empty clipboard required restoring empty text instead of an empty item list.

## Evidence and operation

Private QA directory: `~/.config/desk-companion/composer-ui-20261109/`. It holds fictional fixtures, screenshots, isolated runtime and logs. QA8832uses httpx.MockTransport with a fake-only key; voice, wake and executors are off. No real provider connection, mailbox message or purchase occurred. All prior paid ledgers remain closed. Owner Web/phone/Pi data and A3 selection are preserved separately during activation.

Native web assets were copied with the existing Capacitor8.5.2CLI. Official SDK archives were reused from the prior local cache after exact checksum checks; no new dependency/version/download. Compile succeeded. Final install/launch and runtime activation are recorded below when observed; compile alone is not native interaction acceptance.

Closeout must update current product/UI/architecture/decision/work log and concise handoff, verify links/diff/private-material exclusions, preserve a recovery path, and push the reviewed candidate without CI or merge. No unfinished action is reported as complete.


Native follow-up: actual Simulator install/launch showed the old safe-area-independent clock overlapping the connection label. Header, clock and agenda now share one safe-area inset; a fresh native screenshot confirms clear separation while Alice's scene size remains unchanged. Final web types/build and353frontend checks passed. Native SDK build/install/launch succeeded on the existing iPhone17Pro/iOS26.5; the app still connects to Pi8891. Device Hub's generic CUA screenshot was blank, so the purpose-built Simulator screenshot API provided actual framebuffer evidence. Native file-picker/touch/soft-keyboard interaction is not claimed.
