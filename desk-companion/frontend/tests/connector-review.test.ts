import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { ResponseFence } from "../src/workspace/personal/responseFence.ts";
import { PrivateWriteQueue } from "../src/workspace/personal/privateWrite.ts";
import {
  connectorAccess,
  connectorCancellable,
  connectorId,
  connectorMetadata,
  connectorReviewable,
  connectorReviewKey,
  connectorSelection,
  loadConnectorMetadata,
  loadConnectorPrivate,
  loadConnectorSelectedMetadata,
} from "../src/workspace/connectors/types.ts";
import type {
  ConnectorCapabilities,
  ConnectorIntent,
} from "../src/workspace/connectors/types.ts";

const hash = "a".repeat(64),
  id = "b".repeat(32);
const intent: ConnectorIntent = {
  id,
  state: "review",
  version: 1,
  intent_hash: hash,
  created_at: "2026-10-13T05:00:00Z",
  updated_at: "2026-10-13T05:00:00Z",
  expires_at: "2030-01-01T00:00:00Z",
  dispatched: false,
  cancel_requested: false,
  intent: {
    tool_id: "mcp.public.lookup",
    connector_id: "public",
    tool_name: "lookup",
    endpoint: "https://connector.example.test/mcp",
    server_name: "Public fixture",
    server_version: "1.0",
    destination_scope: "Public fixture data",
    effect: "read",
    arguments: { text: "SENSITIVE_ARGUMENT" },
    data_policy: "public_or_synthetic",
    descriptor_sha256: hash,
    grant_sha256: hash,
    notice: "SENSITIVE_NOTICE",
    provider_destination: null,
  },
};
const capabilities: ConnectorCapabilities = {
  scope_revision: hash,
  tools: [
    {
      ...intent.intent!,
      review_required: true,
      live_acceptance: "not_verified_here",
    },
  ],
};
const now = Date.parse("2026-10-13T05:01:00Z");

test("only connected, visible owner surfaces can read status; private details have an additional gate", () => {
  assert.deepEqual(connectorAccess(true, true, true, false), {
    available: true,
    privateVisible: false,
  });
  assert.deepEqual(connectorAccess(true, true, true, true), {
    available: true,
    privateVisible: true,
  });
  for (const args of [
    [false, true, true, true],
    [true, false, true, true],
    [true, true, false, true],
  ])
    assert.deepEqual(
      connectorAccess(...(args as [boolean, boolean, boolean, boolean])),
      { available: false, privateVisible: false },
    );
});

test("metadata reads demand server-side redaction and whitelist a content-free projection", async () => {
  const paths: string[] = [];
  const rows = await loadConnectorMetadata(async (path) => {
    paths.push(path);
    return {
      intents: [
        {
          ...intent,
          code: "SENSITIVE_CODE",
          result: { text: ["SENSITIVE_RESULT"] },
          provider_destination: "SENSITIVE_PROVIDER",
        },
      ],
    };
  });
  assert.deepEqual(paths, ["/connectors/intents?metadata_only=true"]);
  assert.deepEqual(
    Object.keys(rows[0]).sort(),
    [
      "id",
      "state",
      "version",
      "created_at",
      "updated_at",
      "expires_at",
      "dispatched",
      "cancel_requested",
    ].sort(),
  );
  assert.doesNotMatch(
    JSON.stringify(rows),
    /SENSITIVE|endpoint|provider|arguments|intent_hash/,
  );
});

test("hidden load never reads private detail or even capabilities", async () => {
  const paths: string[] = [];
  assert.deepEqual(
    await loadConnectorPrivate(
      async (path) => {
        paths.push(path);
        throw new Error("private fetch");
      },
      id,
      false,
    ),
    { capabilities: null, detail: null },
  );
  assert.deepEqual(paths, []);
  const loaded = await loadConnectorPrivate(
    async (path) => {
      paths.push(path);
      return path.endsWith("capabilities") ? capabilities : { intent };
    },
    id,
    true,
  );
  assert.deepEqual(
    paths.sort(),
    ["/connectors/capabilities", `/connectors/intents/${id}`].sort(),
  );
  assert.equal(loaded.detail?.id, id);
});

