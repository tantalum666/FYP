# Repository cleanup and teammate review — 26 October 2026

The owner requested that Senplate be archived in one place and teammates' pending PRs be reviewed, repaired and merged. Work uses an isolated main-based worktree; the original checkout and unpublished AliceChan/Omni workspace are preserved. No model API, real media, hardware or deployment was started.

## Hardware PR

[PR #17](https://github.com/tantalum666/FYP/pull/17), by xuz204077-prog, was repaired at `0f7fbb19b17ab4801e5f3d8d621c022a85197e1d` and merged as `4417e3656959bd3deb7e0d42a2e42654723dfba4`. A remote read-back confirmed closed/merged. [Review](pr17-review.md) and [independent validation](pr17-validation.json) cover Pi record attribution, design targets, shaft dimensions/currency, bounded command requirements, all 9 PDF pages, 13 images / 30 links and 453 relative links. No CI checks/statuses existed for the reviewed head.

## Archive and preservation

5,127 existing files were relocated under [archive/senplate](../../../archive/senplate/README.md): the food runtime, iPhone/web/API/tests, plans/research, assets/brand, procurement workbook, food school deliverables and historical QA. [Relocation manifest](../../../archive/senplate/archive-manifest.json) records each original/new path and SHA256 before/after. 5,111 relocated files are byte-identical, including all 731 media/document/font/archive files and 7 licence files. Original binaries and licences retain their bytes; historical JSON and frozen snapshots retain their dated meaning. Navigation-link edits, three runtime/dependency file repairs and split root histories are explicit exceptions, not misreported as identical copies.

Root README/product/handoff now route to current Desk Companion and hardware work. Root decision/work logs retain the post-pivot history and link to the archived food portions. The canonical group record retains all member identities and shares; its old food-specific fields are preserved in an exact archived snapshot. School originals, current desktop proposal/logs and application business source are checked separately. Latest local AliceChan/Omni functionality is identified as unpublished rather than claimed present in main.

## Repairs found during relocation checks

- The deeper archive path exceeded macOS's 103-byte Unix socket limit. Senplate's owned development cluster now uses loopback TCP only; existing clients already use that transport. A fresh isolated cluster is created for verification; previous private project databases are not reused or reset.
- npm audit reported Vite advisories in both workspaces and source-map-js 1.2.1 in the retired frontend. Vite is pinned to 8.3.5, its required build dependencies are updated, and the archive resolves source-map-js 1.2.2. [Vite maintainer advisory](https://github.com/vitejs/vite/security/advisories/GHSA-rq7h-c2jc-7f22) and [source-map-js patch](https://github.com/7rulnik/source-map-js/releases/tag/v1.2.2) document the relevant fixes. No automatic major upgrade or force audit fix was used.
- A link to a generated private credential file in the active README is now a local path instruction, avoiding a broken GitHub link.

## Executed checks

| Check | Result and evidence |
| --- | --- |
| Full Markdown reading | 176 versions / 16,752 lines; [ranges and drift checks](reading-record.json) |
| Current backend | [182 passed](desk-pytest.log), one upstream Starlette deprecation warning |
| Current frontend | [17 passed](desk-frontend-test.log); [typecheck and production build](desk-build.log) |
| Archived backend | [55 passed](senplate-pytest.log), two upstream deprecation warnings; fresh isolated PostgreSQL |
| Archived frontend | [typecheck and production build](senplate-build.log) |
| Ruff | [current](desk-ruff.log) and [archived runtime](senplate-ruff.log) passed |
| npm audit | [current](desk-audit-after.json) and [archive](senplate-audit-after.json) have zero reported vulnerabilities |
| Fresh archived setup | [log](senplate-fresh-setup.log); preserves the initial failed-path log locally |
| Preservation and relative links | [machine result](archive-validation.json); frozen snapshots / vendor examples are listed separately |

1,486 maintained relative Markdown links passed, with zero broken targets. The [59 baseline unresolved links](links-before.json) consist of frozen snapshot/vendor references and one generated private credentials link; the latter is now a plain path instruction. The snapshot/vendor link exceptions predate this change; they are point-in-time evidence, not maintained navigation. Hardware, human-acoustic, Linux/Pi and iPhone UI acceptance are not inferred from these software checks. The Vite update does not publish the newer local Omni implementation.

## Git state and next work

The other open PRs (#4, #5, #15, #16) are historical owner branches/drafts. Metadata and dependencies were triaged, not represented as a full independent code review. #4 conflicts; #5 depends on #4; #16 depends on #15 and contains rejected character work. They are preserved for a separate reconciliation of the latest local software.

The staged archive passed Gitleaks (zero findings over 2.93 MB of changed text). Whitespace validation found two trailing blank lines in the newly split historical logs; both were removed and the check rerun. The cleanup is delivered through [PR #18](https://github.com/tantalum666/FYP/pull/18), with remote merge state checked independently. The test PostgreSQL cluster has been stopped. The next software task is to prepare reviewable AliceChan/Omni increments from the preserved local workspace, keeping rejected art out of the main delivery.
