# Group 2 · Desktop conversation and local media

## 9 November + menu and attachments

The shared composer now has a compact Add files or photos / Browse the web / Today’s briefing menu. File chips and image thumbnails stay local until Send, survive failed delivery, and can be removed. Message recovery stays above the input; history remains separate. [Attachment lifecycle](chat-attachments.md) reuses the existing conversation/permission/receipt services.

## 8 November evening follow-up

Latest captions have a bounded dark surface and the immersive provider/microphone footer is removed. Expanded Conversation still retains separate exchanges. Apps & devices opens the shared [Google/Microsoft connections](connected-apps.md), with official browser consent and existing in-conversation email review. Actual Mac Gmail authorization and one self-email/readback passed; Microsoft account authorization is deferred. [QA](../../output/qa/2026-11-08-caption-mail-voice/verification.md).

## 8 November conversation repair

Compact Alice captions show the latest reply; expanded Conversation retains separate exchanges. The user removed Voice input/Work conversion cards from this view. The former voice-review-screen description below is historical; its backend snapshot/authority contract remains, but the normal chat no longer mounts that screen. Required action approvals stay with the relevant action. Dark transcript text/menu contrast and input/history scrolling are checked on Web and phone.

More → Assistant style now includes Alice's voice and a collapsed Speaking style editor. Owner-only settings are versioned and apply at the next GPT Live session. Saving a choice does not connect to a provider. Cached sample playback appears only when an actual preview file is available. Built-in options remain; original prompt-voice registration is private operator setup, not an unrestricted client upload/clone feature. [Verification and remaining audition gap](../../output/qa/2026-11-08-dialogue-voice/verification.md).

Historical 2 November 2026 direction: a responsive Codex/ChatGPT/Grok-style primary conversation page with usable Mac camera/microphone. This supersedes the older desktop modal/docked assistant arrangement. The 7 November owner decision now unifies the visual treatment through the shared [Alice home](alice-home.md), while preserving each surface's navigation.

## Page and lifecycle

The default Web route is `?page=assistant`. The primary page now combines a large Alice, background calendar/tasks and a persistent dark composer. Plan opens the existing calendar; More opens existing management navigation on all Web widths. Keep the composer visible at normal and zoomed window sizes.

ConversationWorkspace keeps the shared AssistantPanel mounted across navigation with a separate draft-guard scope. Unsent text/messages stay in memory; leaving chat suspends media. Logout protects unsent/in-flight chat, and the existing principal boundary clears private state on identity change. This does not add persistent chat history or a second model/approval/queue service.

Alice retains its licensed appearance. The shared home has explicit responsive scene geometry; old floating-position preferences are not rewritten. Existing contextual approvals and concise-copy rules remain authoritative.

## Local devices and provider

The camera button opens a device panel. Open camera requests video only; Test microphone meters audio locally, without recording, speaker loopback or upload. The Microphone selector stores an explicit per-browser input; local testing, Alice wake and cloud capture all use that same exact device. It does not alter system-wide audio settings. Changing it stops the local test and applies to the next capture; selection is disabled during a voice call. LocalCapture owns stream lifetime, including late/cancelled/superseded permission requests. Stop, close and background release the streams.

Share this frame explicitly sends one frame during a compatible active voice call, using VoiceAudio's existing bounded encoding, rate and disconnect checks. This is not continuous camera streaming. Preview alone is not evidence of model understanding.

The main microphone starts the existing provider-backed session. With Qwen Omni configured, explicit typed/voice input uses the same model path. Opening the page/device panel makes no paid request. The earlier manual-preview-only choice was followed by the explicit OpenAI trial request; that new bounded experiment is now closed. Normal owner use still starts explicitly.

## Historical 2 November preview (superseded)

Vite127.0.0.1:5191 proxies API127.0.0.1:8861 using synthetic `.runtime/work-ui-01`. The newer [OpenAI/Alice contract](openai-alice-wake.md) records the current full Realtime2.1 configuration, private credential-file reference and local keyword model. The earlier Qwen manual-preview choice below is historical. Current owner request separately authorized a small OpenAI trial, now closed; ordinary owner use remains explicit.

When reopening this preview, preserve its current configured provider instead of silently presenting a providers-off QA environment. No key belongs in frontend/Git. Scheduler/computer execution is still off in this UI runtime. Preserve the distinction between ready configuration, returned model output and verified user-visible results.

## Current 7 November status

Mac Web5190/API8831 selects GPT Live for voice, GPT6.1Sol for independent typed work, and pinned local Alice wake. See [voice lifecycle and actual capped trial](openai-alice-wake.md) and [current UI/activation QA](../../output/qa/2026-11-07-alice-home-wake/verification.md). The following older validation counts retain their original scope.

## Verification

[QA](../../output/qa/2026-11-02-conversation-desktop/verification.md) records 309 frontend checks, actual browser/draft/permission behavior, and Mac camera/microphone acquisition. Cloud speech/image understanding, native touch/keyboard and sustained operation remain separate. Use a separate QA tab for viewport emulation; clear it afterwards and do not resize the owner's active review tab.

## 6 November goal change

An explicit text goal change, including a held-out source layout, can update an existing Work run without leaving the conversation. A reviewed voice snapshot uses that same turn when the message carries its `voice_origin_ref`. The voice review screen can send that snapshot with `voice_steer` when one current run is clear, or when the owner picks among several. The same turn then shows one verified result for the new goal. The phrases, the one-run rule, and interruption recovery are in [conversation goal changes](conversation-work.md). The composer and Alice surface are unchanged.

## 4 November integration

This implementation is part of the unified PR74–77/main candidate. The described normal preview is the preserved Nov2 environment, not a newly deployed merged runtime. Local integration tests use a separate providers-off fixture. No new paid or human-media test is implied. [Merge QA](../../output/qa/2026-11-04-merge-74-77/verification.md).
