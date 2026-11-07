# Group 2 · Persistent work across applications

31 October 2026. [Work](agent-runs.md) now connects to the existing [application executor](application-execution.md). The model can select a sequence of bounded operations, inspect their independently verified results, ask for a missing choice and continue. This is separate from ordinary short chat and from unrestricted GUI control. [Local acceptance](../../output/qa/2026-10-31-personal-agent-cross-app/verification.md).

## Responsibilities and admission

`application_work.py` supplies three registered adapters and exact-receipt/parent-run checks. `AgentRunService` owns persisted decisions and waiting states. `JobService` remains the only computer queue; `ApplicationExecutor` owns staged real-app writes and immutable versions. `PermissionService` remains the software-authority source. No new task store, execution queue or model approval tool is introduced; no schema migration is added.

The owner chooses model Work, at least one existing task, `allow_application_jobs: true`, and optional `application_source_ids` from the configured application-input catalog. The UI lists the source names before starting. Task records require the existing business-context permission; input text additionally requires explicit source sharing with the exact approved provider. Public/synthetic MCP grants cannot be combined with this application scope.

Admission binds the executor scope, selected input hashes and the current software permission version. The task must be selected and observed at the request's version. Application dependency/base IDs must belong to this Work; neither a guessed job ID nor a different task's file becomes a dependency. Every selected input stays bound to each queued job even if the planner omits a source reference. Changed source bytes or a different execution workspace stop further writes.

The default application-job budget is6, bounded1–8. It is separate from the existing three non-application effects; all adapter calls still share the1–16 tool-attempt cap and the1–24 model-attempt cap. Model mode admits at most10 selected evidence items including application inputs. These are bounded counts, not a monetary allowance. The existing report/CSV store limits remain separate from office-file versions.

## Registered tools

| Tool | Behavior |
|---|---|
| `application_source_read` | Reads a selected text source or uses the owned Chromium to read selected local HTML; returns bounded whole-line ranges, source hash, coverage and untrusted evidence |
| `application_job_draft` | Strict existing `ApplicationJobInput` for workbook/document/PDF/text; prepares an exact job on the existing queue and records its original reference |
| `application_artifact_read` | Reads bounded JSON lines of an existing current-Work file's independent readback; distinguishes immutable history from an unresolved current result |

Readback summaries preserve Calc computed values, errors, text and formulas without copying redundant display metadata into every reasoning turn. Full saved job receipts remain inspectable. Oversized results are explicitly marked and use the bounded read tool; context overflow blocks rather than silently omitting evidence. Source text, page text and file content never grant permissions.

## Approval, continuation and recovery

In Ask first mode the Work pauses at the shared job card. An exact approval queues that child; the Work waits for the application without spending model calls on status polling. The UI shows `waiting_effect` while an already-approved application runs and `waiting_review` when the owner is actually needed. After the adapter reopens and verifies the result, the next reasoning decision receives that result.

Full access is captured only for newly admitted opted-in Work. It can authorize its newly prepared app jobs through the existing versioned policy. Turning Full on later does not retroactively approve older Work or a recovered pending job. Revocation fences jobs that have not executed. No model can select its own permission mode, approve a job, enable a new executor or connect an account.

Preparation and approval are checked at the existing Store operation transaction. Job execution and publication checkpoints also check the parent Work's control state, session, privacy and deadline. An expired session or paused/cancelled parent cannot keep a queued child running. Graceful shutdown includes `waiting_effect`; unrelated ordinary jobs retain their existing behavior.

A crash after child preparation but before linking adopts the exact existing operation/request/child digest; it does not prepare a replacement. A lost file-save completion is reconciled by reopening the existing published file. Recovery never repeats the write. Cancellation stops pending work but keeps verified files. The application adapter returns a bounded cancellation observation without reopening office files under the parent control lock. Previously recorded verification is retained; resume/final verification independently reads the files again.

For a revised filename, the latest output must match current published bytes. A predecessor explicitly replaced by a verified successor in the same Work is reopened from immutable history. Both versions' hashes, application identity and operation markers are checked. An unrelated change to the current file or a tampered historical file is not accepted as completion.

Calc execution normalizes supported comma/semicolon and sheet-reference syntax outside string literals before passing formulas to UNO. The original approved request remains unchanged; independent verification uses the same semantic formula comparison. This fixes a real `APPLICATION_FORMULA_ERROR` found during this acceptance rather than requiring a planner to know an undocumented separator convention.

## Owner interface

Web and phone share the application selection and exact job cards. Active/review-required actions come before completed files, near the Work controls. File content can be expanded before approval. History downloads use immutable versions; current application files and the separate Work report/evidence pair have distinct headings. Technical tool activity is collapsed by default.

The actual UI test approved a workbook once, observed automatic continuation to a document proposal, then cancelled the parent Work. The workbook remained downloadable and the document was not published. A393px phone check confirmed the same state and matching downloaded bytes. Scope review listed only the selected task/file and the appropriate Ask first mode; its test draft was discarded without creating a second Work. No native iOS or soft-keyboard result is claimed.

## Reproduce the real-app acceptance

Use the existing isolated desktop and environment variables from [the executor setup](application-execution.md). Set text/voice providers and background extraction off in the process environment. The runner installs an in-memory **scripted offline planner**; its fixture destination is never called. Use a fresh core runtime for `run` and preserve failed cases.

```sh
python scripts/application_work_acceptance.py --run-real-apps \
  --runtime .runtime/work-case --report /absolute/local/qa-case --phase run
# Expected exit73: revised workbook saved, completion deliberately lost.
docker --context colima-fyp-apps restart --timeout 3 desk-applications
python scripts/application_work_acceptance.py --run-real-apps \
  --runtime .runtime/work-case --report /absolute/local/qa-case --phase resume
```

The synthetic owner changes36 copies/HKD900 to48 copies/HKD950 and accepts a50-copy minimum. Real Calc moves the feasible choice from Aster776.60 to Birch902.00. Reconciliation preserves SHA/mtime, then real Writer/PDF produces the final files. The runner asserts returned cell values rather than trusting planner prose. It makes zero paid model requests and zero purchases. Its `review`/`serve` modes support an isolated Ask first UI fixture; normal application configuration and real user stores are not changed. Serve previews through a supported local frontend origin, for example Vite5191 proxying the fixture API; do not widen the origin policy for an arbitrary test port.

## Remaining boundary

No live model has passed this new multi-step case. Ordinary Alice/Omni chat still has its existing short-turn behavior; this Work flow requires explicit admission. Complete the ordinary conversation/voice-to-Work handoff and offline unseen variants before a separately scoped paid comparison. Real email, authenticated shopping/travel accounts, arbitrary websites, payment and remote notifications remain separate journeys. Pi software work resumed on6November; only the red-LED investigation is deferred. Pi deployment/results are recorded in the [current QA](../../output/qa/2026-11-06-passwordless-device/verification.md).


No live model has passed this new multi-step case. Ordinary Alice text, held-out source layouts, and a reviewed voice snapshot can admit an explicit goal change into an existing Work run, including interruption and unknown-result recovery, offline only. After that change, the same conversation shows one verified Markdown readback from the existing deterministic executor. A later status ask reads the same file again and does not run the executor. An explicit continue ask advances that run once through the same offline executor. See [conversation goal changes](conversation-work.md). The short chat loop is otherwise unchanged. The voice review screen can update one current run with the reviewed snapshot and still starts new work when nothing current is selected. Real email, authenticated shopping/travel accounts, arbitrary websites, payment and remote notifications remain separate journeys. Pi software is active; only red-LED investigation is deferred.
