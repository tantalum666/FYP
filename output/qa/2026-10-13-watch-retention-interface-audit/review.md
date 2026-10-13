# Independent terminal-watch interface audit

2026-10-13. QA-only audit of the cloud checkout. Inherits the same parent 186-document intake; focused reading is recorded in `reading.json`. No application edits, Git commands, user databases, real deletion, external calls or browser/device interaction.

## Verdict

Pass for the tested software interface boundary after one confirmed integration defect was fixed by the implementer. Actual mounted desktop and narrow-screen interaction remain gated and untested. SSR and deterministic production-hook execution are explicitly **not mounted browser evidence**.

## Confirmed defect and independent retest

The ordinary `useResponsibilities` read hook originally discarded an older overlapping request's authority denial after a newer request had succeeded. A real production-hook fixture returned `fresh=true` after `/responsibilities` rejected with 403 `PRIVATE_CONTEXT_HIDDEN`. That left the shared owner fence active and could leave maintenance enabled. The original failing reproducer was reported before the implementation changed.

The implementer now treats authority denials in the same mounted owner epoch as decisive regardless request ordering, synchronously invalidates the shared fence and clears private value. `ordinary-denial.test.ts` independently verifies the fix. Old successes cannot re-enable maintenance. No audit application changes were made.

## Executed evidence

- `adversarial.test.ts`: eight distinct production-hook adversarial cases: cancel while a preview is in flight; reordered trash/purge previews; nonterminal detail refusal; captured retry and late successful write after privacy change; malformed success retaining exact body/key with no automatic retry/fresh operation; strict boolean consent and expired preview; successful read arriving after denial; monotonic deadline despite wall-clock rollback
- `ordinary-denial.test.ts`: the confirmed older-read denial regression, and hidden mode calling only the safe ordinary list while showing twenty retained slots despite an empty visible list. No maintenance or private capacity endpoint is called
- `disposition.test.ts`: actual ordinary acknowledgment disposition clears selected review detail without invoking a stale selected-detail reload; actual maintenance success clears selection and makes no Work handoff or incidental write
- `semantics.test.ts`: actual final-button callback passes strict true only for purge; render and cancel produce no mutation; bilingual invalid/unknown aggregates never become zero/free slots; long hostile titles/IDs are escaped as text
- Final source verification: **15/15 independent adversarial cases, 214/214 full frontend tests, TypeScript typecheck passed; 19 pinned files unchanged across final verification**. Full frontend test suite rerun, plus TypeScript typecheck. Exact outputs are retained in `full-frontend.log`, `adversarial-results.log` and `typecheck.log`
- `source-hashes.json` pins responsibility interface source, its mutation/fence dependencies and relevant shipped tests; `source-stability.json` checks those bytes after verification

Cancel is measured as zero retention-mutation POSTs. Preparing the server preview itself intentionally uses a read-only preview POST. It is not described as zero network requests.

## Contract inspection and limits

The final confirmation names one exact title/ID and versions, baseline/review counts, retained receipt count, slot release, irreversible normal-recovery loss, independent tasks/Work retention and backup/download/provider exclusions. Trash/Restore explicitly release zero slots; restore does not restart or reset budgets. Retained usage is a separately validated aggregate; missing, invalid, unavailable and over-limit metadata display unknown. Hidden mode has safe aggregate display and stop controls but no maintenance entry.

Current preview identity, parent epoch, snapshot/freshness, session/personal/offline events and both wall/monotonic expiry fence captured confirmation. An unknown result retains the original in-memory serialized request/key until explicit retry or authority/view invalidation. No timer or read refresh automatically retries or mints a replacement operation. Only the final purge button passes strict true; the source has no model callback connection to this component. Backend/model dispatcher refusal is independently owned by runtime audit, not claimed from interface inspection.

The production confirmation and usage SSR has English/Chinese text semantics and escaped long content. CSS inspected for min-width zero, wrapping, overflow-wrap and non-fixed-width actions. This does not measure pixel geometry, keyboard/focus handling, touch behavior or horizontal overflow at any actual desktop/mobile viewport. Those require the separately gated mounted-browser run.

The full frontend regression includes existing Work handoff, voice, private-context, drafts, capacity and watch behavior. It does not establish real model quality, hardware behavior, actual user data preservation, live network authority or deployed migration correctness. Runtime service/migration evidence is separate.

Parent owns product/handoff/decision/work-log updates and publication. This reviewer wrote only this QA directory.
