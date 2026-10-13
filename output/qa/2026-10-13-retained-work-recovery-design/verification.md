# Retained-work recovery design verification

Completed 2026-10-13. Design only; application implementation and user runtime data were not modified.

## Delivered

- `planning/2026-10-13/retained-work-recovery-design.md`: one recommended terminal-watch lifecycle slice, accurate archive/Trash/reclaim/purge vocabulary, capacity/retry/tombstone bounds, and separately gated Work/file extension
- `reading-ledger.json`: inherited same-task 186-document intake plus relevant full-text contract rereads and focused actual source inspection
- `checks.json`: actual link existence, trailing-whitespace, bound arithmetic and final design hash checks

## Important findings

File reservations currently carry their own unique operation receipt; dropping them can resurrect an old upload/publication. Source-from-artifact and publication dependency validation also precede the inner file receipt lookup. Work deletion must preserve voice claims and proposal ownership guards, and must fence currently steerable terminal runs. Unknown pending files and unknown remote child outcomes cannot be treated as completed cleanup.

The bounded first implementation should recover a saved-watch slot only after a fresh owner-confirmed atomic permanent removal. Trash remains counted and genuinely restorable. Finite lifetime identity/receipt bounds prevent moving the original capacity leak into an unbounded tombstone table. Existing record IDs and original operation keys never create replacement effects.

## Checks actually run

Inspected current contracts, SQLite schema/write methods, retry paths, dependency fields, filesystem publication/reconciliation code and existing crash/admission test source. Checked all seven direct links exist (six contracts plus independent review), document whitespace, and 259 × 256 = 66,304 proposed receipt bound. No application test suite, new runtime probe, mounted browser, live model, external service, migration, deletion or Git command was run. This evidence does not establish implementation correctness or UI acceptance.

Only the assigned design and this QA directory were written. Shared product/decision/handoff/work logs were deliberately not edited because the parent owns the frozen capacity publication. Parent may summarize this finalized proposal after its current publication boundary; there is no runtime recovery feature to advertise yet.

## Independent-review revision

The finalized design incorporates `../2026-10-13-terminal-watch-retention-audit/review.md`. The reviewer ran separate synthetic-store probes establishing that old Store bootstrap resets schema version2 to1 and that executescript effects can survive its surrounding context rollback. Its abstract state enumeration reached the proposed259-receipt bound with every admitted Trash restorable. These are reviewer-run findings, not lifecycle implementation tests run by this design worker.

Corrections: operational backup/no-downgrade contract instead of an impossible retrospective guard; early supported-binary schema check and true individual-statement transactional migration with trigger replacement; all-receipt count thresholds and distinct-key no-op rejection; explicit retained_count independent of ordinary list length; small expiring action/session/epoch/inventory-bound preview cache with separate strict final-click purge confirmation; committed replay before preview lookup; lifecycle-result callback branching and selected-detail clearing; watch-only three states and no global-search extension. `checks.json` records the revised document hash and static contract-presence checks. No application code, runtime data, migration or deletion changed.
