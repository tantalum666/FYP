# Group 2 A1/B1 character generation verification

10 October 2026, Asia/Hong_Kong. The user explicitly requested character-image generation after retaining A/B and the wardrobe briefs. This continues the same art workflow; it is not an application/model replacement.

## Reading and generation route

[reading-record.json](reading-record.json) retains the art-task full-body read (128 files / 12,096 lines / 48 chunks), the wardrobe supplement and this task's 130-file inventory / affected-file reading. Truncated skill / avatar outputs were re-emitted in full for the missing ranges. Newly authored concept and prompt files were checked as deliverables, not counted as a new library read.

The system ImageGen skill and Creative Production produce / board-runtime instructions were read. Produce explicitly delegates 2+ uncached native images, so exactly two narrow workers generated A1/B1 with the supplied prompts. Each used built-in ImageGen once, no model override, no CLI/API fallback, no input/reference image and no pixel editing. Each native tool completion was returned through generatedImage by its worker. Both results were consumed and interrupt_agent confirmed completed status immediately. This runtime has no close/destroy-worker API; no destruction is claimed.

Creative Production's rich board tool is exposed only as a nested function here, while the skill explicitly forbids functions.exec forwarding for that UI resource. No board was mounted or remounted; original images are delivered directly. This limitation did not block the user's image request or require approval.

## Asset verification and actual appearance

The coordinator viewed both native images, verified nonempty PNG signatures and 1024 × 1536 dimensions, then copied bytes unchanged into the workspace.

- A1: 1,819,525 bytes, SHA-256 `5ab0ba141b9c6f9dded5b9b180473a1fb88877205534febdc479f85cf908e2de`.
- B1: 1,798,005 bytes, SHA-256 `d4769b281ff138ac3de782dad6099459cd7690959c84ea90499476cc04c0293a`.
- [Original PNGs, exact prompt set and manifest](../../../design/desk-companion/characters/2026-10-10-concepts/README.md).

Both show a single adult female full body with visible hair, hands and shoes, plain warm-grey studio background and relaxed comparable poses. A1 shows silver hair / open-ellipse clip, ivory jacket, graphite high neck, blue-grey wrap skirt, continuous sheer hosiery and ankle boots. B1 shows dark shoulder-length hair, grey-teal blazer, ivory blouse, tailored shorts, continuous hosiery and boots. No labels, weapons, additional figures or background scene appear.

Actual differences from the brief are retained: rendering is relatively semi-realistic stylized 3D, rather than strongly cel-shaded anime; margins are tighter than requested; A1 heels are higher; B1 shorts are shorter and its small warm accent is not obvious. No exact physical age, garment dimensions or 3D topology is measured from the images. Valid candidates are preserved without regeneration. No original character has yet been selected by the user.

These are PNG appearance concepts. No rig, mesh, texture-source project, turnaround, expression sheet, photometric material or VRM was created. The existing licensed runtime sample remains unchanged. A2/B2 are still written candidates.

## Documentation and preservation

Product, root README, avatar contract, research / wardrobe current status, both reference-board status labels, decision log, handoff and work log route to the generated concepts. Old research and its original evidence remain preserved with their dates.

[validation.json](validation.json) records local links, native/delivered byte identity, dimensions, prompt/manifest references, 107 protected school / identity / retired-code files, unchanged frontend/backend/native application paths and the pinned model SHA. No application suite or school-document rendering was rerun because those sources/documents were not changed. The main application's events and preferences were not operated on. Existing static reference-board copy changed only its current status and link; no new app interface or rich board is claimed.

Git delivery uses `codex/full-body-3d-avatar` and the existing open [PR #4](https://github.com/tantalum666/FYP/pull/4). Staged scan and remote ref / PR head readback are recorded at closeout. No main merge, school submission, paid voice call, hardware action, purchase or external contact occurred.

Completed checks: 602 local links valid, both PNG signatures/dimensions/hashes and native/workspace byte identity verified, all 107 protected files and application/model unchanged; staged Gitleaks scan returned zero findings.

Actual delivery: concept commit `3cd7976b981c2a81032a0c550f7f470b667766bd` was pushed and independently read back by remote ref and PR metadata. Main remains `ccfac48ce8c68e6f9c8796911bbe5f35728d7807`; PR #4 is open/unmerged and its body now reflects generated concepts. A final documentation-only closeout commit follows the same push/readback path.
