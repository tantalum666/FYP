# Resident page companion

> Current13November2026: immersive Web/phone/device composition is described in [Alice home](alice-home.md). The renderer now includes [natural Alice motion](avatar.md), superseding the historical nod-only note. Existing pause, offscreen/visibility and disposal ownership remain; the old authored Walk/Stretch asset library is not restored. The dated placement/mobile-planning paragraphs below are historical.

## 2026-10-27 desktop web placement

The desktop web layout now reserves sidebar space for the current character. `desk.companion.layout.v1.web` selects `sidebar` (default) or `floating`; the existing position/scale/motion preference is retained, not overwritten by the fitted position. Companion controls offer Float over workspace and Return to sidebar. Floating mode keeps the existing drag/scale/edge behaviors below. Compact web still falls back to the existing floating behavior; the mobile immersive plan is a separate next step.

Wide non-modal assistant panels keep the sidebar character visible. Shared Modal instances announce whether a blocking modal is open; editing/review dialogs hide and pause the resident, including nested task editors, and closing restores it. One canvas is retained across placement and assistant breakpoint changes. [Implementation and limits](../../planning/2026-10-27/web-ui-implementation.md), QA (local historical material: `output/qa/2026-10-27-web-ui-implementation/verification.md`; not included in this checkpoint).


2026-10-27 mobile planning note: the owner requires Alice to remain visible and now finds the small card/dock treatment visually awkward, asking about a full-screen character experience. The [current proposal](../../planning/2026-10-27/mobile-ux-ui-plan.md) uses an immersive Alice home, merges Today/Assistant presentation, and opens Plan/More as needed. It supersedes the four-tab/compact-dock proposal. Character/persona consistency is informed by [community reference research](../../research/2026-10-27-mobile-companion/deepseek-fish-reference.md), not a decision to adopt a different model. The immersive mobile layout is not implemented; the desktop web changes below are now implemented. The original Alice assets/licence, one-renderer lifecycle and real tool-result boundaries remain. Current design QA (local historical material: `output/qa/2026-10-27-mobile-immersive/verification.md`; not included in this checkpoint).

<!-- FYP-CONTEXT-20261027 -->
> 2026-10-27 核对：**现行规范／入口**。已按本轮保存状态核对；最新软件、GitHub main 和 Pi 部署分开，Pi 暂停、旧 API 预算关闭。 [新聊天入口](../../START_HERE_NEXT_CHAT.md)。
<!-- /FYP-CONTEXT-20261027 -->

Updated 22 October 2026 · Group 2. **AliceChan is the owner-selected initial companion.** [Creator source and licence](../../design/desk-companion/characters/2026-10-22-alice/README.md) retain original face, hair, outfit, native MToon, rig and expressions. The compatibility copy changes only three skin-root hints. A1 illustration/nine outfits and rejected studies remain preserved; the illustration remains an optional fallback.

The [character page](avatar.md) applies model/palette/uniform head scale to same-origin tabs. The new `desk.companion.complete-vrm.v2` defaults to Alice/original/100%; the old v1 study preference remains stored but is not reused to recolor or reshape Alice. Invalid/unavailable storage falls back to Alice. Current v2 choices synchronize between open Web/Device tabs; this is browser presentation storage, not account backup or cross-device synchronization. Older local preview bytes remain in IndexedDB behind “Open saved local preview”.

Authenticated Web and DeviceApp mount the same layer. Login/public share/standalone study do not mount a second resident canvas. When the device preference already shows the full companion scene, the floating layer is omitted so only one canvas exists. Editing/review/management panels hide the floating layer and stop the active character render loop, including the full device scene, protecting the active controls.

| Input | Result |
|---|---|
| Drag (floating mode) | Move freely; release near left/right/bottom to dock |
| Edge distance36–72px /12–36px /≤12px | Half body /head /hidden; hidden leaves a reachable companion recall tab |
| Wheel, corner drag, or scale slider (floating mode) | Continuous uniform resize,50–200%, bounded to viewport |
| Click | Brief native-rig nod; the2D fallback retains its restrained whole-image response |
| Right-click/ellipsis | Display modes, actions, pause, reset,2D/3D choice and study link |
| Double-click/Shift+Enter | Open the existing assistant |
| Arrows /Escape | Move (Shift increases step) /cancel unfinished drag or resize |

The3D renderer uses a complete VRM mesh, native skeleton/expressions and spring bones. Pointer attention and a brief nod use normalized humanoid bones; the old Walk/Stretch library is absent from current controls. Half/head states clip the rendered viewport. The fallback remains one unchanged whole PNG. No new face/hair parts are cut or generated.

Versioned localStorage position/scale/dock/motion keys remain `desk.a1.page-companion.v1.web` and `.device`; the new render choice is `desk.a1.3d.v2.<surface>`. Only presentation preferences are stored, never credentials, calendars or conversations. Legacy sizes migrate; invalid/unavailable storage falls back. Existing scale/docking synchronizes between same-origin tabs. The 2D/3D choice persists separately per surface; already-open tabs pick it up on reload, without live choice synchronization.

The default in this review branch is3D; WebGL/load failure retains the intact illustration and an explanatory control. Original primary checkout/runtime files are preserved. The [complete-model viewer](avatar.md) has orbit/zoom, native expressions, restoration and limited local appearance application; large-action previews are historical. V4 was a continuity reference; the nine saved outfits remain unselected.

QA (local historical material: `output/qa/2026-10-17-assistant-simplify-avatar/verification.md`; not included in this checkpoint) separates actual browser, synthetic-media and asset checks from unmeasured Pi/Linux/physical results. Visible motion is not evidence of AI reasoning, tool success, health benefit or real hardware feedback.
