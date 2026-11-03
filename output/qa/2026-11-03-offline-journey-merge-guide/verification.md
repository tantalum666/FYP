# Offline-journey merge guide

3 November 2026. Docs only. No feature code. Codex merges; this record does not merge #78, #79, or #80.

## Reading

- `AGENTS.md` as the workspace rule.
- `product.md` current requirements through the 2026-10-30 application section.
- `handoff.md` in full on main, then the #78, #79, and #80 tips.
- `decision-log.md` was not reread from the start. The #79 and #80 appends were read from the diffs.
- `desk-companion/docs/pr5-integration.md` in full on main, and #79's last-paragraph diff.
- `desk-companion/docs/integration-acceptance.md` on #78 tip `765b5fe` (not on main).
- `desk-companion/docs/mailbox-journey.md` on #79 tip `5e1e722`.
- `desk-companion/docs/shopping-fixtures.md` on #80 tip `4a04770`.
- `docs/merge-guide.md` historical rehearsal, so the new guide points at it instead of repeating #20–#50.
- `output/qa/2026-10-28-grok-review-merge/verification.md` reviewed-behaviour table.
- `desk-companion/docs/software-maintenance.md` "Integrated review invariants".
- `research/personal-agent-research-index.md` through section 6, plus the #79 and #80 gap-table hunks.
- Pull request bodies and file lists via `gh pr view` for #78, #79, and #80. File lists for draft #73–#77 via the pulls files API.

This is the file list, not a claim that every historical markdown was reread.

## Live state used

`origin/main` was `dac527b386c268caa96d9388d0c11d206b4f6856`. Open and not merged:

- #78 `cursor/integration-acceptance-harness-dcc2` `765b5fef1e7ad63ae4a595a964fa9467c1804c9e`
- #79 `cursor/mailbox-offline-journey-9739` `5e1e72211ed528af71539285a0c54f255b190686`
- #80 `cursor/shopping-fixture-journey-0767` `4a04770b0fdfd5589d58cdc41efba55afe175c2a`

GitHub reported each `MERGEABLE` / `CLEAN` against main. No calendar offline-journey pull request or remote branch was present. Drafts #73–#77 were still open. Their tips are in the guide.

## Merge-tree

`git merge-tree --write-tree --name-only`:

- #79 onto #78: conflict only in `work-log.md`. `handoff.md` auto-merged.
- #80 onto #78: conflict only in `work-log.md`. `handoff.md` auto-merged.
- #80 onto #79, and the reverse: conflicts in `assistant_routes.py`, `decision-log.md`, `handoff.md`, `product.md`, `research/personal-agent-research-index.md`, `work-log.md`. `app.py`, `assistant.py`, `runtime.py`, and `modules.md` auto-merged. The merged tree contains both router includes, both runtime services, the mailbox tick hook, and both decide branches. `assistant_routes.py` still needs the manual keep-both resolution in the guide.

Journey command suites were not re-run. Verification for this change is the link check below.

## Docs updated

`docs/offline-journey-merge-guide.md`, the historical pointer in `docs/merge-guide.md`, a short `handoff.md` note, a short `work-log.md` note, and this file.

## Link check

Local relative targets of the new guide were checked after the file was written. The only relative path that failed was `desk-companion/docs/shopping-fixtures.md`, because that file exists on #80 and not on this branch. The guide now points at the #80 blob URL instead. Remaining local targets (`docs/merge-guide.md`, the 28 October QA note, `software-maintenance.md`, `research/personal-agent-research-index.md`, and the handoff link to this guide) exist. `gh pr view` in the same session still read #78, #79, and #80 as open, not merged, at the tips in the guide. No calendar journey was in `gh pr list --state open`. Journey pytest suites were not run.
