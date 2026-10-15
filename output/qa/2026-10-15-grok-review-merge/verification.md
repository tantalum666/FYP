# Group 2 · 2026-10-15 independent review and merge

User request: inspect Grok bot's Git work and merge it if sound. Scope: PR #6 and the #7–#14 code stack. Earlier A1 PR #4 and kernel PR #5 remain separate. No deployment, paid provider, real audio/video or hardware trial.

## Reading and isolation

- [Local full-read inventory](reading-inventory.json): 148 project-owned Markdown files, 13,432 lines, all read through EOF before editing. Initial branch: `codex/full-body-3d-avatar`, HEAD `50e174f50a4130b3c666f836f666f6aa4cde4b32`.
- [Remote version supplement](supplemental-inventory.json): 32 changed/new versions at the frozen #14 and #6 refs; all 809 unmatched lines emitted and read. Only byte-exact matching lines inherited the already observed local read. Fingerprints detect changes and are not reading proof.
- Excluded only Git internals, dependencies, caches, third-party/build material and automatic output/qa snapshots. The original full-read chunk cache remains local; it is not needed in Git.
- Managed review worktree used fresh locked dependencies and an ignored fixture runtime. Tests did not open the user's calendar/runtime. The earlier referenced chat was read with read_thread; it was background context, not merge authorization.

## Findings and fixes

| Finding | Reproduction/effect | Repair |
|---|---|---|
| Owner-memory boundary bypass | Paired display could list memory proposals and confirm them through the assistant, despite /api/memory returning 403. | Restrict proposals/decisions, local rules, packed text context/cache, advertised voice tools and forced voice calls by principal. Existing task/calendar tools remain available. |
| Folder ancestor race | After path validation, replacing an ancestor with a symlink redirected a write and left an unknown outcome. | Open every absolute-path component with directory handles and O_NOFOLLOW; new files remain O_EXCL and read-back is a separate open. |
| Persona version reuse | Reset deleted the singleton row, returning version 1; an old editor could become current again. | Persist source and increasing versions through reset; append migration preserves existing text. |
| Draft loss/recovery | Persona save errors reloaded over unsaved text; recovered memory saves could leave the same draft ready to duplicate. | Retain failed/conflicting drafts, explicitly load current text, and clear only the draft matching a recovered operation. |
| Existing development dependency finding | npm audit reported source-map-js 1.2.1, GHSA-68fv-2mgg-jv7q. | Lockfile-only patch to 1.2.2; final audit reports zero findings. |
| Stale tooling roadmap | Research still called facts/persona unimplemented and referred work to PR #5. | Reconcile all three tooling docs, current contracts and the historical merge procedure with the #7–#14 implementation. |

The owner-access, version-reset and ancestor-race regressions failed before their repairs and passed afterward. Original 175/17 green tests did not cover those defects.

## Actual merged-code validation

Code main: `2c1e465b4017a014d14aa2f5ef7293d182c930fa`. Its backend/frontend/tests tree exactly matched the reviewed fixed candidate before final reruns. PR #6 changes documentation and evidence only.

| Check | Result | Log |
|---|---|---|
| Backend pytest | 182 passed | [pytest.log](pytest.log) |
| Ruff | Passed | [ruff.log](ruff.log) |
| Frontend tests | 17 passed | [frontend-tests.log](frontend-tests.log) |
| TypeScript | Passed | [typecheck.log](typecheck.log) |
| Vite production build | Passed | [build.log](build.log) |
| npm audit | Zero reported findings | [npm-audit.log](npm-audit.log) |

One upstream Starlette/httpx test-client deprecation is recorded; there are no failed tests. These are local checks, not remote CI or live-provider/device results. [Backend commands](backend-results.json), [frontend commands](frontend-results.json).

## Browser validation

Browser plugin was not listed; used the available built-in CUA browser's Playwright/CDP in two fresh hidden tabs. URL: `http://127.0.0.1:5191/`, English desktop and Simplified Chinese 390×844. Only synthetic data was entered.

- Memory: saved, corrected and reopened a fact. Dropped an HTTP200 response after commit; the UI showed an unresolved save, reused the original operation on safe retry, kept one fact and cleared only its matching draft.
- Persona: two editors held the same version. Saving in the second made the first stale; 409 preserved the first draft. Explicit loading replaced it with the current persona. [Conflict screenshot](persona-conflict.png).
- Folder: no file before owner approval; one generated file after approval. Its 27 UTF-8 bytes and independent SHA256 matched the visible receipt. [Verified result](folder-verified.png).
- Narrow UI: meaningful content, localized controls, document/client/scroll widths all 390; navigation fits its own width. [390×844 screenshot](memory-mobile.png). High-level IAB screenshot sizing was corrected with a tab-level capture of the actual viewport.
- Page identity and content were checked; no framework overlay. Normal persona checks had no warnings/errors. The memory fault intentionally generated a connection error; interception was cleared before recovery.
- Both temporary tabs closed, viewport/interception cleared and fixture server stopped. No user browser tab was changed.

## Git delivery and remaining scope

[Code merge receipts](code-merge-receipts.json) bind each #7–#14 merge to its reviewed head. Fixes were normally pushed to #7/#8/#9, inherited by ordinary merges into later heads, and the dependency patch landed with #14. No force push or branch deletion. The #6 docs branch ordinarily merged current main and resolved its four living-document conflicts in favor of current behavior, then reconciled research and logs.

This #6 delivery includes current product/handoff/decision/work logs, both READMEs, architecture/memory/operator guidance, collaboration/historical merge routing, and three tooling docs. A broken historical clipboard link was converted to a dated observation. Public product research remains dated; external capability or price claims were not refreshed into new live recommendations.

Remaining product work: one named real application/remote-PC task, retention/archive and complete business backup, owner provider/model/spend choice, real voice/wake/AEC and consented posture labels, Pi/iPhone/optics/RIG/cleaner validation. School files and submission status were not changed. One next step is recorded in handoff.md.

## Closeout checks

621 current local links passed; the runtime credentials link is deliberately local and excluded. Protected school/input/art/retired-code Git paths have no changes. The primary A1 checkout remains at its original HEAD with only this round’s QA untracked. All staged source/docs passed whitespace checks; npm’s raw typecheck stdout retains its trailing blank line as an explicit evidence exception. Staged Gitleaks returned no findings. The application source remains byte-identical to validated merged main. [Checks](closeout-checks.json), [Gitleaks result](gitleaks.json).
