# Offline authorized-mailbox journey

3 November 2026. This is the offline slice of the first real acceptance in the [research index](../../research/personal-agent-research-index.md): mail, then the same task, then sourced advice. It does not connect Gmail or Outlook, does not send mail, and does not call a model.

## Responsibility

`mailbox_fixture.py` loads and validates local JSON before any row is written. `mailbox.py` owns the connection, durable read offset, history cursor, and thread-to-task link. It calls `TaskService`, `AssistantService.propose` / the existing proposal decision route, and `Notifier`. It does not create a second task, job, or memory store. The tracked Work item is the existing task id, which the current task list and Work scope already read.

New tables live in the same SQLite store and use its `BEGIN IMMEDIATE` transactions. Every mailbox route and service method rechecks the owner session. A paired display cannot list connections, sync, or confirm a mailbox draft.

## Fixture contract

Files live in [fixtures/mailbox](../fixtures/mailbox/README.md). One sync reads one batch.

- The same message id with the same content is skipped. A second task is not created.
- Messages in a batch are applied in `history_id` order, so an older id that arrives later still lands before a newer one.
- Omitted deadline, timezone, waiting reason, next step, and reply flag do not overwrite the saved task. Present fields update that same task.
- `interrupt` commits messages already read, leaves the attempt row in place, does not advance the history cursor, and returns success false. The next sync continues.
- `revoke` and `disconnect` stop before any later message is read. The result is not success. A later sync reads nothing.
- Advice cites the fixture message id and `observed_at`. `send` is false. Confirm uses the existing proposal decision, records a task note, and does not send. Cancel leaves that acceptance note unwritten.

Notices go through `NoticeInbox`. A duplicate or a message that changes no tracked field does not add a notice. A new or changed thread, a deadline inside 24 hours, or a draft that needs a decision does. Quiet hours suppress delivery and do not retry that notice after the message is already ingested.

## Not in this slice

Portable JSON backup does not export mailbox cursors. There is no mailbox import path. A full runtime SQLite copy would include the tables; this slice does not add one. Real account authorization, live sync, and sending remain unauthorized. A change seen only during quiet hours is not delivered again later.
