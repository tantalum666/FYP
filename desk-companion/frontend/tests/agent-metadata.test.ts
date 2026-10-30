import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import {
  loadRunMetadata,
  metadataActions,
  runAccess,
  runMetadata,
} from "../src/workspace/agent/runMetadata.ts";
import { PrivateWriteQueue } from "../src/workspace/personal/privateWrite.ts";
import { ResponseFence } from "../src/workspace/personal/responseFence.ts";

const metadata = {
  id: "run-test-1",
  state: "running",
  version: 3,
  created_at: "2026-10-13T05:00:00Z",
  updated_at: "2026-10-13T05:01:00Z",
};

test("connected hidden owners retain status access; paired, stale, offline and concealed views do not", () => {
  assert.deepEqual(runAccess(true, true, true, false), {
    available: true,
    privateVisible: false,
  });
  assert.deepEqual(runAccess(true, true, true, true), {
    available: true,
    privateVisible: true,
  });
  for (const input of [
    [false, true, true, true],
    [true, false, true, true],
    [true, true, false, true],
  ]) {
    assert.deepEqual(
      runAccess(...(input as [boolean, boolean, boolean, boolean])),
      { available: false, privateVisible: false },
    );
  }
});

test("hidden status loads only the list and projects all private fields out before retaining rows", async () => {
  const paths: string[] = [];
  const rows = await loadRunMetadata(async (path) => {
    paths.push(path);
    return {
      runs: [
        {
          ...metadata,
          goal: "SECRET_GOAL",
          source_ids: ["SECRET_SOURCE"],
          proposal_ids: ["SECRET_REVIEW"],
          artifact_ids: ["SECRET_FILE"],
          question: "SECRET_QUESTION",
          state_reason: "SECRET_REASON",
          mode: "model",
          plan: ["SECRET_PLAN"],
          private_hidden: false,
        },
      ],
    };
  });
  assert.deepEqual(paths, ["/agent-runs"]);
  assert.deepEqual(
    Object.keys(rows[0]).sort(),
    ["id", "state", "version", "created_at", "updated_at"].sort(),
  );
  assert.doesNotMatch(JSON.stringify(rows), /SECRET|model/);
});

test("unexpected status strings and date text cannot be echoed as private content", () => {
  assert.equal(
    runMetadata({ ...metadata, state: "SECRET_STATUS" })?.state,
    "unknown",
  );
  assert.equal(runMetadata({ ...metadata, id: "../SECRET" }), null);
  assert.equal(runMetadata({ ...metadata, version: 0 }), null);
  assert.equal(runMetadata({ ...metadata, updated_at: "SECRET_DATE" }), null);
  assert.equal(runMetadata(null), null);
  assert.equal(
    runMetadata({
      ...metadata,
      created_at: "2026-10-13 05:00:00 GMT (SECRET_COMMENT)",
    })?.created_at,
    "2026-10-13T05:00:00.000Z",
  );
});

test("hidden controls are pause/cancel only and unknown or terminal states gain no authority", () => {
  for (const state of [
    "queued",
    "planning",
    "running",
    "waiting_input",
    "waiting_review",
    "waiting_effect",
    "verifying",
  ]) {
    assert.deepEqual(metadataActions(state), ["pause", "cancel"]);
  }
  assert.deepEqual(metadataActions("paused"), ["cancel"]);
  assert.deepEqual(metadataActions("blocked"), ["cancel"]);
  for (const state of [
    "unknown",
    "future",
    "succeeded",
    "partial",
    "failed",
    "cancelled",
    "cancelling",
  ])
    assert.deepEqual(metadataActions(state), []);
});

test("invalid list data is rejected rather than enabling controls from stale private objects", async () => {
  await assert.rejects(
    loadRunMetadata(async () => ({ runs: "SECRET_LIST" })),
    /RUN_METADATA_INVALID/,
  );
  assert.deepEqual(
    await loadRunMetadata(async () => ({
      runs: [metadata, { ...metadata, version: "3" }, null],
    })),
    [runMetadata(metadata)],
  );
});

test("hide/show and identity transitions fence both private and metadata late responses", () => {
  const fence = new ResponseFence();
  fence.update("owner:one:private", true);
  const privateEpoch = fence.capture();
  fence.update("owner:one:metadata", true);
  const hiddenEpoch = fence.capture();
  assert.equal(fence.accepts(privateEpoch), false);
  assert.equal(fence.accepts(hiddenEpoch), true);
  fence.update("owner:one:private", true);
  assert.equal(fence.accepts(privateEpoch), false);
  assert.equal(fence.accepts(hiddenEpoch), false);
  const newer = fence.capture();
  fence.update("paired:two:metadata", false);
  assert.equal(fence.accepts(newer), false);
});

test("an uncertain or in-flight pause never occupies the cancellation queue and retries keep their original version", async () => {
  let rejectPause!: (error: unknown) => void;
  const sent: { path: string; serialized: string; key: string }[] = [];
  const pause = new PrivateWriteQueue(
    async (op) => {
      sent.push({ ...op });
      return new Promise((_resolve, reject) => {
        rejectPause = reject;
      });
    },
    () => "pause-key",
  );
  const cancel = new PrivateWriteQueue(
    async (op) => {
      sent.push({ ...op });
      return { run: { ...metadata, state: "cancelled", version: 4 } };
    },
    () => "cancel-key",
  );
  const pending = pause.send("/agent-runs/run-test-1/actions", {
    action: "pause",
    expected_version: 3,
  });
  assert.equal(pause.active, true);
  assert.equal(
    (
      await cancel.send<{ run: { state: string } }>(
        "/agent-runs/run-test-1/actions",
        { action: "cancel", expected_version: 3 },
      )
    ).run.state,
    "cancelled",
  );
  rejectPause({ status: 0 });
  await assert.rejects(pending);
  assert.equal(pause.pending, true);
  const recovery = pause.retry();
  rejectPause({ status: 409 });
  await assert.rejects(recovery);
  assert.deepEqual(sent[0], sent[2]);
  assert.notEqual(sent[0].key, sent[1].key);
  assert.equal(pause.pending, false);
});

test("hidden component keeps uncertain queues through refresh failures and never requests private details", () => {
  const root = new URL("../src/workspace/agent/", import.meta.url);
  const panel = readFileSync(new URL("RunMetadataPanel.tsx", root), "utf8");
  const hook = readFileSync(new URL("useRunMetadata.ts", root), "utf8");
  assert.doesNotMatch(
    panel,
    /run\.(goal|state_reason|source_ids|artifact_ids|proposal_ids)|RunDetail|RunComposer|ArtifactList/,
  );
  assert.match(panel, /disabled=\{!fresh \|\| cancelLocked\}/);
  assert.match(panel, /version !== run.version/);
  assert.match(hook, /sequence.current !== seq/);
  assert.doesNotMatch(
    hook,
    /\/scope|\/sources|\/artifacts|setValue\(null\);\s*setError\(e\)/,
  );
});
