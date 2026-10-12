import assert from "node:assert/strict";
import test from "node:test";
import {
  jobCancellable,
  isApplicationJob,
  verificationAction,
  recoveryMatchesNote,
  reviewAvailable,
} from "../src/workspace/jobTypes.ts";
import type { ComputerJob, JobState } from "../src/workspace/jobTypes.ts";

const job = (state: JobState, cancel_requested = false) =>
  ({
    state,
    cancel_requested,
    expires_at: "2026-10-06T12:05:00Z",
    intent_hash: "reviewed-test-intent",
    request: { title: "Test", content: "Fictional", artifact_id: "test", task_version: null },
  }) as ComputerJob;
test("approval requires fresh data and an unexpired review", () => {
  assert.equal(
    reviewAvailable(job("review"), Date.parse("2026-10-06T12:04:00Z"), true),
    true,
  );
  assert.equal(
    reviewAvailable(job("review"), Date.parse("2026-10-06T12:05:00Z"), true),
    false,
  );
  assert.equal(
    reviewAvailable(job("review"), Date.parse("2026-10-06T12:04:00Z"), false),
    false,
  );
  assert.equal(
    reviewAvailable(job("cancelled"), Date.parse("2026-10-06T12:04:00Z"), true),
    false,
  );
});
test("cancellation remains available for active and unknown jobs only", () => {
  for (const state of [
    "review",
    "queued",
    "running",
    "verifying",
    "unknown",
  ] as JobState[])
    assert.equal(jobCancellable(job(state)), true);
  for (const state of [
    "succeeded",
    "failed",
    "expired",
    "cancelled",
    "cancel_requested",
  ] as JobState[])
    assert.equal(jobCancellable(job(state)), false);
  assert.equal(jobCancellable(job("unknown", true)), false);
});

test("hidden job metadata cannot be approved without reviewed content and hash", () => {
  const hidden = { ...job("review"), request: undefined, intent_hash: undefined };
  assert.equal(reviewAvailable(hidden, Date.parse("2026-10-06T12:04:00Z"), true), false);
});
test("recovering another operation must not clear the current unsaved note", () => {
  const pending = {
    path: "/computer/jobs",
    body: { action: "save_note", title: "A", content: "你好 🦉" },
  };
  assert.equal(recoveryMatchesNote(pending, "A", "你好 🦉"), true);
  assert.equal(
    recoveryMatchesNote(pending, "New note", "New unsaved work"),
    false,
  );
  assert.equal(
    recoveryMatchesNote(
      { ...pending, path: "/computer/jobs/one/approve" },
      "A",
      "你好 🦉",
    ),
    false,
  );
  assert.equal(
    recoveryMatchesNote(
      { ...pending, body: { ...pending.body, action: "verify_note" } },
      "A",
      "你好 🦉",
    ),
    false,
  );
  assert.equal(recoveryMatchesNote(null, "A", "你好 🦉"), false);
});

test("pending note recovery is scoped to the same linked task", () => {
  const pending = {
    path: "/computer/jobs",
    body: {
      action: "save_note",
      title: "Same",
      content: "Same",
      task_id: "task-A",
    },
  };
  assert.equal(recoveryMatchesNote(pending, "Same", "Same", "task-A"), true);
  assert.equal(recoveryMatchesNote(pending, "Same", "Same", "task-B"), false);
  assert.equal(recoveryMatchesNote(pending, "Same", "Same"), false);
});

test("record recovery preserves a different destination draft", () => {
  const pending = {
    path: "/computer/jobs",
    body: { action: "create_record", title: "A", content: "中文 🎯" },
  };
  assert.equal(
    recoveryMatchesNote(pending, "A", "中文 🎯", undefined, "create_record"),
    true,
  );
  assert.equal(
    recoveryMatchesNote(pending, "A", "中文 🎯", undefined, "save_note"),
    false,
  );
  assert.equal(
    recoveryMatchesNote(pending, "B", "中文 🎯", undefined, "create_record"),
    false,
  );
});
test("verification preserves adapter category", () => {
  assert.equal(isApplicationJob("create_record"), true);
  assert.equal(isApplicationJob("verify_record"), true);
  assert.equal(isApplicationJob("save_note"), false);
  assert.equal(verificationAction("create_record"), "verify_record");
  assert.equal(verificationAction("verify_record"), "verify_record");
  assert.equal(verificationAction("save_note"), "verify_note");
  assert.equal(verificationAction("verify_note"), "verify_note");
});
