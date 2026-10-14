# FYP repository review for teammates and coding agents

Date: 14 October 2026. Scope: `main` at `ccfac48` (software merge `8ca728d` plus the 9 October closeout). Group 2. Desk Companion is the current product. Senplate food-monitoring material is historical and is not the specification.

The hosted-API design, the Muse/Dot inference, and the provider recommendation are in [companion-architecture.md](companion-architecture.md). The public product teardown (Meta Muse, both Dots, gaps, and a task list) is in [companion-product-teardown.md](companion-product-teardown.md).

## Goals

From [product.md](../../product.md) and the 28 September proposal:

- One physical desk terminal for a home or office adult, shared by phone, computer, and the device’s own touchscreen.
- Mandatory posture loop: fixed camera, personal calibration, sustained visible head-and-shoulder deviation, a concrete prompt, then a new observation recorded as returned, still deviated, or unknown. Not a medical score.
- A local calendar and, since 6 October, a personal agent that can perform real but limited computer or software actions. Chat alone does not meet that later requirement.
- English by default, Simplified Chinese in the UI. The proposal’s voice evaluation is Mandarin and English. Cantonese is a later test, not a result we have.
- Three students, about six months, one prototype. Yuan Yuchen leads the software and AI work; the other two members lead hardware. The 40/30/30 split is a plan, not a grade.
- Replaceable hosted voice. The provider is not chosen. This run’s design uses hosted LLM APIs and keeps memory, tools, scheduling, persona, and the voice session in our code.

School files are unsubmitted drafts. Local software is not mentor approval or a Moodle upload.

## What is already on main

Verified on 9 October in an isolated database, with fake providers and synthetic pose points: 149 backend tests, 15 frontend tests, Ruff, TypeScript, production build, and browser checks. That is not a camera accuracy, a voice quality score, or a Pi run.

| Area | State on main |
|---|---|
| App shape | `desk-companion/`: React / TypeScript / Vite, one FastAPI process, SQLite. Phone, web, and the Linux always-on screen share the API and use different layouts. |
| Calendar | Day, week, month, recurrence, exceptions, reminders, CSV, ICS, read-only Google preview. No write-back to Google. |
| Tasks | Durable tasks, evidence, one pending follow-up, pause and snooze. A 1-second loop applies rules. Optional text advice is off and capped at 20 attempts a day. |
| Assistant | Draft tools for tasks, calendar, posture, device presets, and a bounded note job. The model cannot confirm. Owner approval is a separate request. |
| Computer jobs | Default off. Creates a new UTF-8 file under the app’s `computer-notes/` directory, then reads it back (size, SHA-256, name). No shell, no arbitrary path, no third-party GUI. |
| Voice | Qwen Audio and Gemini Live adapters, PCM, barge-in, one session, time limits. Local Chinese/English wake word. Providers default to `none`. |
| Posture | MediaPipe landmarks plus team thresholds. Replay does not move hardware. No human-labeled accuracy yet. |
| Outputs | Named light and arm presets, 5-second claims, simulator and PCA9685. RIG-Arm is researched and not driven. |
| iPhone | Capacitor project, Keychain pairing, widget and cached local notifications. A physical iPhone network test is still open. |
| Old Senplate | Separate FastAPI/Postgres app under `apps/` and `services/`. Do not extend it for Desk Companion. |

Code map: `backend/desk/` (calendar, tasks, assistant, voice, jobs), `backend/desk/agents/` (camera, wake, outputs), `frontend/src/device/` (always-on screen), `frontend/src/workspace/` (assistant and device panels), `frontend/ios/`, `scripts/`, `config/`. Private runtime data stays in `desk-companion/.runtime/` and is gitignored.

## Two open GitHub items

The repository’s open-issue count is 2. Both are pull requests. There is no separate open issue thread.

