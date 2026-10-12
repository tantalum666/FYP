# CI and cloud preparation verification

Date: 2026-10-12. Source baseline: `50e174f50a4130b3c666f836f666f6aa4cde4b32`, tree `5a8c782d80d651300ae3a13e21c4fd5af8c241a2`. This record covers preparation and check tooling, not the later integrated agent features.

## Verified baseline

- Pinned connector materialization with Git blob verification; 421 remote files materialized before implementation. Full remote tree and 6,100 omissions were recorded separately. Historical missing binaries are not deletion requests.
- All 186 authored Markdown files were actually read by the coordinated readers: 148 non-QA and 38 authored QA. The union ledger validates full line-range/EOF coverage and unchanged source hashes. Four before-state evidence snapshots and one vendored README were explicitly excluded.
- Desk Companion backend: 149 tests passed; Ruff passed. One upstream Starlette/httpx deprecation warning remains.
- Frontend: all 28 tests passed after recovering the unchanged public VRM from its manifest-pinned official upstream and verifying both SHA256 and repository Git blob. The initial missing-VRM failure is retained in the baseline log.
- TypeScript and Vite build passed, including a rerun after VRM recovery; the existing large-chunk warning remains.
- The private A1 PNG was not recovered through the available connector/Library routes. Its source and provenance were not edited; no placeholder was substituted. Existing visual QA is not reasserted as fresh cloud evidence.

## Added verification tooling

- `.github/workflows/desk-companion-ci.yml`: relevant PR/push/manual triggers, Ubuntu 24.04, 15-minute timeout, `contents: read`, no stored checkout credentials or secret references. The three action versions are pinned to release SHAs verified through the official repositories; `ci-action-pins.json` records them.
- `desk-companion/scripts/check_software.sh`: frozen optional installation, offline cache mode, inherited application configuration cleared in a child shell, disabled providers/background execution, isolated temporary runtime, asset hashes, Ruff, backend/frontend tests, TypeScript/build and fail-fast behavior.
- `desk-companion/scripts/check_assets.py`: checks both runtime asset manifests and binary hashes without downloads or edits. Missing A1 is reported as an error; `--skip-assets` is explicitly labeled for partial checkouts and is absent from CI.
- Seven helper tests passed, covering valid/corrupt/missing assets, path rejection, invalid manifest preservation, frozen/offline flags, disabled inherited provider configuration, failure propagation and temporary-directory cleanup.
- `bash -n` passed. Workflow YAML parsed; event/permission checks and all three full-length action pins passed. No actionlint binary was installed and no remote Actions run has occurred yet.
- A separate dependency-only directory completed `uv sync --frozen --offline` (35 packages) and `npm ci --offline --ignore-scripts --no-audit --no-fund` (160 packages) using the now-populated caches. No project lockfile changed.

An initial helper invocation without the cloud's writable `UV_CACHE_DIR` failed because the home cache is read-only. It was corrected by selecting the existing authorized cache, then the asset check and seven helper tests were rerun successfully. The asset check correctly exits 1 for the missing PNG.

## Browser limits verified

The cloud browser is available, but its loopback cannot reach a server in the per-command shell network namespace. A supported escalation attempt failed with a bubblewrap mount error; protected paths were not inspected. A same-command Playwright attempt found installed Chromium 154 but failed at process-singleton socket creation with `Operation not permitted`, with Chromium sandbox enabled. No sandbox disabling, security change or alternate credential route was used. All trial server processes were stopped.

The GitHub browser session is logged out and the private image URL displayed a sign-in/404 page. Library search found no matching current PNG. These are the remaining reasons that a fresh browser screenshot is unavailable from this cloud preparation stage. API/unit checks remain usable; target hardware, live AI, audio, permissions and school submission were not exercised.

## Handoff

Use the existing pinned remote tree as `base_tree` and overlay only intended changes when publishing from this partial materialization. Refresh the remote head first. The parent owns combined documentation, publication and final integrated verification; no source code or workflow was published by this worker.
