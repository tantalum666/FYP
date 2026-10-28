# Group 2 · Software delivery gates

28 October 2026. This is an acceptance map for the current Desk Companion, not a new feature wish list or a completion percentage. The accepted journey remains [task → permission → execution → independent result → later continuation](../../planning/2026-10-06/personal-agent-discussion-and-next-steps.md). This semester prioritizes software and AI; Luwu/Pi integration is best-effort and currently paused.

An implemented module, a passing local test, a real provider trial, native-device acceptance and a completed deployment are different states. The [current QA](../../output/qa/2026-10-28-native-memory/verification.md) is local-only. Qwen is the measured baseline; other candidates remain open.

| Delivery gate | Current evidence | What is still required for acceptance |
|---|---|---|
| One useful task completed and continued across web/phone | Persistent tasks, selected-task chat, approved bounded jobs, result evidence, cancel/unknown-result handling already exist; local tests cover these services | Run one representative task through the actual interfaces: clarify scope, approve exact file contents, independently verify the result, reopen the same task on phone, then resume after a lost response/restart without duplicate execution or a false completion. Treat this as integration acceptance, not a request for another task system |
| Reliable personal memory | Owner-approved facts, correction/deletion/expiry, current-fact retrieval and private scopes exist. This checkpoint fixes older-than-40 lookup/drafts and replay invalidation; shared memory search and draft recovery have actual browser evidence | Broader long-running, mixed-language conversations; provider wording and natural reference quality. This checkpoint's deterministic/mock tests do not score real-model intelligence |
| Natural unified text/voice assistant | Unified Omni, shared tools and bounded context; dated real Qwen trials with fictional facts and synthetic audio | Human Mandarin/Cantonese/mixed-language speech, background noise/AEC, interruption recovery, first useful word and resource use; compare candidates under the same tasks only after a new spending authorization |
| Usable phone and desktop | Alice home, Plan/More, shared editor/session recovery, desktop workflows and phone browser checks; current source builds/installs/launches on iPhone17Pro Simulator | Actual native taps/soft keyboard/recovery remain open because current mirror/native automation cannot reliably deliver app touches. Real-device pairing/TLS, accessibility, notifications, power/temperature and network interruption need independent evidence |
| Helpful follow-up without repeated interruption | Tasks, quiet hours, delayed checks, deterministic recap/suggestions, preferences and notification configuration exist | Multi-day use with reopen/restart/timezone changes and observed notification delivery; confirm follow-ups are useful and can be silenced. Do not infer usefulness from feature counts |
| Required posture and physical terminal | Fixed-camera calibration/visibility/duration/feedback/re-observation logic and replay fixtures exist; bounded output presets are separate | Labelled human posture trials, measured false alarms and feedback/retest behavior; later Pi/Luwu driver, stop and bench validation. No medical benefit or physical-motion claim without measurement |

## Next software slice

**Complete the first row's task journey in the isolated local environment.** Reuse TaskService, the existing job queue, approvals and result evidence. Use a disposable fixture file and offline/scripted model responses, inspect the same task on web and phone, and fix whichever integration failure the run exposes. Keep cancellation, version conflicts, lost acknowledgements and server restart in that journey's acceptance record.

Native input acceptance stays explicitly open; repeated successful builds do not close it. The present limitation is recorded in the [phone implementation note](../../planning/2026-10-28/phone-simulator-implementation.md). Do not let that tooling issue stop independent task/AI work or describe browser interaction as a native pass.

## Working constraints

Local tests, builds and real UI/readback checks only; no GitHub CI. Keep Alice and the compact phone navigation. Reuse shared boundaries instead of adding another conversation store, polling loop or executor queue. No new hosted-model usage, external account actions, live capture or hardware restart is implied by this map. Source publication follows [AGENTS](../../AGENTS.md); report submission remains separate.
