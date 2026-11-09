# Group 2 · Chat attachments and composer

9 November 2026. The owner asked for a compact Codex-like + menu, readable dark controls and ordinary wording without model/vendor branding. Chat attachments are distinct from retained Work sources and file-operation history.

## User flow

+ opens a small keyboard-accessible menu: Add files or photos, Browse the web, Today’s briefing. File-operation history remains under the conversation's More menu. The file subview has one Back to chat control. Browse the web retains explicit cloud screenshot consent, action approval and stop behavior; vendor names/API-turn counts are removed from ordinary copy. Technical configuration remains an operator concern; user-authored/provider content is not rewritten to hide words.

File selection, image paste and file drop prepare local chips/thumbnails. Selecting, cancelling or removing a file never calls a model or uploads it. Send uploads the selected bytes to the connected desk's temporary conversation, then submits opaque references through the existing message/SSE path. Files and text stay available after a failed send; Check message delivery reuses the same operation. On phone it stays above the input, and an unresolved delivery opens the conversation panel so feedback does not overlap the clock/scene. Multiple phone attachments use a horizontal strip instead of stacking over Alice.

Supported: PDF, DOCX, XLSX, PPTX, UTF-8 TXT/Markdown/CSV/JSON, PNG/JPEG/WebP. At most2MiB per file and4files per conversation. Unsupported, empty, corrupt-format and oversized selections fail explicitly. Removing a file clears a stale selection error. Actual document interpretation is a separate provider capability; selection/transport success is not proof of complete analysis.

## Ownership and temporary storage

ComposerMenu owns menu focus/outside-close/Escape/arrow behavior. useChatFiles owns selected File objects, object-URL cleanup, client revision fencing and upload preparation; ComposerFiles renders previews. AssistantPanel retains message/voice/operation ownership, and ConversationWorkspace retains drafts across navigation. No raw file bytes enter sessionStorage: the existing pending-write record contains only IDs and ordinary message metadata.

ChatAttachments validates bounded JSON/base64, names, extensions and format signatures. Office ZIP metadata is bounded without extraction. Uploads require the actual owner session, visible private context and the supported connection. Existing Conversations owns the raw bytes in RAM, under the same login/task scope,30-minute inactivity expiry and16-conversation bound; a32MiB raw-file pool cap bounds total retained data. Pending uploads are not model context until their IDs are explicitly sent. Duplicate selected bytes/name in one conversation reuse the same reference. New conversation/forgetting/replay invalidation releases the corresponding RAM files. No new persistent file/transcript table, arbitrary path, URL fetch or source-library permission is introduced.

Before provider dispatch, the file guard rechecks the session, hidden-private state, active conversation, selected references and memory revision. Cached acknowledged replies retain the existing principal-scoped recovery behavior; raw files are not replayed into a new login. File content is untrusted reference data, not tool or memory-write authority. Existing business permissions/proposal/job services remain responsible for effects.

## Provider boundary

The existing TextAssistant/AgentLoop passes file metadata as context and bounded native file/image parts separately to the Responses adapter. The private bytes are not copied into the text context budget or a second agent stack. Typed chat uses this path; existing live-voice frame sharing remains a separate explicitly supported capability.

Current Responses file inputs support these common document types as native input_file parts; images use input_image. Non-PDF embedded images are not extracted, and spreadsheets cover at most the first1,000rows per sheet. The file-specific system instruction requires honest limits and forbids unverified whole-workbook totals. [Official file-input guide](https://developers.openai.com/api/docs/guides/file-inputs). The composer reference is the official attach/paste/image-context workflow, not a claim of pixel-identical inspection of Codex's protected native window. [Official image-input guide](https://learn.chatgpt.com/docs/image-inputs).

No new provider call is made by choosing a file, opening the + menu or deploying this change. Normal owner Send remains an explicit cloud action. All earlier audition budgets remain closed; validation uses local mocked protocol responses, not extra paid calls.

## Verification

[Current QA](../../output/qa/2026-11-09-composer-attachments/verification.md) distinguishes actual browser/backend transport checks, mocked provider interpretation, native build/launch and deployment. Real model content quality, full native file-picker acceptance and physical-device microphone behavior must not be inferred from mock results.
