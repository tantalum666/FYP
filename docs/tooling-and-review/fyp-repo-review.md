# FYP repository review for teammates and coding agents

Date: 14 October 2026. Original scope: `main` at `ccfac48`; implementation status refreshed after the 15 October #7–#14 merges. Group 2. Desk Companion is the current product. Senplate food-monitoring material is historical and is not the specification.

The hosted-API design, the Muse/Dot inference, and the provider recommendation are in [companion-architecture.md](companion-architecture.md). The public product teardown (Meta Muse, both Dots, gaps, and a task list) is in [companion-product-teardown.md](companion-product-teardown.md).

**Review update, 15 October 2026.** The independent review fixed permission, directory-opening, persona-version and draft-recovery defects, then merged #7–#14 with merge commits. The actual merged code passed 182 backend tests, 17 frontend tests, Ruff, typecheck, production build and npm audit (zero findings). [Evidence](../../output/qa/2026-10-15-grok-review-merge/verification.md). The 9 October figures below retain their date. PRs #4 and #5 remain separate.

**Omni follow-up,17 October.** The owner selected Qwen3.8 Omni and approved CNY5 maximum for synthetic trials. Independent voice/image adaptation and selected-key calendar/image trials are complete on draft [PR #15](https://github.com/tantalum666/FYP/pull/15), not main. [Contract](../../desk-companion/docs/qwen-omni.md) / [QA](../../output/qa/2026-10-16-qwen-omni-integration/verification.md). Default providers stay none; actual capture, multilingual quality, Pi and GUI remain open.

## Goals

From [product.md](../../product.md) and the 28 September proposal:

- One physical desk terminal for a home or office adult, shared by phone, computer, and the device’s own touchscreen.
- Mandatory posture loop: fixed camera, personal calibration, sustained visible head-and-shoulder deviation, a concrete prompt, then a new observation recorded as returned, still deviated, or unknown. Not a medical score.
- A local calendar and, since 6 October, a personal agent that can perform real but limited computer or software actions. Chat alone does not meet that later requirement.
- English by default, Simplified Chinese in the UI. The proposal’s voice evaluation is Mandarin and English. Cantonese is a later test, not a result we have.
- Three students, about six months, one prototype. Yuan Yuchen leads the software and AI work; the other two members lead hardware. The 40/30/30 split is a plan, not a grade.
- Replaceable hosted voice. The owner selected Qwen3.8 Omni on16 October. This run’s design uses hosted LLM APIs and keeps memory, tools, scheduling, persona, and the voice session in our code.

School files are unsubmitted drafts. Local software is not mentor approval or a Moodle upload.

## What is already on main

Verified on 9 October in an isolated database, with fake providers and synthetic pose points: 149 backend tests, 15 frontend tests, Ruff, TypeScript, production build, and browser checks. That is not a camera accuracy, a voice quality score, or a Pi run.

| Area | State on main |
|---|---|
| App shape | `desk-companion/`: React / TypeScript / Vite, one FastAPI process, SQLite. Phone, web, and the Linux always-on screen share the API and use different layouts. |
| Calendar | Day, week, month, recurrence, exceptions, reminders, CSV, ICS, read-only Google preview. No write-back to Google. |
| Tasks | Durable tasks, evidence, one pending follow-up, pause and snooze. A 1-second loop applies rules. Optional text advice is off and capped at 20 attempts a day. |
| Assistant | Draft tools for tasks, calendar, posture, device presets, and a bounded note job. The model cannot confirm. Owner approval is a separate request. |
| Computer jobs | Dedicated notes default off; an owner may configure one real folder. Approval binds exact text and scope, every directory component rejects symlinks, and independent read-back checks size/SHA-256. No shell or third-party GUI. |
| Owner memory/persona | Correctable facts, deletion from future context and a shared owner persona. Paired text/voice cannot read facts or decide memory drafts. Persona reset preserves monotonic versions. |
| Voice | Qwen Audio and Gemini Live adapters, PCM, barge-in, one session, time limits. Local Chinese/English wake word. Providers default to `none`. |
| Posture | MediaPipe landmarks plus team thresholds. Replay does not move hardware. No human-labeled accuracy yet. |
| Outputs | Named light and arm presets, 5-second claims, simulator and PCA9685. RIG-Arm is researched and not driven. |
| iPhone | Capacitor project, Keychain pairing, widget and cached local notifications. A physical iPhone network test is still open. |
| Old Senplate | Separate FastAPI/Postgres app under `apps/` and `services/`. Do not extend it for Desk Companion. |

Code map: `backend/desk/` (calendar, tasks, assistant, voice, jobs), `backend/desk/agents/` (camera, wake, outputs), `frontend/src/device/` (always-on screen), `frontend/src/workspace/` (assistant and device panels), `frontend/ios/`, `scripts/`, `config/`. Private runtime data stays in `desk-companion/.runtime/` and is gitignored.

## Separate unmerged branches

The #7–#14 batch is independent of the two earlier feature branches below. Open issue counts are not used as completion evidence.

| Item | Branch | What it contains | What it is not |
|---|---|---|---|
| [PR #4](https://github.com/tantalum666/FYP/pull/4) | `codex/full-body-3d-avatar` | Intact 2D A1 page companion, plus an earlier full-body VRM path that the PR text says is not the selected look. Large image set. | Not merged. Not a license to restart segmented 3D. |
| [PR #5](https://github.com/tantalum666/FYP/pull/5) | `codex/personal-agent-kernel-20261012`, stacked on PR #4 | Public Muse, Dot, and Grok studies; memory; durable work runs; routines; bounded MCP and browser fixtures; CI; Mac notes for some checks. Head discussed in the PR body was `11dc2b8` on 13 October. | Not merged. Not commercial-agent parity. Live models, general desktop control, and hardware are still gated there too. |

Read PR #5’s research before writing another product survey. Do not implement the next agent features on that branch. The owner asked for the #7–#14 stack on `main` instead.

## Strengths

- One owner, one process, one database. Identity, drafts, and device stop are explicit.
- Writes are proposals until a person approves the exact payload. Retries use operation ids. A lost write becomes unknown and is reconciled by reading, not by repeating.
- Voice tools are queued so a slow tool does not block the socket forever. Stop still has a slot when ordinary tool quota is full.
- Posture, calendar, and the agent share a desk, but posture code does not call the LLM to decide a lean.
- The retired food project, school originals, and decision log are still in the tree, with dates.

## Gaps, in the order they block a demo

1. Omni adapter and synthetic live trial evidence exist separately on PR #15. Main retains Audio/Gemini until merge. Naturalness, Cantonese, echo, Pi playback and the complete invoice remain unknown; ordinary configuration stays none.
2. Main supports bounded notes and one owner-named folder. General GUI, LCU, and a remote PC executor are not built. LCU was a candidate on 6 October and was not installed.
3. Owner facts and persona are implemented, but retention/archive and complete business backup remain open. Facts are not a full transcript or a biography.
4. Job history is not in the business JSON backup, and there is no archive UI. The cap is 1000 jobs.
5. Posture has no consented human labels, so the proposal’s F1 and false-alarm targets are plans. MediaPipe on Linux aarch64 has not been run on a Pi for this project.
6. RIG-Arm, the cleaner module, the optical character path, and a physical stop are untested. PCA9685 does not speak the arm’s servo bus.
7. iPhone signing on a real phone, Google OAuth with a real account, and an always-on desk install are unverified. There is no CI workflow on `main` (PR #5 adds one).
8. School Progress I was dated 26 October 2026 in the proposal timetable. This review does not submit that report.

## Next work

Use the current [handoff](../../handoff.md). First define one real target application task and allowed data, and validate it through the existing approval/read-back/cancel contract. Do not fork another queue. Owner facts, shared persona, quiet holds and Qwen/Gemini text adapters are already implemented; do not add duplicate versions of them.

Then address archive/backup and real-service/device validation. The CNY5 Omni synthetic trial is complete; further paid operating tests need their own budget and capture scope. Hardware and consented posture evaluation remain separate.

Run, from `desk-companion/`, for code changes:

```bash
uv run --no-sync pytest -q
uv run --no-sync ruff check backend scripts tests
cd frontend && npm test && npm run build
```

Use a throwaway `DESK_RUNTIME_DIR`. Do not commit `.runtime/`, credentials, or model weights.