| Item | Branch | What it contains | What it is not |
|---|---|---|---|
| [PR #4](https://github.com/tantalum666/FYP/pull/4) | `codex/full-body-3d-avatar` | Intact 2D A1 page companion, plus an earlier full-body VRM path that the PR text says is not the selected look. Large image set. | Not merged. Not a license to restart segmented 3D. |
| [PR #5](https://github.com/tantalum666/FYP/pull/5) | `codex/personal-agent-kernel-20261012`, stacked on PR #4 | Public Muse, Dot, and Grok studies; memory; durable work runs; routines; bounded MCP and browser fixtures; CI; Mac notes for some checks. Head discussed in the PR body was `11dc2b8` on 13 October. | Not merged. Not commercial-agent parity. Live models, general desktop control, and hardware are still gated there too. |

Read PR #5’s research before writing more product analysis. Implement agent features on that branch unless the owner asks for a `main`-only patch.

## Strengths

- One owner, one process, one database. Identity, drafts, and device stop are explicit.
- Writes are proposals until a person approves the exact payload. Retries use operation ids. A lost write becomes unknown and is reconciled by reading, not by repeating.
- Voice tools are queued so a slow tool does not block the socket forever. Stop still has a slot when ordinary tool quota is full.
- Posture, calendar, and the agent share a desk, but posture code does not call the LLM to decide a lean.
- The retired food project, school originals, and decision log are still in the tree, with dates.

## Gaps, in the order they block a demo

1. No hosted provider is configured, tried, or paid for. Naturalness, Cantonese, echo, and the real invoice are unknown. Adapters exist only for Qwen and Gemini.
2. The only executed computer action on `main` is a note in the app directory. General GUI, LCU, and a remote PC executor are not built. LCU was a candidate on 6 October and was not installed.
3. Long-term memory the owner can correct is not on `main`. Tasks are not a biography. PR #5 starts a fact store; it is unmerged.
4. Job history is not in the business JSON backup, and there is no archive UI. The cap is 1000 jobs.
5. Posture has no consented human labels, so the proposal’s F1 and false-alarm targets are plans. MediaPipe on Linux aarch64 has not been run on a Pi for this project.
6. RIG-Arm, the cleaner module, the optical character path, and a physical stop are untested. PCA9685 does not speak the arm’s servo bus.
7. iPhone signing on a real phone, Google OAuth with a real account, and an always-on desk install are unverified. There is no CI workflow on `main` (PR #5 adds one).
8. School Progress I was dated 26 October 2026 in the proposal timetable. This review does not submit that report.

## Tasks a teammate or Codex can pick up

Match the task to the branch. The product teardown is [companion-product-teardown.md](companion-product-teardown.md); do not write another one. Do not self-host an LLM. Do not reverse-engineer a commercial client; that cannot show the hosted model, as [companion-architecture.md](companion-architecture.md) notes.

| Priority | Task | Done when | Avoid |
|---|---|---|---|
| P0 | Read [companion-product-teardown.md](companion-product-teardown.md) and [companion-architecture.md](companion-architecture.md). | The next patch names which branch it targets and which roadmap item it is. | A third Muse/Dot survey. |
| P1 | Context-packer test on the existing text adapter, no live HTTP. | The recorded request has persona and the selected task, and lacks the API key and deleted text. | A new provider. |
| P1 | Prove the advice loop stays silent when the provider is `none` or the cap is spent. | A regression test fails if a model client is constructed in those cases. | Calling Qwen from the 1-second tick. |
| P2 | One owner-named app or folder action with approval and independent read-back. | A lost receipt stays unknown and a second approve does not write twice. | Shell tools, LCU, or a parallel job framework if PR #5 already has the ledger. |
| P2 | One editable persona text used by both voice and text setup. | UI language still follows the user; medical claims stay out. | Copying a vendor system prompt. |
| P3 | Fake-provider voice test: partial audio cannot approve; hang-up does not cancel an approved job. | Tests only. Real mics wait for a key and a spend cap. | A billing trial hidden inside a refactor. |
| P3 | Hardware preset or posture-label tooling, by the hardware members. | Simulator and “physical success” stay different statuses. | LLM-chosen motor angles. |
| P4 | After the owner sets a cap, run the Mandarin/English command list on Qwen, then Gemini if the account works. | A short log of model id, region, failures, and usage. No accuracy claim beyond that log. | Treating September price examples as the invoice. |

Run, from `desk-companion/`, for code changes:

```bash
uv run --no-sync pytest -q
uv run --no-sync ruff check backend scripts tests
cd frontend && npm test && npm run build
```

Use a throwaway `DESK_RUNTIME_DIR`. Do not commit `.runtime/`, credentials, or model weights.
