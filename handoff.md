# Group 2 Current Handoff

2 November 2026, Asia/Hong_Kong. **Web is conversation-first; Pi stays paused.** Active worktree `/Users/tantalum/.codex/worktrees/personal-agent-20261031/FYP`, branch `codex/conversation-desktop-20261102`, based on [PR75](https://github.com/tantalum666/FYP/pull/75) head34de1e7. Publication and merge/deployment are separate; see [QA](output/qa/2026-11-02-conversation-desktop/verification.md).

## Current result

Web defaults to `?page=assistant`: full-page conversation, visible composer, calendar/tasks in navigation. No width-dependent chat modal. ConversationWorkspace retains the existing panel/draft across views while suspension releases media. Responsive navigation and floating-avatar avoidance preserve Alice and her saved preference. [Contract](desk-companion/docs/desktop-conversation.md).

Local camera preview/mic metering have explicit controls and late-permission cleanup. Share this frame reuses the existing voice image path in a compatible call; no continuous-video claim. Actual Mac camera1280x720 and built-in microphone input were checked.309 frontend/type/build pass; actual150%860x454,1280x800,393x852, draft return and permission/navigation checks passed. Native app/keyboard and fresh cloud speech remain unverified.

## Runtime and owner choice

Vite5191 -> API8861, synthetic `.runtime/work-ui-01`. API PID47713 at this checkpoint runs ordinary create_app, scheduler off, `DESK_VOICE_PROVIDER=qwen_omni`, and the existing protected `~/.config/desk-companion/qwen.env` via DESK_QWEN_CREDENTIAL_FILE. Separate text/background and computer execution remain off; explicit typed chat uses this same configured Omni. No credential content changed. Recheck process ownership before reuse.

Owner chose to try voice personally instead of authorizing the proposed automated RMB1 test. Keep the service ready for that explicit interaction; do not run paid tests or reopen older budgets. Do not silently revert to the providers-off QA launch. OpenAI and other candidates remain separate. Account for an active owner call before restarting services.

The user's Chrome tab was restored to normal1291x681 at100% after an intrusive narrow test. Further QA used separate-tab CDP emulation and was cleared/closed. Never resize the owner's live review tab for testing. Web settings `?page=device` and Pi display `?surface=device` are different surfaces.

PR74's durable Work/office queue and1,701 backend result are prior evidence, not this round. [Application contract](desk-companion/docs/application-work.md), [research](research/personal-agent-research-index.md). Pi[PR73](https://github.com/tantalum666/FYP/pull/73) and power/kiosk/wired gaps stay paused. No CI, VM restart, external account or transaction action.

## One next step

Connect ordinary Alice/Omni long-task admission/recovery to existing Work through this stable chat surface, reusing goal/voice-prefill and selected-task authority. Start offline with changed-goal/reconnect/unknown-result cases; model autonomy and consumer-agent journeys retain independent gates.
