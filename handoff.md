# Group 2 Current Handoff

2 November2026, Asia/Hong_Kong. **Current software: OpenAI realtime + local Alice wake; Pi paused.** Active worktree `/Users/tantalum/.codex/worktrees/personal-agent-20261031/FYP`, branch `codex/openai-alice-wake-20261102`, based on [PR76](https://github.com/tantalum666/FYP/pull/76) head17df074. Current publication is recorded in [QA](output/qa/2026-11-02-openai-alice-wake/verification.md); push/merge/deployment are separate.

## Implemented and observed

Web remains the primary chat page with Alice and contextual actions. Existing shared VoiceService now admits OpenAI GA Realtime through a separate wire adapter; Qwen/Gemini remain. Browser16k PCM is converted at the OpenAI boundary to24k; output stays24k. Permissions, tool dispatch, context, cancellation and approved work reuse current services. [Contract](desk-companion/docs/openai-alice-wake.md).

Say Alice to wake is an owner opt-in. While waiting, audio goes to the connected desk's local sherpa detector; this preview is same-Mac loopback. Alice/Chinese-name synthetic samples trigger; ordinary test words do not. Actual local HTTP/ticket/WebSocket detection returned the keyword with cloud inactive. Browser waiting/off was verified; its temporary QA voice-ticket block was cleared. User's existing Full mode was preserved. Initial enable is required per page; reload/close stops listening. Quiet OpenAI ends after30 seconds, then local waiting resumes; errors disarm instead of charged retries.

Four paid synthetic Mandarin checks preserved failures. Mini had timezone/schema retries, truncated output, then a wrong09:30->10:30 reading. After generic tool/time/brevity fixes, full2.1 returned3 meetings at09:30/14:00/16:00 correctly with audio. Prompt also changed: not a controlled ranking. Current preview uses full2.1; Mini remains candidate. No live human wake/AEC/noise/background accuracy or speaker-latency score is claimed.

## Running preview and closed budget

Vite5191 (PID41034 at checkpoint) -> API8861 (PID80987), synthetic `.runtime/work-ui-01`. API uses this worktree's own `.venv` from frozen audio/dev extras. Explicit config: DESK_VOICE_PROVIDER=openai_realtime; DESK_VOICE_MODEL=gpt-realtime-2.1; voice=marin; DESK_WAKE_ENABLED=1; DESK_WAKE_MODEL_DIR points to this worktree's ignored `.runtime/models/wake`.

DESK_OPENAI_CREDENTIAL_FILE is the previously confirmed `/Users/tantalum/.codex/worktrees/grok-reviewed-fixes/FYP/desk-companion/.env.local`. Read it only through the protected loader; never print/copy its value. Separate text/background providers, scheduler and computer execution are off in this particular UI runtime. Recheck process ownership/active calls before reuse or restart. Do not silently replace this with providers-off QA.

The freshUSD1 test ledger at `.runtime/openai-alice-smoke-20261102/budget.sqlite3` is CLOSED: returned-usage upper estimate0.1692086, conservative accounted0.6499936 including unknown reservation. No more agent-paid checks under that round. Normal explicit owner use is separate; the older reportedUSD170 balance was not re-audited. [Budget](output/qa/2026-11-02-openai-alice-wake/budget-summary.json), [cost assumptions](output/qa/2026-11-02-openai-alice-wake/cost-scenarios.json).

Tests: full1716 backend passed, then16 focused checks including an additional idle-close case;314 frontend and build. A later test-only addition is identified in QA instead of pretending one command ran everything. Model files, audio, stores and keys remain ignored. No CI, Pi/VM restart, outside account or transaction action. Phone/native/background/human quality is still separate.

## One next step

Connect ordinary Alice long-task admission/recovery to existing Work through this stable conversation surface, starting with offline changed-goal/reconnect/unknown-result cases. Preserve [research](research/personal-agent-research-index.md) and [application Work](desk-companion/docs/application-work.md); real human wake/voice and consumer-agent journeys retain their own acceptance gates.
