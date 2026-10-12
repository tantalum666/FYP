# Browser adapter source checkpoint

Date: 2026-10-12. Scope: FYP-owned fixed public-source → reviewed StackEdit Markdown workflow, default off. Publication and actual Mac application acceptance are separate gates owned by the coordinator.

## Checked here

- 37 focused backend tests passed on the final source snapshot; [raw log](browser-focused-tests.log)
- Ruff passed for the four browser modules, tests and acceptance runner; [log](browser-ruff.log)
- Python compile check and acceptance runner `--help` passed; [CLI](acceptance-cli-help.txt)
- `UV_CACHE_DIR=/tmp/fyp-browser-uv-cache uv lock --check --offline` resolved 57 packages and exited 0
- Optional dependency: Playwright 1.62.0; lock includes greenlet and pyee. This checkpoint did not install the optional package or a browser
- Source-derived selectors have pinned public provenance; [manifest](selector-provenance.json). No raw vendor source copied into the repository

Tests explicitly use a fake browser for policy/state faults, plus trusted local Python subprocesses for environment/protocol and bounded process cleanup. HTTP tests exercise the real owner/privacy routes with that fake executor. **No Chromium process, live StackEdit UI, paid model, user browser profile, LCU or physical device was exercised by these tests.**

## Reviewed failure boundaries

The independent review identified and prompted fixes for retained child pipes after leader exit; durable privacy revision invalidation; receipt bytes incorrectly overriding process-cleanup uncertainty; restart fencing of effect and observation claims; recording normal observation cleanup separately from privacy authorization; and cancellation remaining available at the work-history capacity. The final tests cover each boundary.

A verified file plus unknown process cleanup remains unknown and blocks new browser work. Read-only reconciliation/download can retain the actual byte proof, but cannot prove process cleanup or authorize a retry. At capacity, cancellation retains at most one receipt per existing job; repeats do not grow history.

## Remaining acceptance

Run the [actual adapter script](../../../desk-companion/scripts/check_browser_workflow.py) on the authorized isolated Mac setup using an already provisioned official Chromium executable. Follow the [operator contract](../../../desk-companion/docs/browser-workflow.md). Retain the exact source hash, review, actual application export, browser version and independent readback evidence. A selector or sandbox failure is a failure, not permission to replace the export with a generated file or disable the sandbox.

Request routing is defense in depth only; no hard network-confinement claim is made. Admission is limited to the fixed public/synthetic scope. Broader desktop/autonomous cross-application behavior, private data, credentials, authenticated apps and automatic cleanup rearm remain outside this checkpoint.

Changed owned files and hashes are in [delivery-manifest.json](delivery-manifest.json). The coordinator owns shared runtime/app wiring, aggregate tests, global handoff/work log updates and any remote publication. The inherited full-reading gate and this follow-up's exact read coverage are in [implementation-reading-supplement.json](implementation-reading-supplement.json) and [final-reading-supplement.json](final-reading-supplement.json).
