import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync, readdirSync } from "node:fs";
import { PrivateWriteQueue } from "../src/workspace/personal/privateWrite.ts";
import { ResponseFence } from "../src/workspace/personal/responseFence.ts";
import {
  byteVerified,
  canReviewProposal,
  newRunDraft,
  prepareRun,
  runActions,
  sourceFormat,
} from "../src/workspace/agent/types.ts";
import type {
  ArtifactRecord,
  RunDraft,
  RunScope,
} from "../src/workspace/agent/types.ts";
import {
  rawUpload,
  readSourceFile,
  SOURCE_BYTE_LIMIT,
} from "../src/workspace/agent/upload.ts";
const root = new URL("../src/workspace/agent/", import.meta.url);
const source = (name: string) => readFileSync(new URL(name, root), "utf8");
const scope: RunScope = {
  scope_revision: "a".repeat(64),
  modes: ["deterministic", "model"],
  business_context_allowed: true,
  destinations: [
    {
      id: "provider-a",
      kind: "text",
      provider: "Configured A",
      endpoint: "https://provider.example/v1",
    },
    {
      id: "voice-a",
      kind: "voice",
      provider: "Voice",
      endpoint: "wss://voice.example",
    },
  ],
  sources: Array.from({ length: 12 }, (_, index) => ({
    id: `file-${index}`,
    name: `Notes ${index}.md`,
    format: "markdown" as const,
    status: "verified" as const,
    byte_count: 16,
    revision: 1,
    sha256: "f".repeat(64),
  })),
  tasks: Array.from({ length: 10 }, (_, index) => ({
    id: `task-${index}`,
    title: `Task ${index}`,
    version: 3,
  })),
  events: [
    {
      id: "event-1",
      title: "Selected event",
      version: 2,
      start_local: "2026-10-13T09:00",
      end_local: "2026-10-13T10:00",
      timezone: "Asia/Hong_Kong",
    },
  ],
  limits: {},
};
const draft = (extra: Partial<RunDraft> = {}): RunDraft => ({
  ...newRunDraft(),
  goal: "Compare selected sources",
  retain: true,
  source_ids: ["file-0"],
  ...extra,
});

