# Personal context frontend verification · Group 2

Recorded: 12 October 2026 (UTC). Source changes frozen for the parent's first integration checkpoint. This is frontend implementation and local automated verification, not evidence of live provider use, user-account connection, hardware testing, or completed browser interaction.

## Implemented

- Owner-only saved conversation list, explicit temporary-chat mode, create/rename/delete, selecting and reopening existing history, and a draft-discard confirmation before switching threads.
- Explicit local text retention permission, separately controlled AI use of chat history, approved memory, and saved business context. The privacy dialog identifies the configured provider and exact safe destination; saving a selected AI option approves only the shown destinations. No provider is called by toggling a checkbox.
- Inspect/add/correct/forget individual memories with category, provenance and timestamp; reviewed assistant memory proposals use the existing deterministic decision endpoint. Stored text is data, not action authority or task-completion evidence.
- Reply mode uses the recorded result, not provider configuration as a proxy. Saved proposal references show their current state without claiming that approval proves execution.
- Sensitive request recovery uses one immutable operation ID in component-lifetime memory, with no sessionStorage/localStorage body persistence. Unknown outcomes retain the exact request for explicit retry. Definite conflicts and the backend's 410 nonretained-reply receipt do not automatically rerun a request.
- Saved history, memories, transcripts, replies and proposal text are gated by current privacy/identity state. A response fence rejects late results across owner-to-paired downgrade, reauthentication and hide/show cycles. Read generations reject superseded responses. Successful mutations force fresh reads rather than accepting an older in-flight snapshot.
- Privacy concealment closes private editors without saving their unsaved content. The request-box draft remains in memory during temporary concealment; identity changes clear it. Inputs are never copied automatically from voice into history or memory.
- Native dialog semantics, focus restoration, busy guards and unsaved-edit protection use the existing Modal/DraftGuard infrastructure. Rename and settings editors freeze their original versions, so another window's changes cannot be silently overwritten.
- The routines worker's panel is mounted inside AssistantPanel with the same owner/privacy visibility override. A1 art and animation files are unchanged. DeviceApp and task-linked assistant call sites only pass their display-mode privacy flag; the independent device layout remains unchanged.

## Automated checks

- `node --experimental-strip-types --test tests/personal-context.test.ts`: 11 passing focused tests; see `personal-focused-tests.log`.
- `npm test`: 50 passing frontend tests at the recorded checkpoint, including other workers' job and routine coverage; see `frontend-tests.log`.
- `npm run typecheck`: passed; see `frontend-typecheck.log`.
- `npm run build`: passed; see `frontend-build.log`. Vite still reports chunks larger than 500 kB, including the pre-existing optional VRM scene. No target-device performance claim is made.

The focused tests exercise immutable same-ID recovery without touching browser storage, rejection of changed/parallel requests, definitive versus uncertain errors, clearing recovery, owner/private/offline/stale gating, retention versus provider-consent independence, draft-switch guards, actual reply-mode labels, the nonpersistent write boundary, and privacy/session response epochs.

## Independent review fixes

The independent reviewer identified two privacy races and a stale-rename problem. Temporary replies/transcripts now receive the same privacy gate as saved history; late owner results cannot enter a paired/display session or a later visibility epoch. The title editor now captures original ID/version with its initial title. A further mutation-completion navigation issue was fixed so successful thread create/delete can update selection without being blocked by the write's own busy state, while unsent drafts still require confirmation.

## Browser verification limit

Installed Chromium failed before opening any page: its process-singleton socket call returned `Operation not permitted`. One reviewed escalated retry failed identically. No screenshot or UI-click pass is claimed. The isolated synthetic-data loopback server was stopped through its owned session (exit 130). The parent has arranged a separate supported Mac validation task against the published code checkpoint.

## Evidence and remaining scope

`source-hashes.json` identifies this frontend source snapshot; hashes identify bytes, not reading or runtime behavior. The parent owns the integrated commit, root documentation and final aggregate tests. Real model/voice quality, provider charges, OS execution, physical safety, Pi/iPhone behavior and end-to-end browser receipts remain separate acceptance gates.
