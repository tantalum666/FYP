# A1 control-obstruction correction

12 October 2026 · Group 2 · Cloud implementation and software checks complete; corrected real-browser acceptance pending.

## Finding and minimal change

The parent relayed a real obstruction from isolated Mac acceptance on source `c57b05288db30ed246dd3aefc354214f92f157e1`: A1 intercepted the Web Device page's “Hide private details” checkbox. The subsequent Mac report identifies F1 P2 at the as-launched 1288×681 desktop viewport; keyboard Space succeeds while A1 intercepts the checkbox pointer interaction. Mac retains `38-a1-obstructs-private-toggle.jpg` and `36-settings-private-controls.txt`. Those files have not been transferred to this cloud workspace, so this worker has not inspected their pixels or contents and claims no cloud browser reproduction.

Source inspection explains the reported obstruction: `.a1-companion` is a fixed layer at z-index 12; the silhouette hit button has pointer events enabled. Web modal/edit/review panels already pass `blocked`, but the main Device settings page did not. The original JSX condition evaluates false for that page with all panels closed.

The only production-code change adds `page === "device"` to the existing blocked condition in `frontend/src/App.tsx`. The companion stays mounted and uses its existing hidden-root behavior, which removes its visual/pointer layer and pauses movement. The existing blocking effect cancels unfinished drag/resize gestures and closes transient controls without persisting a new display mode. Leaving settings removes the temporary block; the saved placement, scale, edge mode and motion setting remain in the same component/storage contract. This is a scoped settings-page avoidance correction, not a general collision-avoidance algorithm for every page.

The independent DeviceApp clock/display is unchanged and still displays A1 outside its existing management panels. No click forwarding, global stacking change, new image, segmentation, deformation or new asset was introduced.

## Verification actually completed

- The actual JSX blocked expressions are parsed and evaluated by four new source-level regressions: repeated Web settings enter/leave; every existing Web panel gate; the independent DeviceApp display/panel distinction; existing hidden-root/motion/nonpersisting-block behavior
- The original Device-page expression returns false where true is required; the corrected expression returns true. This is a red/green source-expression check, not browser hit testing
- Ten targeted companion tests pass, including existing continuous scale, persisted preferences, edge states, recall and viewport geometry tests
- Complete `bash scripts/check_software.sh` passes: protected runtime asset hashes, Ruff, 500 backend tests, 79 frontend tests, TypeScript and Vite production build
- Prettier passes for the changed App and added test after formatting the test file
- Existing Starlette/httpx deprecation, npm environment-config and large-bundle warnings remain nonfatal; dependencies and lockfiles were not changed
- Renderer, companion CSS, placement, independent DeviceApp, original A1 PNG and licensed VRM SHA-256 values match the pre-edit snapshot; exact checks are in `verification.json`

All checks used the cloud workspace and existing dependency installation, with dedicated UV/npm caches. No Mac operation, provider call, account permission change, hardware action, commit or push was performed by this worker.

## Browser recheck still required

After publication, the existing isolated Mac acceptance task must load the exact new pushed SHA and directly click the privacy checkbox and save control in the originally failing viewport, without forced clicks or relocating A1 as a workaround. It should also check narrow Web layout, repeated navigation into/out of settings, restored companion position/scale/edge mode on return, modal avoidance, and the independent DeviceApp display. Existing saved-mode hiding should remain hidden when returning. Software checks above do not establish these pointer/visual results or Linux/Pi behavior.

## Reading, ownership and publication scope

This continues the same implementation round and inherits the 186-file full-read ledger at `../2026-10-12-agent-kernel/reading-union-status.json`; it does not claim a new full-library read. Related context was read to EOF: root AGENTS/product/handoff, the latest relevant decision-log sections, page-companion/software-checks contracts, and the changed App/test plus companion renderer/CSS/placement. Device settings and DeviceApp call sites were inspected for the reported interaction.

Owned publication files are only the App visibility change, new `companion-visibility.test.ts`, `docs/page-companion.md`, this report and `verification.json`. Raw logs, intermediate snapshots and source-before copies are local evidence only and excluded. The parent owns root product/decision/handoff/work-log updates and publication. No broad UI or protected asset changes are included.

## Subsequent actual-browser checkpoint

The [sanitized Mac report](../2026-10-12-mac-acceptance-checkpoint/report.md) supersedes the pending pointer-recheck status above: source `91e6ed9` passed actual native checkbox/save interaction at desktop1288×681 and narrow390×844, repeated settings navigation and retained A1 preferences, plus independent DeviceApp1024×600 controls. The earlier sections preserve what the cloud worker knew at implementation time. The image files remain in the isolated Mac QA workspace; the cloud coordinator has read the returned report, not inspected those pixels. Other application acceptance gaps remain explicit in that report.
