# Group 2 · Desktop conversation and Mac media verification

2 November 2026, Asia/Hong_Kong. Branch `codex/conversation-desktop-20261102`, based on PR75 head34de1e7. The owner requested normal Web proportions, a Codex/ChatGPT/Grok-style chat interface and Mac microphone/camera.

## Findings and changes

Actual Chrome was at150% zoom, with a CSS viewport860x454. The old1200px threshold turned chat into an oversized modal. The preceding preview launch also explicitly disabled providers, making the microphone unavailable despite existing integration.

Web now defaults to the assistant page. ConversationWorkspace keeps the existing AssistantPanel and unsent draft across navigation with a separate guard scope; leaving chat suspends media. Composer height/width, compact navigation and floating-avatar avoidance were corrected. Obsolete docking CSS was removed. No new backend, model client, execution queue or dependency was introduced.

LocalCapture owns device lifetime and late permission results. MediaDevicePanel provides explicit local camera preview/mic metering. A selected camera frame reuses VoiceAudio image encoding/transport during a supported active voice call. Continuous video is not claimed.

## Actual checks

| Check | Observed result |
|---|---|
| Main Web chat | A primary page, with no assistant modal or framework overlay |
| Layout | Actual150%860x454,1280x800 and393x852 checked; no horizontal overflow; composer remains inside the viewport |
| Floating Alice | In short original viewport, avatar bottom299 is above composer top311; header space remains clear |
| Draft navigation | Exact unsent synthetic text survived Chat -> Tasks -> Chat; only that test draft was cleared |
| Narrow navigation | Focus enters menu; Escape and selecting the current page both close it |
| Permission menu | Ask first retained; popover fits short viewport (top104.6/bottom377 within454); no authority change |
| Actual Mac camera | FaceTime HD1280x720, readyState4, paused=false; preview stopped; no frame saved/uploaded |
| Actual Mac microphone | Built-in input produced changing meter readings; test stopped and panel closed; no recording/upload |
| Qwen readiness | Existing protected configuration validates and main voice button is enabled; owner chose manual trial, no agent-paid test |

[Structured checks](interaction-checks.json), [desktop layout](desktop-1280.png), [original150% layout](desktop-150-percent.png). These actual captures show the accepted layout; the provider caption was subsequently shortened to Qwen Omni. No user-supplied browser screenshot, unrelated tab inventory, device image/audio, credential or runtime database is published.

## Test-window correction

In-app tab binding returned `browser.user is unavailable`. CUA native Chrome identified the actual150% zoom; the supported Chrome extension supplied DOM/screenshots. Native app screenshot capture was a thumbnail and was not used as proof.

An initial narrow-width test changed the owner's visible tab. The owner queried whether it was the device UI. Restored the normal Web window and100% zoom; further checks used a separate QA tab with tab-scoped CDP emulation. Readback showed QA393x852 while the owner remained1291x681. Cleared/closed QA and left the owner's tab open. This was a workflow correction, not a Pi change.

No app console error was observed in the separate final QA tab; warnings came from a wallet extension. Full accessibility/native keyboard and sustained voice performance were not tested.

## Local validation and runtime

309/309 frontend tests and TypeScript/Vite build pass. New tests cover late/overlapping device requests, stream cleanup, stale denial, one-frame sharing after disconnect, and avatar/composer geometry. [Tests](frontend-tests.txt), [build](build.txt); the existing large-chunk warning remains. Backend source/dependencies are unchanged; previous backend scores retain their original date.

API8861/Vite5191 use synthetic work-ui-01. API now loads existing private Qwen credentials through DESK_QWEN_CREDENTIAL_FILE with DESK_VOICE_PROVIDER=qwen_omni. Separate text/background providers, scheduler and computer execution remain off; explicitly typed chat uses the configured Omni path. Startup makes no model request. The owner declined the proposed RMB1 automatic test and will click personally. No fresh cloud response/latency/quota/network success is claimed.

Updated product, entry/handoff, decision/work log, UI-copy, desktop-conversation, Omni/maintenance and dated Web guidance. No CI, Pi/VM restart, private-account change or transaction. Publication is separate from merge/deployment. Next implementation step remains Alice/Omni long-task admission/recovery through existing Work.

Publication: sourceff0b401 pushed to [draft PR76](https://github.com/tantalum666/FYP/pull/76), stacked on PR75. GitHub readback matches the exact source head, open/draft/unmerged.317 local links, formatter, staged diff and secret/scope checks passed. [Checks](publication-checks.json), [receipt](publication.json). Final follow-up changes documentation only.
