# Group 2 · Current software entry

29 October 2026. Resume the **shared assistant permissions and task/file/phone continuity** checkpoint; the owner explicitly required the UX correction on web and App, not just mobile.

Use `/Users/tantalum/.codex/worktrees/grok-reviewed-fixes/FYP`, branch `codex/assistant-permissions-20261029`. Base is open [PR64](https://github.com/tantalum666/FYP/pull/64) head `b02d92b132a83dccb4674abb25f33d7613fbcd28`; main remains the separate local-validation-only baseline. Publication receipt is being finalized in the current QA; do not infer merge/deployment.

Read [AGENTS](AGENTS.md), [product](product.md), concise [handoff](handoff.md) and latest relevant [decisions](decision-log.md), then [permissions](desk-companion/docs/assistant-permissions.md) / [maintenance](desk-companion/docs/software-maintenance.md). Inspect Git status before changing branches or overwriting anything.

Current [QA](output/qa/2026-10-29-assistant-permissions/verification.md):489 backend/89 frontend, lint/types/build/format, actual web/phone inline approval/Full access/recovery, independent file readback, current Simulator build and real frame. Native taps/soft keyboard remain unaccepted; browser checks do not close that gate. Ask first is still selected in the disposable preview.

Grok20–59 and#60 already merged via [PR61](https://github.com/tantalum666/FYP/pull/61). PR64 older-memory changes are the base for this increment, still open/unmerged. Original integration [receipts](output/qa/2026-10-28-grok-review-merge/publication.json), dirty worktrees, school originals and private runtimes remain preserved.

Keep full-screen Alice, intentional phone navigation and common business services. Local validation only, **no CI**. Qwen is a tested baseline rather than the final/only model; paid budgets stay closed. Pi/Luwu stay paused. Source publication, native installation, real-device acceptance and school submission remain distinct.

The one next step is in [handoff](handoff.md): mixed-action partial-success/revocation/restart acceptance using offline/scripted providers and existing receipts. Current ports, process ownership and preserved old data are also recorded there; recheck before reuse.
