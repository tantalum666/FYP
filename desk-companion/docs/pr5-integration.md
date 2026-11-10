# PR5 integration with the current application

31 October 2026. The owner explicitly requested repairing and merging [PR5](https://github.com/tantalum666/FYP/pull/5). The integration starts from main `18d205607d5c2eb9f3f23143bbf8eacbc29b7077` and preserves original PR5 head `11dc2b84cebe6e8250b28ca4442fc91f0dfec676` in Git ancestry. [Repair and validation record](../../output/qa/2026-10-31-pr5-repair/verification.md).

## Composition

The current `Runtime`, Alice presentation, Omni conversation, `TaskService`, `JobService`, `PermissionService`, current application executor and owner fact store remain authoritative. Work is a retained orchestration record referencing existing task/calendar IDs and exact child effects; it does not replace a task or automatically complete one.

Integrated PR5 capabilities:

- Immutable selected sources, verified Markdown/CSV artifacts, metadata search and capacity reporting.
- Bounded, restart-aware Work with persisted decisions, questions, explicit review links, cancellation, steering, source coverage and independent outcome checks. Deterministic compilation remains distinct from model interpretation.
- Selected-task change watches, coalesced reviews, bounded retention maintenance and local scheduled briefings/check-ins.
- Explicitly retained text conversations and provider-bound context selection for those conversations and Work.
- Server-observed voice snapshots that can be reviewed and handed to the Work composer. Speech, interruption and provider tool output cannot approve or start Work by themselves.
- Default-off public-page acquisition, fixed public browser workflow and finite operator-configured public/synthetic MCP grants. These are not Gmail/Outlook, shopping or payment connections.

The obsolete 2D A1 interface and demo-record application adapter are superseded. Their original sources/tests remain at the pinned PR5 commit. Current Calc/Writer/Chromium operations keep their existing executor and single computer-job queue. A fake record API is not added to the ordinary action catalog or portable backup format. The useful hidden-job and approved-intent regressions were ported to the current executor.

## Memory compatibility

`owner_memories` is the only active fact store. `PersonalMemoryAdapter` projects current facts into retained-context fields without mirroring their text. It sees all active facts, including those outside the ordinary 40-fact prompt window. Corrections keep their existing revision history; expiry, supersession and deletion remove facts from subsequent retained projections. Aliases and owner settings remain in their current tables.

The canonical fact limit remains 200 active facts. The text bound is now 1,000 characters to preserve original PR5 facts without truncation. New UI entry points reuse the current memory editor, including corrections, expiry and aliases. Historical PR5 category labels are preserved as import attribution; categories do not become instructions or permissions.

Canonical fact changes invalidate retained-context epochs in the same SQLite transaction. Selected memory bindings also recheck the current text/version; no projection cache can hide a correction or expiry. Deletion scrubs the current body, prior revision bodies and relevant local cached text. Retired memory-operation requests keep only their digest, so original-key recovery cannot recreate the forgotten fact. Explicitly retained conversation transcripts remain separately inspectable until the owner deletes the conversation; this is not forensic erasure of SQLite/WAL/backups or remote provider copies.

Already-linked Work proposals remain classified as Work-origin even if privacy cleanup redacts their prose. The independent confirmation guard checks current context before accepting the saved effect. Unlinked crash recovery still requires a matching canonical intent, so unrelated/colliding drafts are not adopted.

## Store migration

Fresh stores initialize schema 3. Existing schema 1 and 2 stores are refused by ordinary startup until their explicit offline migrations are completed. Unsupported versions are refused before bootstrap. Runtime refuses a remaining legacy `personal_memories` table instead of starting with invisible or divergent facts.

After stopping the old runtime and independently verifying a coherent protected backup, use the applicable commands from `desk-companion/`:

```sh
python scripts/migrate_watch_retention.py --runtime /absolute/runtime --allow-watch-retention-migration
python scripts/migrate_public_capture.py --runtime /absolute/runtime --allow-public-capture-migration
```

The first advances 1 → 2, the second 2 → 3. Each is separately acknowledged and idempotently verifies its supported current target. The flags acknowledge operator checks; the scripts do not stop processes or create/verify a backup.

Only an original PR5 store with `personal_memories` additionally needs:

```sh
python scripts/migrate_personal_memory.py --runtime /absolute/runtime --stopped-and-backed-up
```

That conversion retains IDs, versions, dates, source attribution and forgotten state; conflicting IDs or excessive active capacity abort atomically. It never overwrites a different current fact. Old context bindings become invalid and require fresh selection. Current main stores already using `owner_memories` need no fact conversion.

The macOS guard pins directory device/inode/mode/owner, and database device/inode/mode/owner/single-link identity. Directory link count is deliberately excluded because legitimate SQLite WAL sidecars change it. Database hard links, replaced paths and non-private migration inputs remain rejected. This is a cooperating-process migration boundary, not an OS guarantee against hostile concurrent path replacement.

The integration's actual fixture test used the unmodified main baseline to create schema 1. Both migrations preserved all 45 original tables row-for-row. Corrected fact text/version, history, expiry, aliases, full-permission policy and an unapproved job remained available through the new runtime. No actual user database was migrated.

## Shared UI and conversation boundaries

Web, phone and the web-based native app expose Work and watches from the existing Tasks page. Phone keeps its Alice home and Plan/More navigation. Large Work detail uses an appropriate desktop width; phone uses one column. Action reviews reuse the current `ProposalActionCard` and original operation IDs. Scope, retention and a typed review are separate from effect approval.

Normal Alice/Omni chat keeps its login/task-scoped volatile conversation IDs and existing durable business-receipt recovery. Optional retained chat uses `/api/assistant/retained-messages` and its own explicitly selected saved-thread ID. A saved-thread ID is never interpreted as a live Omni replay ID. Its settings are labelled **Saved-work privacy** and apply to retained conversations and Work, not to normal Alice's existing context settings. All business effects still use the current service/approval boundaries.

Consuming a reviewed voice-goal prefill must not unmount the Work composer. The handoff stays open after the prefill is acknowledged; identity/privacy changes clear it. Tests execute the actual hook transition. Voice input and freeze references remain volatile until explicit Work admission; no microphone or paid session was used for this integration.

## Transport, maintenance and limits

Text adapters retain the current provider interface and gain bounded raw JSON reading plus a pre-dispatch authorization checkpoint. JSON depth is explicitly capped at 64; it no longer depends on Python raising `RecursionError`. Provider endpoint validation, disabled ambient proxies and redirect denial protect credential-bearing transport. Current Qwen Omni's configured endpoint/model remains supported. These checks do not prove provider availability or choose the final model.

Background Work/watch/browser/connector services use the existing application lifespan. Shutdown attempts every service cleanup even when one fails, then cancels workers. No scheduler creates an external connector grant or paid-model budget. Computer jobs verify that the persisted request still matches the approved hash immediately before dispatch. Hidden job APIs omit review content and block new approvals while leaving cancellation available.

Only local verification is used; no GitHub Actions workflow is added or triggered. Package locks retain current dependencies and add the optional browser extra. No browser executable was installed, and no real mailbox, public capture, third-party browser write, paid model, native Simulator or hardware/Pi acceptance was performed. The existing private runtime/key/worktrees are preserved.

SQLite backup and portable calendar/memory/job exports are different features. Work's immutable source/artifact files are not included in the older portable business-data export. An operator backup of retained Work must preserve the stopped runtime's database and its source/artifact directories coherently. This integration does not add automatic Work/source/artifact deletion or claim unlimited storage.

The unified November4 software now combines [cross-application Work](application-work.md) with the reviewed offline [mailbox](mailbox-journey.md), [shopping](shopping-fixtures.md) and [calendar](offline-calendar-journey.md) journeys. Ordinary text, held-out source layouts, and a reviewed voice snapshot can admit an explicit goal change into existing Work, with interruption and unknown-result recovery, offline only: [conversation goal changes](conversation-work.md). The voice review screen can update one current run with the reviewed snapshot, and starts new work when nothing current is selected. After the change, the same conversation shows one verified offline result, a later status ask reads the same file again, and an explicit continue ask advances that run once offline. A later ask takes one more step only while the run is still open. Real authorized mailbox and consumer-account journeys remain separate acceptance gates; code integration does not deliver sending, purchases or flight booking. [Research and current gaps](../../research/personal-agent-research-index.md).
