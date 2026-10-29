# Group 2 · Assistant permissions and task continuity

29 October 2026, Asia/Hong_Kong. This continuation began with a real task/file/phone journey and then incorporated the owner's explicit correction: approvals and Full access must work consistently on **web and app**, with simpler phone navigation. Current source is on `codex/assistant-permissions-20261029`, based on open PR64 head `b02d92b132a83dccb4674abb25f33d7613fbcd28`. Publication is recorded separately in `publication.json`; local completion is not a merge or deployment.

## Result

The shared assistant now carries action review, Allow once / Not now, execution state, stop, recovery and verified file results. The composer and Settings share an actual owner-only, versioned Ask first / Full access preference. Phone management uses full-screen navigation and keeps Alice as the home. Task results lead back into the same selected-task conversation. [Permission contract](../../../desk-companion/docs/assistant-permissions.md) records exact scope, provenance and limitations; [before audit](audit.md) records the original interaction problems.

## Local verification

| Check | Actual outcome / evidence |
|---|---|
| Task binding regression | English/Chinese Editor preview originally lost task scope: 2 failures / 6 passes in [original tests](../2026-10-28-task-journey/before-tests.txt). All six local file command variants now use one scope helper. 8 journey cases cover normal/restart/crash-after-write paths |
| Forgetting regression | [Before](forgotten-replay-before.txt): retrying a forgotten Remember operation reinserted its original user text into a new RAM conversation, despite not restoring the persistent fact. Retired metadata now blocks that replay without retaining the text. [31 focused checks](forgotten-replay-after.txt) cover EN/ZH, restart, changed body under old key and a legitimate new request |
| Backend | **489 passed**, [log](backend-tests.txt). Includes owner-only/versioned policy, stale revocation fencing a delayed Full request, paired/internal/expired denial, policy change during generation, queued revocation, manual approval survival, task provenance, physical exclusion, cancellation and durable applied-effect recovery |
| Frontend | **89 passed**, [log](frontend-tests.txt); TypeScript/Vite [build](build.txt) and [Prettier](format.txt) pass. No new dependency versions |
| Lint | [Ruff](lint.txt) passes on backend/scripts/tests |
| Current native build | Capacitor sync, corrected configuration helper and pinned framework preparation succeeded; final [Xcode build/install/launch](native-build.json) on iPhone17Pro/iOS26.5 succeeded. [Live frame](11-native-current.jpg) shows the new Ask first entry and Alice |
| Desktop browser | 1365×900 actual inline approval, Full access automatic file action, verified result, settings and Chinese labels checked. [Inline review](04-web-inline-approval.jpg), [Full result](05-web-full-access-result.jpg), [final settings](14-web-settings-zh.jpg) |
| Phone browser | 393×852 and 320×740, plus a short393×420 viewport. Full-screen Calendar/Tasks/More, back/draft guards, task history → Continue with Alice, permission choice, cancel, inline result/recovery checked. Final [task result](12-phone-task-results.jpg) and [permission chooser](13-phone-permissions-final.jpg). A long task-title/button collision found in this final pass was repaired and visually rechecked |
| Native interaction | **Not accepted.** Fresh mirror Plan tap again produced no app transition. Build/live frame are valid; actual taps/soft keyboard, VoiceOver, real-device TLS/pairing, notifications and power remain separate gates |

The full backend suite has one existing Starlette/httpx deprecation warning. Vite retains the existing >500kB chunk advisory. `policy-tests-initial.txt` contains initial test-harness/signature errors, not a claimed product baseline. `native-sync.txt` includes a wrong helper-path invocation after successful sync; it was corrected to the existing `frontend/scripts/configure-ios-features.cjs` ([configuration](native-configuration.txt)), then [preparation](native-preparation.txt) and the final native build passed. No tests were weakened to hide failures.

## Actual task and recovery journey

The earlier [journey record](../2026-10-28-task-journey/reading-record.json) and its screenshots predate the owner's navigation correction; those layouts are superseded. Its business evidence remains valid:

1. Created the fictional task “Demo: prepare a software review note”, prepared a linked note and approved exact content through the UI. Independent API and filesystem reads verified the file and task association.
2. A second approval's real HTTP200 response was intentionally dropped with origin-scoped CDP Fetch. The isolated API was restarted. Recovering the same operation returned one original job and unchanged file SHA/mtime. [Restart readback](../2026-10-28-task-journey/restart-recovery.json).
3. On phone browser, checked the original file again, cancelled another unexecuted action, recorded progress and explicitly completed the task. [Final independent readback](../2026-10-28-task-journey/phone-final-readback.json) proves 3 succeeded/1 cancelled linked actions, 2 files unchanged, cancelled-file absence and `user_confirmed` completion. A file receipt alone did not complete the task.

With the new interaction implemented, the actual [permission readback](ui-readback.json) verifies:

- “Permission card demo”: one-time owner approval, succeeded, 75 bytes, independently checked SHA.
- “Full access demo”: automatic policy version2, succeeded, 83 bytes, independently checked SHA.
- “Declined phone demo”: **expired**, not a user-decline claim; no file.
- “Phone approval check”: explicitly Not now, cancelled, no file.

For “Inline recovery demo”, dropped a real approval response after it reached the server. The inline recovery restored the same job/result while preserving the separate unsent draft. During the pending response, permission controls remained usable independently of the business-write queue. [Readback](inline-recovery-readback.json) shows one job/file, actual SHA and final **Ask first, version5**. All Fetch interception was cleared. No normal owner data was migrated or modified; all fixture contents are fictional.

## Final source and preview

- Current browser target: `http://localhost:5190/`; phone browser: `?surface=phone`. API is127.0.0.1:8833, isolated `desk-companion/.runtime/task-journey-20261028`. Use localhost for Vite so the old127.0.0.1 memory preview cookie does not collide. No Origin allowlist was widened.
- API was restarted after the final retention repair. Providers are `none`, background AI/extraction/push and Linux executor are off; only the fixed local-note executor is enabled for these fixtures. Current policy is Ask first.
- Current native app uses launch-only `-desk.server.origin.v1 http://127.0.0.1:8833`. Saved device address and real-device TLS policy remain unchanged. Mirror `http://localhost:3200/` is the installed app stream, not a browser emulation. Temporary browser viewport overrides are reset at closeout.
- Final browser error/warning reads returned empty. Earlier deliberately injected network failures belong to the recovery test. No live media, hosted-model calls, external-account actions, Pi/Luwu work or school-document changes/submissions occurred.

## Reading, documentation and publication checks

Focused reading continued from the same task rather than restarting the archive. [Reading record](reading-record.json) separates full files from relevant chapters. Updated product, permission/job/memory/Omni/task/maintenance/architecture/operator/agent-loop contracts, delivery gates, phone implementation note, design brief, readmes, decisions, work log, entry and concise handoff. Internal links, scoped diff, sources and staged secrets are checked before publication; exact results go in `publication.json`.

Source hashes in `source-manifest.json` identify the implementation checked, without pretending a hash is a full read. Screenshots retain the existing AliceChan attribution: edisonlee55 / yuna0x0, [source metadata](../../../desk-companion/frontend/public/avatars/alice/source.json), [CC BY-SA4.0](../../../desk-companion/frontend/public/avatars/alice/LICENSE.md). No new model asset or private authoring original is published.

## One next software slice

Use offline/scripted providers for one mixed calendar/memory/file task, define partial-success and restart behavior, revoke permission between effects, and resume using only existing receipts. The current HTTP loop still ends after one effect-producing tool result; no general multi-step completion claim is made. Native input acceptance remains open independently. All validation stays local; **no GitHub CI**.
