# PR5 compatibility repair and merge verification

31 October 2026, Asia/Shanghai. Owner request: repair and merge PR5. Baseline main is `18d205607d5c2eb9f3f23143bbf8eacbc29b7077`; original PR5 is `11dc2b84cebe6e8250b28ca4442fc91f0dfec676`. The original heads are retained by an ordinary merge, without force-push or replacement of current Alice/Omni. Remote publication is recorded separately after local acceptance.

## What was repaired and integrated

The [current integration contract](../../../desk-companion/docs/pr5-integration.md) describes actual modules and operator steps. Shared main files were restored first and older behavior integrated at explicit boundaries. Work/source/artifact/watch/routine services reference the current task/calendar core. Current facts, approval policy, normal chat replay and real application execution stay authoritative.

- Migration now ignores the directory link-count change caused by legitimate SQLite WAL files while retaining directory identity/private-mode and database single-link checks.
- Current `owner_memories` facts are projected into retained Work, preserving version/history/expiry/aliases. Original PR5 facts have an explicit atomic conversion; conflicts preserve both originals and abort. No actual user database was migrated.
- Forgetting scrubs canonical/revision text and relevant cached copies while retaining content-free request digests. Existing keys cannot recreate a forgotten fact. Already-linked Work proposals remain protected after their text is redacted.
- Normal Omni replay IDs and explicitly retained text-thread IDs use distinct endpoints. Provider dispatch rechecks privacy at the HTTP transport boundary. Raw JSON has a portable explicit depth bound rather than relying on parser recursion.
- Cleanup attempts every service shutdown. Current computer jobs reject a changed approved intent before dispatch, and private-hidden job APIs return metadata while keeping cancellation available.
- Tasks exposes the shared Work/watch entry on web and phone. Approval uses current action cards; the ordinary memory editor is reused. Actual UI testing repaired a narrow desktop Work modal, newly created retained-thread selection, duplicate history rendering and precise memory-approval wording. A production-hook regression proves that consuming a voice prefill does not unmount its Work composer.

Original A1 presentation, demo-record execution and conflicting old voice restrictions are superseded by the current accepted implementations. They remain in Git history. The demo's useful hidden-job/intent regressions were ported to the current executor. [Scope/disposition](dispositions.json), [original-path inventory](integration-inventory.json), [actual reading scope](reading-record.json). This is an integration review and full local regression run, not an exhaustive security audit of every historical line.

## Final local checks

| Check | Result | Evidence |
|---|---|---|
| Complete final backend | **1,686 passed**, two warnings | [Log](backend-verified.txt) |
| Complete final frontend | **300 passed**, zero failed/skipped | [Log](frontend-final.txt) |
| Current note/privacy/retained-context/local-check boundaries | 67 passed | [Focused run](final-boundaries.txt) |
| Current voice/provider regressions | 99 passed | [Focused run](current-voice-regressions.txt) |
| Fact conversion, context, publication and voice Work | 78 passed | [Focused run](compatibility-sixth.txt) |
| TypeScript/Vite production build | Passed; existing large 3D chunk advisory | [Build](build-final.txt) |
| Ruff | Passed | [Lint](ruff-final.txt) |
| Lock metadata | Frozen lock checked offline | [Lock](lock-check.txt) |
| Alice/runtime/fallback and historical asset hashes | Passed, no asset bytes changed | [Assets](asset-check.txt) |
| Staged publication secret scan | No leaks found | [Scan](secret-scan.txt) |
| Changed Markdown links | 504 local references, no broken links | [Links](link-check.json) |

Checks ran on this Mac with Python 3.14.5 using the preserved existing development environment. The optional Playwright extra and its dependencies were resolved into `uv.lock`; no Chromium binary was installed. The legacy voice fixtures were changed to syntactically admitted synthetic endpoints while retaining fake transports; endpoint protection was not relaxed to make tests pass. No CI or paid API was used. A generic-key heuristic matched fictional task-step text; its marker wording was changed and the consent regression rerun ([1 passed](fixture-marker-check.txt)), without a scanner exception or runtime-code change. Early diagnostic runs remain in ignored local `.runtime/pr5-repair-intermediate/`, not mistaken for final counts.

