# Reproducible software checks

Run from `desk-companion/` with Python 3.12+, Node 22.12+ and uv:

```sh
bash scripts/check_software.sh --install
```

The script installs the exact committed Python/npm lockfiles, disables npm lifecycle scripts, verifies the bundled VRM and A1 PNG against their provenance hashes, runs Ruff and the complete backend test directory, then runs frontend tests and TypeScript/Vite production build. Frontend `npm test` also recursively checks all implementation `.ts`/`.tsx` files under `src` for case-insensitive extensionless module-key collisions and case-only directory aliases; `.d.ts` declaration companions are excluded. This source guard catches cross-platform naming ambiguity on Linux, but does not replace an actual Mac build. A failed stage stops the remaining stages. Dependency installation needs package-registry access unless caches are already complete.

`--install` performs an exact base/dev dependency sync and may remove optional vision/audio packages from that virtual environment. Use a dedicated software-check checkout, or omit installation when retaining an existing hardware environment. For read-only home directories, set `UV_CACHE_DIR` and npm's `--cache`/`npm_config_cache` to an authorized writable cache location.

For an existing installation, omit `--install`. To require cached dependency installation:

```sh
bash scripts/check_software.sh --install --offline
```

`--offline` disables uv/npm network access; it does not sandbox arbitrary test code or prove that every future test is network-free. The test suite currently uses synthetic fixtures and mocked providers. The script clears inherited `DESK_*` settings in its child shell, disables live text/voice providers, background AI and computer execution, and creates an isolated temporary runtime. Tests may explicitly enable fixture-only capabilities. The caller's environment and normal runtime are left unchanged; only the script-created temporary directory is removed on exit.

## Partial source materializations

`--skip-assets` is an explicit, visibly labeled exception for a partial checkout. It skips only the extra bundled-image hash stage; existing frontend VRM tests still require their model. It must not be used to claim that all presentation assets are present or visually correct. Do not replace missing A1 artwork with a placeholder. Full repository CI does not use this exception.

## GitHub Actions

The repository workflow `.github/workflows/desk-companion-ci.yml` runs this same command on relevant pull requests, main/codex branch pushes, and manual dispatch. It uses Ubuntu 24.04, Node 24.19.0, Python 3.12.14 and uv 0.12.23. Checkout is scoped to `desk-companion` and the workflow directory, including the actual runtime images/models. Official actions are pinned to verified release commit SHAs; dependency caches are keyed by lockfiles. The workflow grants only `contents: read`, does not persist checkout credentials, and contains no provider secrets, deployment, merge, device or purchase steps.

The action pins were verified on 2026-10-12 against [checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1), [setup-node v7.1.0](https://github.com/actions/setup-node/releases/tag/v7.1.0), and [setup-uv v10.2.0](https://github.com/astral-sh/setup-uv/releases/tag/v10.2.0). Tool versions are fixed for reproducibility; upgrading them should include a new local/CI check.

Local success is separate from a completed remote Actions run. Before publication there is no claim that GitHub has executed this workflow. Browser interaction, real provider/audio quality, iPhone/Pi performance, camera calibration and hardware output require separate scoped evidence.