test("malformed or nested listing, private path injection, bad version and unknown status fail closed", async () => {
  await assert.rejects(
    loadConnectorMetadata(async () => ({ intents: { intents: [intent] } })),
    /CONNECTOR_RESPONSE_INVALID/,
  );
  for (const value of [
    null,
    "../private",
    "https://evil.test",
    "",
    "a".repeat(33),
  ])
    assert.equal(connectorId(value), false);
  for (const changes of [
    { version: "1" },
    { version: 0 },
    { id: "../private" },
    { created_at: "SECRET" },
  ])
    assert.equal(connectorMetadata({ ...intent, ...changes }), null);
  assert.equal(
    connectorMetadata({ ...intent, state: "PRIVATE_STATUS" })?.state,
    "unrecognized",
  );
  const paths: string[] = [];
  await loadConnectorPrivate(
    async (path) => {
      paths.push(path);
      return capabilities;
    },
    "../private",
    true,
  );
  assert.deepEqual(paths, ["/connectors/capabilities"]);
  await assert.rejects(
    loadConnectorPrivate(
      async (path) =>
        path.endsWith("capabilities")
          ? capabilities
          : { intent: { ...intent, id: "c".repeat(32) } },
      id,
      true,
    ),
    /CONNECTOR_RESPONSE_INVALID/,
  );
});

test("approval is exact, current, public-only and bound to the operator catalog even for a read", () => {
  assert.equal(connectorReviewable(intent, capabilities, true, now), true);
  assert.equal(connectorReviewable(intent, capabilities, false, now), false);
  assert.equal(connectorReviewable(intent, null, true, now), false);
  assert.equal(
    connectorReviewable(intent, { ...capabilities, tools: [] }, true, now),
    false,
  );
  for (const changes of [
    { state: "queued" },
    { state: "observed_result" },
    { state: "unknown_effect" },
    { cancel_requested: true },
    { dispatched: true },
    { version: 0 },
    { intent_hash: "invalid" },
    { expires_at: "bad" },
    { expires_at: "2020-01-01" },
  ])
    assert.equal(
      connectorReviewable(
        { ...intent, ...changes } as ConnectorIntent,
        capabilities,
        true,
        now,
      ),
      false,
    );
  for (const changes of [
    { endpoint: "https://other.example/mcp" },
    { effect: "write" },
    { tool_name: "changed" },
    { grant_sha256: "b".repeat(64) },
    { descriptor_sha256: "b".repeat(64) },
    { destination_scope: "changed" },
    { data_policy: "private" },
    { arguments: null },
    { notice: "" },
    { provider_destination: undefined },
    {
      provider_destination: {
        id: "x",
        provider: "x",
        endpoint: "",
        kind: "text",
      },
    },
  ])
    assert.equal(
      connectorReviewable(
        {
          ...intent,
          intent: { ...intent.intent!, ...changes },
        } as ConnectorIntent,
        capabilities,
        true,
        now,
      ),
      false,
    );
});

test("checkbox binding changes for a new version, hash, destination, provider or arguments", () => {
  const key = connectorReviewKey(intent);
  for (const changed of [
    { ...intent, version: 2 },
    { ...intent, intent_hash: "b".repeat(64) },
    { ...intent, id: "c".repeat(32) },
    {
      ...intent,
      intent: { ...intent.intent!, arguments: { text: "CHANGED" } },
    },
    {
      ...intent,
      intent: {
        ...intent.intent!,
        provider_destination: {
          id: "actual",
          kind: "text" as const,
          provider: "configured",
          endpoint: "https://provider.example.test/generate",
        },
      },
    },
  ])
    assert.notEqual(connectorReviewKey(changed), key);
});

test("Cancel is limited to current pre-terminal calls and does not imply rollback", () => {
  for (const state of ["review", "queued", "preflight", "dispatching"] as const)
    assert.equal(connectorCancellable({ ...intent, state }), true);
  for (const state of [
    "observed_result",
    "unknown_effect",
    "failed",
    "cancelled",
    "rejected",
    "expired",
    "unrecognized",
  ] as const)
    assert.equal(connectorCancellable({ ...intent, state }), false);
  assert.equal(
    connectorCancellable({ ...intent, cancel_requested: true }),
    false,
  );
});

test("review switching prompts for checked choices and unknown receipts and blocks active requests", () => {
  assert.equal(connectorSelection(id, null, true, false), "confirm");
  assert.equal(connectorSelection(id, null, true, true), "stay");
  assert.equal(connectorSelection(id, id, true, false), "stay");
  assert.equal(connectorSelection(id, null, false, false), "switch");
});

test("pending approval and cancellation use independent operation IDs and retries retain exact version/hash", async () => {
  const calls: { path: string; serialized: string; key: string }[] = [];
  let rejectApproval!: (e: unknown) => void;
  const approval = new PrivateWriteQueue(
    async (op) => {
      calls.push({ ...op });
      return new Promise((_resolve, reject) => {
        rejectApproval = reject;
      });
    },
    () => "approval-key",
  );
  const cancellation = new PrivateWriteQueue(
    async (op) => {
      calls.push({ ...op });
      return { intent: { ...connectorMetadata(intent), state: "cancelled" } };
    },
    () => "cancel-key",
  );
  const first = approval.send(`/connectors/intents/${id}/approve`, {
    expected_version: 1,
    intent_hash: hash,
    public_only: true,
  });
  assert.equal(approval.active, true);
  await cancellation.send(
    `/connectors/intents/${id}/cancel?metadata_only=true`,
    { expected_version: 1 },
  );
  rejectApproval({ status: 0 });
  await assert.rejects(first);
  assert.equal(approval.pending, true);
  const retry = approval.retry();
  rejectApproval({ status: 409 });
  await assert.rejects(retry);
  assert.deepEqual(calls[0], calls[2]);
  assert.notEqual(calls[0].key, calls[1].key);
  assert.match(calls[1].path, /metadata_only=true/);
});

