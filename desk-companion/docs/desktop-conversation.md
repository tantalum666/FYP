# Group 2 · Desktop conversation and local media

2 November 2026. Owner direction: a responsive Codex/ChatGPT/Grok-style primary conversation page with usable Mac camera/microphone. This supersedes the older desktop modal/docked assistant arrangement. Pi DeviceApp and the phone's full-screen Alice surface remain separate.

## Page and lifecycle

The default Web route is `?page=assistant`. Conversation is the primary page; calendar/tasks/settings are adjacent views. Keep the composer visible at normal and zoomed window sizes. Narrow Web navigation has four primary actions plus a drawer.

ConversationWorkspace keeps the shared AssistantPanel mounted across navigation with a separate draft-guard scope. Unsent text/messages stay in memory; leaving chat suspends media. Logout protects unsent/in-flight chat, and the existing principal boundary clears private state on identity change. This does not add persistent chat history or a second model/approval/queue service.

Alice retains its appearance and saved position preference. Floating geometry must avoid the composer without rewriting that preference. Existing contextual approvals and concise-copy rules remain authoritative.

## Local devices and provider

The camera button opens a device panel. Open camera requests video only; Test microphone meters audio locally, without recording, speaker loopback or upload. LocalCapture owns stream lifetime, including late/cancelled/superseded permission requests. Stop, close and background release the streams.

Share this frame explicitly sends one frame during a compatible active voice call, using VoiceAudio's existing bounded encoding, rate and disconnect checks. This is not continuous camera streaming. Preview alone is not evidence of model understanding.

The main microphone starts the existing provider-backed session. With Qwen Omni configured, explicit typed/voice input uses the same model path. Opening the page/device panel makes no paid request. The owner elected to test manually this round; do not infer a new automatic test budget.

## Current local preview

Vite127.0.0.1:5191 proxies API127.0.0.1:8861, using synthetic `.runtime/work-ui-01`. Current launch uses `DESK_LOCAL_PREVIEW=1`, `DESK_VOICE_PROVIDER=qwen_omni`, and `DESK_QWEN_CREDENTIAL_FILE` pointing to the existing protected local file. No key belongs in frontend config or Git. `DESK_TEXT_PROVIDER=none` and `DESK_TEXT_BACKGROUND=0` do not disable the configured shared Omni path. Scheduler/computer execution are off in this particular UI runtime; it is not unattended cross-application deployment.

When reopening this preview, preserve the current explicit voice configuration instead of silently presenting a providers-off QA environment as the normal app. Recheck process ownership and handoff. Configuration readiness is distinct from a successful billable request. OpenAI and other candidates are not excluded by restoring the existing Qwen baseline.

## Verification

[QA](../../output/qa/2026-11-02-conversation-desktop/verification.md) records 309 frontend checks, actual browser/draft/permission behavior, and Mac camera/microphone acquisition. Cloud speech/image understanding, native touch/keyboard and sustained operation remain separate. Use a separate QA tab for viewport emulation; clear it afterwards and do not resize the owner's active review tab.
