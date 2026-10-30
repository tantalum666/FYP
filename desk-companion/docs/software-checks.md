# Local software checks

Updated 31 October 2026. Validation is local only. No GitHub Actions workflow is present or required; do not add or trigger CI for this project.

From `desk-companion/`, with Python 3.12+, Node 22.12+ and uv:

```sh
bash scripts/check_software.sh --install
```

The script uses committed Python/npm lockfiles, disables npm lifecycle scripts, checks bundled model/image hashes, runs Ruff and the full backend suite, then frontend tests and TypeScript/Vite build. The asset check validates Alice's runtime hash separately from its original-source hash, its phone fallback, and retained development assets. It does not change the selected avatar or download artwork.

Frontend tests also detect case-insensitive TS/TSX implementation-path collisions. The integration renamed the current diagnostic helper to `diagnosticsData.ts`; `diagnostics.tsx` is the rendered panel. This source check complements an actual Mac build.

`--install` synchronizes base/dev dependencies and can remove optional vision/audio packages from that environment. Use a separate checkout or omit installation when preserving an existing device environment. `--offline` requires already-cached dependencies. The optional `browser` extra is locked separately; ordinary checks do not install a Chromium executable or activate the experimental browser.

The child shell clears inherited `DESK_*` settings, uses providers `none`, and creates its own temporary runtime. Tests may explicitly enable synthetic fixture capabilities. The caller's normal runtime and configuration remain unchanged. Only the script-created temporary directory is removed. Test isolation is not a network sandbox; fixture transport restrictions and real-world acceptance are separate.

`--skip-assets` labels a partial checkout and skips only the standalone asset-hash check. It cannot support an avatar-presence or visual-quality claim. No CI, real provider, microphone, mailbox, purchase, device or deployment result follows from local test counts.

The 31 October [integration QA](../../output/qa/2026-10-31-pr5-repair/verification.md) records actual commands, fixture migration, web/phone behavior, complete suite results and publication separately. [Compatibility contract](pr5-integration.md).
