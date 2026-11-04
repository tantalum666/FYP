# Offline calendar journey

3 November 2026. This is a local fixture gate for schedule changes. It is not a Google or Outlook connection, and it is not the travel-booking acceptance in the [research index](../../research/personal-agent-research-index.md).

## Responsibility

`desk/offline_calendar/` loads `desk-calendar-fixture-v1` files and writes through the existing stack:

| Concern | Owner |
| --- | --- |
| Deadline and task identity | `TaskService` |
| Location, notes, reminders, recurrence, conflicts | existing calendar event store |
| Conflict / prepare / RSVP advice | `assistant_proposals`, kind `calendar_advice` |
| Owner approval, read-back, cancel | existing proposal decision route |
| Meaningful change | `NoticeInbox` |
| Work pointer | the same task id (`{"kind":"task","id":...}`) |

No second task core, no memory write, and no model call. `google_calendar.py` stays a separate, unconnected read scope. The package is `offline_calendar` so it does not collide with `desk/calendar.py`.

## Fixture and cursor

Fixtures live in `fixtures/offline-calendar/`. The loader checks the name, refuses path traversal, rejects files over 256 KiB, and rejects two different bodies for the same event id and sequence before any write.

One sync reads one batch from the durable `next_event` offset. Revisions inside the batch are applied in sequence order. The same id, sequence, and fingerprint is a duplicate and does not rewrite the task. A lower sequence that arrives after a higher stored sequence is skipped. `history_cursor` advances to the highest applied sequence only when the batch finishes without interrupt, revoke, or disconnect.

`interrupt` commits revisions already read, leaves the cursor unmoved, and returns success false. `revoke` and `disconnect` stop on that control event. Later syncs read nothing and are not success. Replaying the same operation id returns the stored applied response. A second runtime does not see the first runtime's connections.

## One event, one task

One tracked event or series maps to one task and one local calendar event. Later updates use those same ids. The task deadline is the event start. Series recurrence stays on the calendar event; it does not create a second task.

Omitted `notes`, `location`, and `reminder_minutes` are left as stored. The task `next_step` and owner evidence notes are also left in place. Cancel is terminal: a later upsert of that id returns `CALENDAR_ITEM_CANCELLED`.

## Advice and notices

A conflict, prepare-for-meeting, or requested RSVP becomes a `calendar_advice` draft. The summary cites the fixture event id and `observed_at`. `send` and `accept` stay false. Confirming writes a task note that no invite was accepted and no RSVP was sent. Cancelling the draft does not write that note. Full permission does not auto-confirm this kind. A paired display cannot list, sync, or confirm it.

Notices are published only for a new conflict, a deadline inside 24 hours, a cancelled meeting that already had a task, or a draft that needs a decision. An unchanged or far new event stays silent. During quiet hours the same Notifier records the notice as held. `Runtime.tick` publishes that hold when quiet hours end, using the existing notice id so a restart does not drop it or deliver it twice.

## Backup

Portable JSON export includes `offline_calendar_bundle`: connection cursor, event-to-task rows, revisions, conflict pairs, sync attempts, and quiet-hour holds. Preview validates that bundle before the owner applies it. A paired display cannot export, preview, or apply it. Restore inserts a missing connection and does not rewrite a cursor that is already present, so the next sync updates the same task instead of creating another. A backup from before this field still previews as an empty cursor bundle. A whole-file SQLite copy remains a separate private snapshot.

## What this does not claim

No live calendar account, no invite acceptance, no RSVP send, no paid model call, and no travel or mailbox journey. Mailbox, shopping and calendar are now combined in the reviewed integration.

## 4 November review corrections

Revision identity includes the effective upsert/cancel operation. Stored overlap pairs represent active conflicts so a resolved conflict can notify again when it reappears. Native local-calendar counterparts are valid backup references; deleted external dedup markers are omitted from export. Repeated cancellation revisions update bookkeeping without another notice.

A partial later batch may retain its prior completed cursor while newer effects are already committed. Restore validates this state and continues the same task. Cached sync receipts are fully validated, including connection/item identity and mandatory sent=false/accepted=false, before import can replay them. Revoke is independent of the batch lock; the next item rechecks authority/state. [Combined QA](../../output/qa/2026-11-04-grok-journey-review/verification.md).
