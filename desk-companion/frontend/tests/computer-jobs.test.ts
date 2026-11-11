import assert from "node:assert/strict";
import test from "node:test";
import {
  isFolderAction,
  jobCancellable,
  readBackCopy,
  recoveryCopy,
  recoveryMatchesNote,
  reviewAvailable,
} from "../src/workspace/jobTypes.ts";
import type { ComputerJob, JobState } from "../src/workspace/jobTypes.ts";

const job = (state: JobState, cancel_requested = false) =>
  ({
    state,
    cancel_requested,
    expires_at: "2026-10-06T12:05:00Z",
  }) as ComputerJob;
test("folder jobs are distinct from the dedicated notes adapter", () => {
  assert.equal(isFolderAction("save_folder_file"), true);
  assert.equal(isFolderAction("verify_folder_file"), true);
  assert.equal(isFolderAction("save_note"), false);
  assert.equal(isFolderAction("verify_note"), false);
});
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
    "owner_takeover",
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

test("read-back and fingerprint failures name a recoverable next step", () => {
  const mismatch = {
    ...job("unknown"),
    error: "JOB_VERIFICATION_FAILED",
    action: "save_folder_file",
    result: { verified: false, reason: "content_mismatch" },
    request: { folder_fingerprint: "abc123def456" },
  } as ComputerJob;
  assert.match(readBackCopy("content_mismatch")![0], /left unchanged/);
  assert.match(recoveryCopy(mismatch)![0], /check the file named above/i);
  assert.equal(readBackCopy("read_back_matches"), null);
  const rebound = {
    ...job("failed"),
    error: "COMPUTER_SCOPE_CHANGED",
    result: null,
  } as ComputerJob;
  assert.match(recoveryCopy(rebound)![0], /prepare a new job/i);
  const cancelled = { ...job("cancelled"), result: null } as ComputerJob;
  assert.match(recoveryCopy(cancelled)![0], /No new file was written/);
  assert.equal(recoveryCopy(job("succeeded")), null);
  for (const reason of [
    "content_mismatch",
    "artifact_missing",
    "target_denied",
    "verification_unavailable",
  ]) {
    const copy = readBackCopy(reason);
    assert.ok(copy);
    assert.match(copy[0], /[A-Za-z]/);
    assert.match(copy[1], /\p{Script=Han}/u);
    assert.doesNotMatch(copy[1], /[與檢驗沒後這為裡]/u);
  }
  const cancelledCopy = recoveryCopy(cancelled);
  assert.match(cancelledCopy![1], /\p{Script=Han}/u);
  assert.doesNotMatch(cancelledCopy![1], /[與檢驗沒後這為裡]/u);
  const reboundCopy = recoveryCopy(rebound);
  assert.match(reboundCopy![1], /\p{Script=Han}/u);
  assert.doesNotMatch(reboundCopy![1], /[與檢驗沒後這為裡]/u);
});
