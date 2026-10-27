# Group 2 · Maintainable AI/software milestone

28 October2026, Asia/Hong_Kong. The owner authorized continuing AI/software work, focused Markdown reading, maintainable implementation, current handoffs and GitHub publication of important milestones. This is a complete local implementation/verification checkpoint; remote publication receipts are recorded separately below and in the PR.

## Scope and source

A fresh managed checkout was created from refreshed main46ac167 at`software-ai-maintenance/FYP`, on`codex/software-ai-maintenance-20261028`. The existing archive structure and hardware/school content are preserved. Previously local Alice/unified Omni/Linux/web/phone application source was copied selectively using Git's tracked/non-ignored application list, then checked in this independent environment. Private runtime, credentials, databases, downloaded personal models and authoring backups were not copied for publication.

[Initial copy manifest](application-copy-manifest.json) records281 application files/133,728,165bytes before integration edits. It is a transfer baseline, not the final source hash list. Main's Vite8.3.5 was retained; the older source checkout used8.3.1. Dependencies were installed from the resulting lockfiles in the new checkout. The old dirty checkout and its snapshots remain preserved.

[Reading record](reading-record.json) lists focused documents and sections. The latest explicit owner instruction replaces the former automatic full-Markdown pass. AGENTS and routing were updated accordingly. Historical local evidence not included in this publication is identified as local material, without broken links or a claim that it was republished.

## Changes and validation

| Area | Change and actual proof |
|---|---|
| Phone structure | Home, Plan, management, calendar read and environment lifecycle are separate modules; root920→363lines. Shared LoginView and event editing remove desktop/phone copies. Module responsibilities are in the[contract](../../../desk-companion/docs/software-maintenance.md) |
| Calendar reading | Home/day query deduplication, concurrent independent ranges, refresh coalescing, stale-response rejection and scope disposal. Five new tests cover these behaviors, including errors and recovery |
| Event editing | Web Add→unsaved guard→Continue→Save persisted one29Oct14:00–15:00 event; phone Next date read it. A held event read was released after Close without reopening the editor;[receipt](late-editor-read.json) |
| Selected task / AI | Handshake now carries task_id. Server reads the real task and binds owner/task replay; invalid, hidden or non-owner scopes fail before provider connection. Ten new backend checks include the public WebSocket route, current version refresh and cross-task/owner rejection. The frontend handshake test confirms no microphone request for text |
| Task review | Existing fictional task selected in phone; local progress message produced a correctly titled review card. Cancel left task version1/statusTo do and no added note. Ending discussion kept prior visible messages and removed the active task label |
| Draft safety | Underlying assistant draft survived Plan and event interactions. A dirty progress note blocks Calendar/Tasks switching; closing offers Continue/Discard. Discarding that note leaves the separate assistant draft intact |
| Modal/readability fixes | A blocked discussion message is now visible inside the modal footer. Expanded conversation sits above the home header;[final conversation](phone-conversation-final.png). The[before screenshot](phone-task-review-before-layer-fix.png) retains the found overlap |
| Session recovery | Both web and phone share the preview/session lifecycle. Two controlled expirations deleted only temporary sessions in the named fictional preview, then the foreground client renewed and retained exact unsent input with no login screen. [Web result](web-session-recovery.json),[phone result](phone-session-recovery.json). No write was automatically retried |
| Persistence | [Independent readback](data-readback.json) confirms one shared-editor event, no discarded/cancelled task note, zero pending proposals and providersdisabled;[helper](readback.py) reads no credential file |
| Native | Current source built/installed/launched on iPhone17Pro/iOS26.5;[build result](native-build-result.json),[log](native-build.log),[actual home](iphone-simulator-final.jpg). Native touch/keyboard was not reclassified as passed |

## Automated checks

- **303 backend tests passed** in the integrated checkout, [log](backend-tests.log). Ten selected-task tests extend the prior293. Existing Starlette/httpx deprecation warning remains.
- **65 frontend tests passed**, [log](frontend-tests.log). Five calendar-reader tests plus one task-handshake test extend the prior59.
- Ruff passed across backend/scripts/tests, [log](ruff.log).
- TypeScript and Vite8.3.5 build passed, [log](frontend-build.log). Existing>500kB bundle warnings remain; this is not a bundle/energy benchmark.
- The actual phone browser used393×852; desktop1280×720. Final observed phone state had one assistant, one canvas, document width393 and no framework overlay. Fault-injection requests deliberately produce401/abort diagnostics; these are kept separate from clean-run console health.
- CI was added for backend lint/tests and frontend tests/build, with model/background/executor flags off and read-only repository permissions. Action usage was checked against official repository documentation. Workflow creation alone is not a green CI result.

## Failures and repairs retained

The actual desktop session fell back to Login after the preview runtime changed; this led to the shared recovery hook rather than a repeated manual login. The test then expired sessions intentionally and proved retained drafts in both clients. Business rows were not deleted.

A first delayed-read attempt outlived its interception handle. It is not counted as a successful late-response test. The successful retry performed hold→Edit→Close→release within one browser call and cleared interception in finally. Browser Use required an explicit Fetch resource type and an empty patterns array to clear interception; no Document navigation or browser warning was bypassed.

Minor scripting/formatting attempts failed before applying their intended edits (a missing optional formatting glob, and a documentation script encoding/quoting error); successful source/build results are the evidence. These were not app/runtime failures and were not hidden as successful checks.

## Remaining limits

New AI tests use scripted providers and actual application services, not new hosted-model answers. Qwen remains the prior tested baseline; other candidates still need equal-scenario evaluation. Old paid budgets remain closed. No real microphone/camera/user-screen collection, Pi/Luwu action, live external calendar account, school report edit/submission or external contact occurred.

The previous simulator automation did not expose WebView controls reliably. Current build/launch/visual proof does not certify native Plan taps, software keyboard, VoiceOver, real phone TLS/pairing, media interruptions, notification delivery or energy/thermal performance. These remain separate acceptance work. No main merge or device deployment is implied by branch publication.

## Publication and handoff

Important software is prepared on the independent branch based on archived main; older rejected-art PRs and independent PR20 are not blindly merged. Published runtime assets retain their existing licences and source metadata. Current authoring originals and complete raw historical QA remain local where explicitly stated. Staged-file, secret, link and remote-readback results are finalized in the publication records. [Handoff](../../../handoff.md) keeps the live environment and one next step.

Prepublication scope check:213 initial staged paths, zero private runtime/credential/editable-authoring paths. Staged Gitleaks found no secrets. Full whitespace check retains original licence text and raw Vite/Xcode log spacing; the source/document check excludes only the two unchanged licence files and verbatim QA logs and is recorded separately. This is not a claim of zero warnings in unmodified third-party text. Active scoped documentation links resolve; omitted historical local artifacts are explicitly marked in[publication document scope](publication-document-scope.json).