test("hide/show, disconnect/reconnect and same-principal session replacement fence late results", async () => {
  for (const next of [
    "owner:one:metadata",
    "owner:two:private",
    "disconnected",
    "closed",
  ]) {
    const fence = new ResponseFence();
    fence.update("owner:one:private", true);
    const old = fence.capture();
    let resolve!: (value: unknown) => void;
    let published = false;
    const late = new Promise((done) => {
      resolve = done;
    }).then(() => {
      if (fence.accepts(old)) published = true;
    });
    fence.update(next, next !== "disconnected" && next !== "closed");
    fence.update("owner:one:private", true);
    resolve({ text: "PRIVATE_LATE_RESULT" });
    await late;
    assert.equal(published, false, next);
  }
});

test("unmount clear prevents a late old queue from consuming a replacement component operation", async () => {
  let resolve!: (value: unknown) => void;
  const old = new PrivateWriteQueue(
    () =>
      new Promise((done) => {
        resolve = done;
      }),
    () => "old-owner-op",
  );
  const first = old.send("/connectors/intents/a/approve", {
    expected_version: 1,
  });
  old.clear();
  const replacement = new PrivateWriteQueue(
    async () => {
      throw { status: 0 };
    },
    () => "new-owner-op",
  );
  await assert.rejects(
    replacement.send("/connectors/intents/b/approve", { expected_version: 2 }),
  );
  resolve({ intent: { result: "PRIVATE_OLD_RESULT" } });
  await first;
  assert.equal(old.pending, false);
  assert.equal(replacement.pending, true);
});

test("production integration keeps drafts volatile, session fencing synchronous, and hidden cancellation separate", () => {
  const base = new URL("../src/workspace/connectors/", import.meta.url);
  const panel = readFileSync(new URL("ConnectorReviewPanel.tsx", base), "utf8");
  const hook = readFileSync(new URL("useConnectorData.ts", base), "utf8");
  const detail = readFileSync(
    new URL("ConnectorIntentDetail.tsx", base),
    "utf8",
  );
  assert.doesNotMatch(
    panel + hook + detail,
    /localStorage|sessionStorage|dangerouslySetInnerHTML|<iframe|<a\b/,
  );
  assert.match(
    panel,
    /const approval = usePrivateMutation\(\);\s*const cancellation = usePrivateMutation\(\)/,
  );
  assert.match(panel, /useDraftGuard\(dirty, busy\)/);
  assert.match(
    panel,
    /expected_version: detail.version,\s*intent_hash: detail.intent_hash,\s*public_only: true/,
  );
  assert.match(panel, /key=\{`\$\{identity\}:\$\{epoch\}`\}/);
  assert.match(
    panel,
    /fence.current.update\("session-changing", false\);\s*setSessionEpoch/,
  );
  assert.match(
    panel,
    /if \(!alive.current \|\| !fence.accepts\(captured\)\) return/,
  );
  assert.match(hook, /serial !== sequence.current/);
  assert.match(hook, /alive.current = false;\s*\+\+sequence.current/);
  assert.match(detail, /disabled=\{!fresh \|\| cancellationLocked\}/);
});

test("hidden linked calls outside the latest list use exact metadata-only detail and strip unexpected content", async () => {
  const paths: string[] = [];
  const loaded = await loadConnectorSelectedMetadata(async (path) => {
    paths.push(path);
    return { intent: { ...intent, result: { text: ["PRIVATE_RESULT"] } } };
  }, id);
  assert.deepEqual(paths, [`/connectors/intents/${id}?metadata_only=true`]);
  assert.equal(loaded?.id, id);
  assert.doesNotMatch(
    JSON.stringify(loaded),
    /SENSITIVE|PRIVATE|endpoint|intent_hash|arguments/,
  );
  await assert.rejects(
    loadConnectorSelectedMetadata(
      async () => ({ intent: { ...intent, id: "c".repeat(32) } }),
      id,
    ),
    /CONNECTOR_RESPONSE_INVALID/,
  );
  const unchanged = paths.length;
  assert.equal(
    await loadConnectorSelectedMetadata(async (path) => {
      paths.push(path);
      return {};
    }, "../escape"),
    null,
  );
  assert.equal(paths.length, unchanged);
});
