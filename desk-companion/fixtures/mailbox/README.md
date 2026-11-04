# Offline mailbox fixtures

These files are the only mailbox source for the offline journey. They are not a Gmail or Outlook account, and nothing in this directory is a credential.

Format `desk-mailbox-fixture-v1`:

- `account_id` and `address` name the fictional mailbox. One offline connection per account.
- `batches` are incremental sync units. One `POST /api/mailbox/connections/{id}/sync` reads one batch, then stops.
- A `message` event is one mail. The same `id` with the same content is a duplicate and must not create a second task. The same `id` with different content is rejected before any row is written.
- Messages inside a batch are applied in `history_id` order, even when the file lists them out of order. The higher history id wins when both set the same task field.
- Omitted task fields (`deadline_local`, `timezone`, `waiting_for`, `next_step`, `await_reply`) do not change the tracked task. A present field updates that field on the same thread's task.
- `interrupt` stops the batch after the messages already read. The sync result is not success, the history cursor does not advance, and the attempt row stays. The next sync reads what follows the interrupt.
- `revoke` and `disconnect` stop further reads immediately. Messages after that event are not applied. Another sync does not read them.
- `observed_at` is the source observation time cited by advice. The desk clock does not replace it.
- `needs_decision` or `await_reply: true` prepares one owner review draft. The draft's `send` field is false. Confirming it records a task note and does not send mail.

File names are lowercase ASCII so they stay distinct on macOS. The loader accepts only `[a-z0-9-]` fixture names under this directory.