## Actual current-main migration fixture

Unmodified baseline main code created a schema1 fixture containing a corrected/expiring fact, its revision history, custom aliases, an existing task, an unapproved job and full-permission policy. The two explicit offline upgrades advanced schema1 → 2 → 3. All **45 original tables remained row-for-row identical**, and the new runtime independently read the same fact/version, policy and review-state job. The retained-context projection sees the canonical fact. [Machine-readable result](current-main-migration.json).

Additional tests cover original PR5 fact IDs/versions/source attribution, forgotten rows, retry idempotence and transaction rollback on conflicting identities. Existing real runtime directories and keys were neither migrated nor copied.

## Actual web and phone journey

CUA controlled the in-app browser against an isolated fixture at `http://localhost:8832`. Providers were `none`; application/public-browser/capture executors were disabled. Desktop was explicitly measured at **1280 × 800** and phone at **393 × 852**, with document widths equal to their viewports. Native Simulator/touch/keyboard and live speech were not exercised.

1. Web Tasks → Work → select the existing synthetic task → review scope/retention → start local compilation. Closing and reopening the panel preserved the run. Actual Markdown and CSV artifacts passed independent readback.
2. A second deterministic run was seeded through the real local API with one typed task-note proposal to exercise review without a paid model. It waited at the linked review; the original task remained unchanged before approval.
3. The actual browser opened the exact action card and clicked **Allow once**. Exactly one note was written to the existing task. Work then reconciled the effect and reached its structural completion state.
4. A watch created in the UI had no initial alert. The approved progress change produced one review for that exact task/field. Acknowledge reduced pending reviews to zero; subsequent reads/restart did not generate another review.
5. The phone read that same progress note. Alice and Plan/More remained visible; no extra bottom-navigation destinations were added.
6. The browser downloaded the actual 1,515-byte report. Its SHA matched independently read server bytes. Two completed runs retain four files total; the test service restart preserved their hashes, terminal states and single progress note.
7. Explicit saved-chat retention was enabled only on the synthetic fixture. Creating a thread selected it correctly; a local memory request remained a draft until Allow once. Refresh recovered exactly two stored messages, rendered once. The ordinary Alice memory page read the same new fact; there is no parallel `personal_memories` table. Provider usage stayed zero.

[Independent file/task readback](ui-independent-readback.json), [restart and retained-thread readback](ui-restart-and-retained.json), [seeded exact review request](ui-review-run.json). Screenshots: [desktop Work](web-work-desktop.jpg), [watch acknowledgment](web-watch-acknowledged.jpg), [phone progress](phone-task-readback.jpg), [phone Alice](phone-alice.jpg), [recovered thread](retained-conversation-recovered.jpg), [canonical fact page](canonical-memory-readback.jpg). Relevant browser console warnings/errors were absent. The old narrow modal is retained as [before-fix evidence](web-work-before-width-fix.jpg).

The synthetic preview was stopped, temporary viewport overrides reset and agent-created tabs closed. Prior user preview services, original private keys/data and other worktrees remain unchanged. The downloaded file is a synthetic fixture, not a school submission.

## Remaining product boundaries

This integrates the repaired PR5 foundations. It does not prove a live model autonomously completes the complex office task, authenticate a real mailbox/merchant, buy anything, issue a ticket, deliver remote phone notifications or deploy to Pi. Public/synthetic connector and browser capabilities remain default-off and separately reviewed. Existing paid rounds remain closed. Work/source/artifact storage has finite retention limits and is not part of the older portable business-data export.

## Publication

Local acceptance is complete. The owner has authorized updating and merging original PR5 after these checks. The publication receipt will record the exact repaired head, GitHub merge result and main readback; pushing a branch alone is not counted as merge or deployment.
