import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

register(new URL("./fixtures/render-tsx-loader.mjs", import.meta.url));
const { MailReplyReminderCard, LOCAL_REPLY_DRAFT, reminderIsLocal } = await import(
  "../src/workspace/MailReplyReminder.tsx"
);

const t = (en: string) => en;
const reminder = {
  id: "follow-1",
  task_id: "task-1",
  task_title: "Venue for Friday",
  fingerprint: "a".repeat(64),
  observation_revision: 1,
  summary: "Alex replied: Venue for Friday",
  message_ids: ["sample-venue-2"],
  source_label: "Local mail sample. Not a live mailbox.",
  live_mailbox: false,
  count: 1,
  draft_state: "none",
  draft: null,
};

function card(extra: Partial<Parameters<typeof MailReplyReminderCard>[0]> = {}) {
  return renderToStaticMarkup(
    createElement(MailReplyReminderCard, {
      reminder,
      t,
      drafting: false,
      draftText: LOCAL_REPLY_DRAFT,
      original: "",
      note: "",
      busy: false,
      onRead: () => {},
      onReread: () => {},
      onStartDraft: () => {},
      onDraftText: () => {},
      onReview: () => {},
      onDismiss: () => {},
      onDecide: () => {},
      ...extra,
    }),
  );
}

test("one followed reply offers a draft only after the owner asks, and does not say it was sent", () => {
  assert.equal(reminderIsLocal(reminder), true);
  const closed = card();
  assert.match(closed, /Venue for Friday/);
  assert.match(closed, /Local mail sample/);
  assert.match(closed, /Draft a reply/);
  assert.doesNotMatch(closed, /<textarea/);
  assert.doesNotMatch(closed, /sent the email|Email accepted/i);
  const open = card({ drafting: true });
  assert.match(open, /<textarea/);
  assert.match(open, /Review draft/);
  assert.doesNotMatch(open, /Friday after 3 still works/);
});

test("a saved draft stays a draft and the original read is labeled as unsaved", () => {
  const read = card({ original: "Friday after 3 still works for me." });
  assert.match(read, /Not saved as a memory/);
  assert.match(read, /Friday after 3 still works for me/);
  const pending = card({
    reminder: {
      ...reminder,
      draft_state: "pending",
      draft: {
        id: "draft-1",
        body: LOCAL_REPLY_DRAFT,
        summary: reminder.summary,
        fingerprint: reminder.fingerprint,
        expires_at: "2026-11-25T05:00:00Z",
        send: false,
      },
    },
  });
  assert.match(pending, /does not send the email/);
  assert.match(pending, /Save draft/);
  assert.doesNotMatch(pending, /Draft a reply/);
});