test("persistent work requires an explicit retention choice and at least one valid selected source", () => {
  assert.equal(prepareRun(newRunDraft(), scope), null);
  assert.equal(prepareRun(draft({ retain: false }), scope), null);
  assert.equal(prepareRun(draft({ source_ids: [] }), scope), null);
  assert.equal(prepareRun(draft({ goal: "   " }), scope), null);
  assert.equal(
    prepareRun(draft({ source_ids: ["not-selected"] }), scope),
    null,
  );
  assert.equal(
    prepareRun(draft({ source_ids: ["file-0", "file-0"] }), scope),
    null,
  );
  assert.equal(prepareRun(draft(), { ...scope, scope_revision: "" }), null);
  assert.equal(prepareRun(draft(), scope)?.retain, true);
});
test("local compilation never inherits provider transmission or mutation grants", () => {
  const input = prepareRun(
    draft({
      destination: "provider-a",
      share: true,
      allow_mutation_proposals: true,
    }),
    scope,
  )!;
  assert.equal(input.mode, "deterministic");
  assert.equal(input.provider_destination_id, null);
  assert.equal(input.share_sources_with_provider, false);
  assert.equal(input.allow_mutation_proposals, false);
  assert.deepEqual(input.mutation_requests, []);
});
test("unknown source reservations and finished or expired reviews cannot be selected", () => {
  assert.equal(
    prepareRun(draft(), {
      ...scope,
      sources: scope.sources.map((x) => ({ ...x, status: "unknown" as const })),
    }),
    null,
  );
  const now = Date.parse("2026-10-12T15:00:00Z");
  const review = { state: "pending", expires_at: "2026-10-12T15:01:00Z" };
  assert.equal(canReviewProposal(review, now), true);
  assert.equal(
    canReviewProposal({ ...review, state: "confirmed" }, now),
    false,
  );
  assert.equal(
    canReviewProposal({ ...review, state: "cancelled" }, now),
    false,
  );
  assert.equal(canReviewProposal({ ...review, state: "expired" }, now), false);
  assert.equal(canReviewProposal(review, now + 60000), false);
  assert.equal(
    canReviewProposal({ ...review, expires_at: "invalid" }, now),
    false,
  );
  assert.equal(canReviewProposal({ state: "pending" }, now), false);
});
test("adaptive work requires exact text destination plus explicit selected-content sharing", () => {
  const model = draft({
    mode: "model",
    destination: "provider-a",
    share: true,
  });
  assert.equal(prepareRun({ ...model, share: false }, scope), null);
  assert.equal(prepareRun({ ...model, destination: "voice-a" }, scope), null);
  assert.equal(
    prepareRun({ ...model, destination: "old-provider" }, scope),
    null,
  );
  assert.equal(prepareRun(model, { ...scope, modes: ["deterministic"] }), null);
  assert.equal(
    prepareRun(
      { ...model, task_ids: ["task-0"] },
      { ...scope, business_context_allowed: false },
    ),
    null,
  );
  assert.equal(
    prepareRun(model, { ...scope, business_context_allowed: false })?.mode,
    "model",
  );
  assert.equal(
    prepareRun({ ...model, allow_mutation_proposals: true }, scope)
      ?.allow_mutation_proposals,
    true,
  );
});
test("selection count, source bytes and section requirements match server ceilings", () => {
  const ten = draft({
    mode: "model",
    destination: "provider-a",
    share: true,
    source_ids: scope.sources.slice(0, 10).map((x) => x.id),
  });
  assert.ok(prepareRun(ten, scope));
  assert.equal(prepareRun({ ...ten, task_ids: ["task-0"] }, scope), null);
  assert.ok(
    prepareRun(draft({ source_ids: scope.sources.map((x) => x.id) }), scope),
  );
  const large = {
    ...scope,
    sources: scope.sources.map((x) => ({ ...x, byte_count: 1024 * 1024 })),
  };
  assert.ok(
    prepareRun(
      draft({ source_ids: large.sources.slice(0, 4).map((x) => x.id) }),
      large,
    ),
  );
  assert.equal(
    prepareRun(
      draft({ source_ids: large.sources.slice(0, 5).map((x) => x.id) }),
      large,
    ),
    null,
  );
  assert.deepEqual(
    prepareRun(draft({ required_sections: " Findings \n\n Risks " }), scope)
      ?.required_sections,
    ["Findings", "Risks"],
  );
  assert.equal(
    prepareRun(
      draft({ required_sections: Array(9).fill("Section").join("\n") }),
      scope,
    ),
    null,
  );
  assert.equal(
    prepareRun(draft({ required_sections: "S".repeat(161) }), scope),
    null,
  );
});
test("reviewed request arrays are immutable snapshots rather than live checkbox arrays", () => {
  const form = draft();
  const input = prepareRun(form, scope)!;
  form.source_ids.push("file-1");
  form.goal = "Changed goal";
  assert.deepEqual(input.source_ids, ["file-0"]);
  assert.equal(input.goal, "Compare selected sources");
});
test("unknown model outcome has an explicit new-attempt action and no ordinary resume", () => {
  assert.deepEqual(runActions("blocked", "RUN_PROVIDER_OUTCOME_UNKNOWN"), [
    "retry_model",
    "steer",
    "cancel",
  ]);
  assert.deepEqual(runActions("paused", "RUN_PAUSED", 2), ["resume", "cancel"]);
  assert.deepEqual(runActions("waiting_input"), ["answer", "steer", "cancel"]);
  assert.deepEqual(runActions("succeeded", null, 1), ["steer"]);
  assert.deepEqual(runActions("partial", null, 2), []);
  assert.deepEqual(runActions("cancelled"), []);
  assert.deepEqual(runActions("new-future-state"), []);
});
test("file selection validates UTF-8 bytes, suffix, display name and content before upload", async () => {
  const fakeFile = (name: string, bytes: Uint8Array, size = bytes.length) => ({
    name,
    size,
    arrayBuffer: async () => bytes.slice().buffer,
  });
  const prepared = await readSourceFile(
    fakeFile("笔记.markdown", new TextEncoder().encode("原始资料\n")),
  );
  assert.equal(
    new URL("https://local.invalid" + prepared.path).searchParams.get("format"),
    "markdown",
  );
  assert.equal(prepared.body.content, "原始资料\n");
  await assert.rejects(
    readSourceFile(fakeFile("note.html", new Uint8Array([65]))),
    /SOURCE_FORMAT_INVALID/,
  );
  await assert.rejects(
    readSourceFile(fakeFile("../note.txt", new Uint8Array([65]))),
    /SOURCE_FORMAT_INVALID/,
  );
  await assert.rejects(
    readSourceFile(fakeFile("note.txt", new Uint8Array([0xff]))),
    /SOURCE_FORMAT_INVALID/,
  );
  await assert.rejects(
    readSourceFile(fakeFile("note.txt", new Uint8Array([0]))),
    /INVALID_SOURCE_TEXT/,
  );
  await assert.rejects(
    readSourceFile(
      fakeFile("note.txt", new Uint8Array(), SOURCE_BYTE_LIMIT + 1),
    ),
    /SOURCE_TOO_LARGE/,
  );
  assert.equal(sourceFormat("REPORT.CSV"), "csv");
  assert.equal(sourceFormat("file.js"), null);
});
test("source upload preserves raw Unicode and one operation ID across an unknown response without storage", async () => {
  const descriptors = ["localStorage", "sessionStorage"].map(
    (key) => [key, Object.getOwnPropertyDescriptor(globalThis, key)] as const,
  );
  descriptors.forEach(([key]) =>
    Object.defineProperty(globalThis, key, {
      configurable: true,
      get() {
        throw new Error("Private content reached browser storage");
      },
    }),
  );
  try {
    const sent: ReturnType<typeof rawUpload>[] = [];
    const queue = new PrivateWriteQueue(
      async (operation) => {
        const raw = rawUpload(operation);
        sent.push(raw);
        if (sent.length === 1) throw { status: 0 };
        return { source: { id: "saved" } };
      },
      () => "same-source-operation",
    );
    const body = { content: "Private 中文 source\n" };
    await assert.rejects(
      queue.send("/sources/upload?name=notes.txt&format=text", body),
    );
    body.content = "New unsent edit";
    assert.deepEqual(await queue.retry(), { source: { id: "saved" } });
    assert.deepEqual(sent[0], sent[1]);
    assert.equal(sent[1].body, "Private 中文 source\n");
    assert.equal(sent[1].headers["X-Operation-Id"], "same-source-operation");
    assert.equal(sent[1].headers["Content-Type"], "text/plain;charset=utf-8");
  } finally {
    descriptors.forEach(([key, descriptor]) =>
      descriptor
        ? Object.defineProperty(globalThis, key, descriptor)
        : Reflect.deleteProperty(globalThis, key),
    );
  }
});
test("a file hash or model message does not grant structural or semantic verification", () => {
  const artifact = {
    status: "unknown",
    verification: "unverified",
    sha256: "a".repeat(64),
    quality: "not_semantically_checked",
  } as ArtifactRecord;
  assert.equal(byteVerified(artifact), false);
  assert.equal(byteVerified({ ...artifact, status: "verified" }), false);
  assert.equal(
    byteVerified({
      ...artifact,
      status: "verified",
      verification: "byte_readback",
    }),
    true,
  );
  assert.equal(artifact.quality, "not_semantically_checked");
  assert.match(source("ArtifactList.tsx"), /Content quality not reviewed/);
});
test("privacy, identity and hide-show transitions permanently fence earlier replies", () => {
  const fence = new ResponseFence();
  fence.update("owner:one:session1", true);
  const old = fence.capture();
  fence.update("owner:one:session1", false);
  fence.update("owner:one:session1", true);
  assert.equal(fence.accepts(old), false);
  const newer = fence.capture();
  fence.update("paired:display:session1", false);
  assert.equal(fence.accepts(newer), false);
  fence.update("owner:one:session2", true);
  assert.equal(fence.accepts(newer), false);
});
test("component contracts preserve modal drafts, selected-run fences and independent cancellation", () => {
  const composer = source("RunComposer.tsx"),
    detail = source("RunDetail.tsx"),
    panel = source("RunPanel.tsx"),
    reads = source("useAgentRuns.ts");
  assert.match(composer, /dirty=\{dirty\}/);
  assert.match(
    composer,
    /review\.input\.scope_revision !== scope\.scope_revision/,
  );
  assert.match(composer, /!input\s*\|\|\s*uploadDraft/);
  assert.match(detail, /cancellation = usePrivateMutation\(\)/);
  assert.match(
    detail,
    /disabled=\{!fresh \|\| cancelLocked\}\s+onClick=\{\(\) => setCancelVersion\(run\.version\)\}/,
  );
  assert.match(detail, /editor\.version !== run\.version/);
  assert.match(detail, /new AI request and may be billed again/);
  assert.match(reads, /current\.current !== id/);
  assert.match(reads, /sequence\.current !== seq/);
  assert.match(
    reads,
    /if \(!recoverableRunReadError\(e\) \|\| terminalError\) setValue\(null\)/,
  );
  assert.match(reads, /fresh: !!visibleValue && !error/);
  assert.match(panel, /desk:session/);
  assert.match(panel, /key=\{epoch\}/);
  assert.match(panel, /setDetailGeneration/);
});
test("all new run components avoid persistent browser bodies and raw generated HTML", () => {
  const all = readdirSync(root)
    .filter((name) => /\.tsx?$/.test(name))
    .map(source)
    .join("\n");
  assert.doesNotMatch(
    all,
    /localStorage|sessionStorage|dangerouslySetInnerHTML|innerHTML\s*=|\beval\(/,
  );
  assert.match(
    source("ArtifactList.tsx"),
    /<pre tabIndex=\{0\}>\{preview\.content\}<\/pre>/,
  );
  assert.match(
    source("ArtifactList.tsx"),
    /crypto\.subtle\.digest\("SHA-256", bytes\)/,
  );
  assert.match(source("ArtifactList.tsx"), /if \(!valid\(\)\) return;/);
  assert.match(source("SourcePreview.tsx"), /fence\.accepts\(epoch\)/);
});
