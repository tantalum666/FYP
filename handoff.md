# Group 2 · Current handoff

16 November 2026. Continue in `/Users/tantalum/.codex/worktrees/alice-motion-20261113/FYP`, branch `codex/alice-natural-motion-20261113`, based on main6153b41d. [PR123](https://github.com/tantalum666/FYP/pull/123) remains open/unmerged. No CI or new paid calls; A3 and original Alice retained.

## Latest completed work

Added short contextual motions with quiet intervals: smile/nod, curious tilt, compact open-hand explanation, glance, shoulder relaxation and pondering, alongside the corrected wave. Clicks vary across four responses; idle motion yields to interaction. The real phone check caught/fixed a visibly finished gesture still rejecting the next tap. Shared timing now governs both pose sampling and input coalescing. Gesture elapsed time is separate from capped spring-physics time; existing pause/reduced-motion behavior remains.

387 main frontend tests and366 runtime-compatible tests, types/build pass. Actual desktop/phone gestures and final four-response phone cycle were observed; real rig checks cover palms, torso clearance, fingertip extent and fixed feet. More froze rendering; reduced motion disposed/restored one canvas. [Current QA](output/qa/2026-11-16-alice-variety/verification.md).

## Actual delivery

- **Mac web:** compatible frontend activated at `http://127.0.0.1:8831/?page=assistant`; `?surface=phone` is the phone browser view. Original API PID28112/backend520ab563/data retained; A3/version9 and protected files unchanged. New frontend `dist-motions-20261116`; previous `dist-motion-20261113-v2` and old hashed assets retained.
- **Native Simulator:** rebuilt/installed on original iPhone17Pro/iOS26.5. Pi8891was unreachable; actual UI/idle glance was checked using a process-only Mac8831launch override. The saved `desk.server.origin.v1` preference is absent, confirmed by read-only plist inspection: the previous Pi address was also a launch argument, not a saved setting. Current native checking is Mac-backed, not Pi acceptance. No new physical-iPhone, native-tap/keyboard or paid-voice acceptance.
- **Pi:** existing pinned relay check failed. No16November deployment/restart/network change. Last verified frontend activation is13November; physical animation/performance remains unverified. Power/red-LED diagnosis stays deferred.

Private artifacts and rollback receipts: `~/.config/desk-companion/alice-motions-20261116/`. Keep original live-agent-eval source/runtime/vendor dependencies and prior backups. Temporary Vite servers are stopped; normal Mac8831remains available. CUA/Xcode capability availability changed during closeout; do not infer further UI actions occurred after those tools were removed.

## Personal-agent status

Read the [current capability/runtime map](desk-companion/docs/personal-agent-status.md) and [research index](research/personal-agent-research-index.md). GitHub main still contains the reviewed11November Grok integration, but not all later features are in the retained ordinary backend. FYP Gmail self-send has8November real evidence;16November local catalog shows saved Gmail connection, Google Calendar configured/unconnected and Microsoft apps unconfigured/unconnected. No fresh token/mailbox/transaction trial was made.

Real-model controlled shopping/flight/browser tests exist. Actual merchant owner takeover, continuous real inbox-to-task tracking, payment/order/ticket receipts and reliable unattended completion remain open. The shipped browser lacks owner-input transport; fixture pause/return is not a usable account journey.

## One next product step

Implement a real same-browser owner-control and explicit-return flow on the existing JobService, then verify it before claiming authenticated merchant work. Reuse durable jobs, session/version checks, cancellation and independent result readback. Do not open a paid budget or perform unspecified mail/purchase actions. Pi rendering remains a separate pending verification when connectivity returns.
