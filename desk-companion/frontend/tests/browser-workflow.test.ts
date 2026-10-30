import assert from "node:assert/strict";
import test from "node:test";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import {
  browserReady,
  browserReviewable,
  browserVerified,
  browserExportVerified,
  browserCancellable,
  browserSelection,
  catalogUrl,
} from "../src/workspace/browser/types.ts";
import type {
  BrowserCapabilities,
  BrowserJob,
} from "../src/workspace/browser/types.ts";
import { verifiedExportBytes } from "../src/workspace/browser/exportVerification.ts";
import { ResponseFence } from "../src/workspace/personal/responseFence.ts";
import { PrivateWriteQueue } from "../src/workspace/personal/privateWrite.ts";
const capabilities: BrowserCapabilities = {
  configured: true,
  ready: true,
  reason: null,
  experimental: true,
  scope: "public_synthetic_only",
  network_boundary: "routing_only",
  live_acceptance: "not_verified_here",
  destination: { id: "stackedit_markdown_v1", url: "https://stackedit.io/app" },
  sources: [
    {
      id: "python_asyncio",
      url: "https://docs.python.org/3/library/asyncio.html",
      label: "Python asyncio",
    },
  ],
  limits: { title_chars: 120, note_chars: 2000, export_bytes: 65536 },
};
const hash = "a".repeat(64);
const job: BrowserJob = {
  id: "1".repeat(32),
  state: "review",
  version: 2,
  intent_hash: hash,
  expires_at: "2030-01-01T00:00:00Z",
  created_at: "2026-10-12T15:00:00Z",
  cancel_requested: false,
  error: null,
  request: {
    source: {
      id: "2".repeat(32),
      source_id: "python_asyncio",
      url: capabilities.sources[0].url,
      title: "asyncio",
      heading: "asyncio",
      excerpt: "Real source excerpt",
      sha256: hash,
      observed_at: "2026-10-12T15:00:00Z",
      version: 1,
    },
    title: "Public example",
    document_name: `fyp-source-${"1".repeat(32)}`,
    content: "# Public example\n",
    destination: "https://stackedit.io/app",
    public_only: true,
    adapter: "stackedit_markdown_v1",
    catalog_version: 1,
    environment_id: hash,
  },
};
const now = Date.parse("2026-10-12T15:01:00Z");

test("browser readiness is fail-closed for missing, stale or unavailable runtime and altered target", () => {
  assert.equal(browserReady(capabilities, true), true);
  assert.equal(browserReady(null, true), false);
  assert.equal(browserReady(capabilities, false), false);
  assert.equal(browserReady({ ...capabilities, ready: false }, true), false);
  assert.equal(
    browserReady({ ...capabilities, configured: false }, true),
    false,
  );
  assert.equal(
    browserReady(
      {
        ...capabilities,
        destination: {
          ...capabilities.destination,
          url: "https://evil.test/app",
        },
      },
      true,
    ),
    false,
  );
  assert.equal(
    browserReady(
      {
        ...capabilities,
        destination: { ...capabilities.destination, id: "generic_desktop" },
      },
      true,
    ),
    false,
  );
});
test("approval requires exact visible intent, current deadline, ready runtime and no cancellation", () => {
  assert.equal(browserReviewable(job, true, now), true);
  assert.equal(browserReviewable(job, false, now), false);
  for (const change of [
    { request: undefined },
    { intent_hash: undefined },
    { intent_hash: "invalid" },
    { cancel_requested: true },
    { expires_at: "invalid" },
    { expires_at: "2020-01-01" },
    { state: "unknown" as const },
  ])
    assert.equal(browserReviewable({ ...job, ...change }, true, now), false);
  assert.equal(
    browserReviewable(
      { ...job, request: { ...job.request!, public_only: false } },
      true,
      now,
    ),
    false,
  );
});
test("an executor state string or click receipt cannot become verified export success", () => {
  assert.equal(browserVerified({ ...job, state: "succeeded" }), false);
  assert.equal(
    browserVerified({ ...job, state: "succeeded", result: { verified: true } }),
    false,
  );
  const success = {
    ...job,
    state: "succeeded" as const,
    cleanup_confirmed: true,
    result: {
      verified: true,
      byte_count: 20,
      sha256: hash,
      process_cleanup_confirmed: true,
      browser_close_confirmed: true,
      export_method: "stackedit_ui_markdown_download",
    },
  };
  assert.equal(browserVerified(success), true);
  for (const change of [
    { process_cleanup_confirmed: false },
    { browser_close_confirmed: false },
    { byte_count: 0 },
    { byte_count: 65537 },
    { sha256: "wrong" },
    { export_method: "generated_file" },
    { verified: false },
  ])
    assert.equal(
      browserVerified({ ...success, result: { ...success.result, ...change } }),
      false,
    );
  assert.equal(browserVerified({ ...success, state: "unknown" }), false);
  assert.equal(
    browserVerified({ ...success, cleanup_confirmed: false }),
    false,
  );
  const uncertainCleanup = {
    ...success,
    state: "unknown" as const,
    cleanup_confirmed: false,
    result: { ...success.result, process_cleanup_confirmed: false },
  };
  assert.equal(browserVerified(uncertainCleanup), false);
  assert.equal(
    browserExportVerified(uncertainCleanup),
    true,
    "verified existing export remains inspectable without repeating browser actions",
  );
});
test("cancel and navigation controls do not imply rollback or discard uncertain requests", () => {
  for (const state of [
    "review",
    "queued",
    "running",
    "verifying",
    "unknown",
  ] as const)
    assert.equal(browserCancellable({ ...job, state }), true);
  for (const state of [
    "cancelled",
    "cancelling",
    "failed",
    "expired",
    "succeeded",
  ] as const)
    assert.equal(browserCancellable({ ...job, state }), false);
  assert.equal(browserCancellable({ ...job, cancel_requested: true }), false);
  assert.equal(browserSelection(null, "a", true, false), "confirm");
  assert.equal(browserSelection("a", "b", false, true), "stay");
  assert.equal(browserSelection("a", "a", true, false), "stay");
  assert.equal(browserSelection("a", null, false, false), "switch");
});
test("only an exact catalog source becomes a source hyperlink", () => {
  assert.equal(
    catalogUrl(capabilities.sources[0].url, capabilities.sources),
    capabilities.sources[0].url,
  );
  for (const url of [
    "javascript:alert(1)",
    "https://evil.test/",
    capabilities.sources[0].url + "?private=1",
    "http://127.0.0.1/",
  ])
    assert.equal(catalogUrl(url, capabilities.sources), null);
});
test("same-ID recovery and independent cancellation remain separate requests", async () => {
  const attempts: { path: string; key: string; serialized: string }[] = [];
  const approval = new PrivateWriteQueue(
    async (request) => {
      attempts.push({ ...request });
      throw { status: 0 };
    },
    () => "approval-id",
  );
  const cancel = new PrivateWriteQueue(
    async (request) => {
      attempts.push({ ...request });
      return { state: "cancelling" };
    },
    () => "cancel-id",
  );
  await assert.rejects(
    approval.send(`/browser/jobs/${job.id}/approve`, {
      expected_version: job.version,
      intent_hash: job.intent_hash,
      public_only: true,
    }),
  );
  assert.equal(approval.pending, true);
  assert.deepEqual(await cancel.send(`/browser/jobs/${job.id}/cancel`, {}), {
    state: "cancelling",
  });
  await assert.rejects(approval.retry());
  assert.equal(attempts[0].key, attempts[2].key);
  assert.equal(attempts[0].serialized, attempts[2].serialized);
  assert.equal(attempts[1].key, "cancel-id");
});
test("privacy, newer selection and owner session changes fence browser observations and exports", () => {
  const fence = new ResponseFence();
  fence.update("owner:session1:jobA", true);
  const token = fence.capture();
  fence.update("owner:session1:jobB", true);
  assert.equal(fence.accepts(token), false);
  fence.update("owner:session1:jobA", true);
  const beforeHide = fence.capture();
  fence.update("owner:session1:jobA", false);
  fence.update("owner:session1:jobA", true);
  assert.equal(fence.accepts(beforeHide), false);
  const beforeSession = fence.capture();
  fence.update("owner:session2:jobA", true);
  assert.equal(fence.accepts(beforeSession), false);
});
const text = "# Public 来源\n\nObserved facts only\n";
const bytes = new TextEncoder().encode(text);
const expected = {
  byte_count: bytes.byteLength,
  sha256: createHash("sha256").update(bytes).digest("hex"),
};
const response = (
  body: BodyInit = text,
  contentType = "text/markdown; charset=utf-8",
) => new Response(body, { headers: { "Content-Type": contentType } });
test("actual UTF-8 export bytes are independently hash checked", async () => {
  assert.deepEqual(
    await verifiedExportBytes(response(), expected, () => true),
    bytes,
  );
  await assert.rejects(
    verifiedExportBytes(response("changed"), expected, () => true),
    { code: "BROWSER_EXPORT_MISMATCH" },
  );
  await assert.rejects(
    verifiedExportBytes(response(), { ...expected, sha256: hash }, () => true),
    { code: "BROWSER_EXPORT_MISMATCH" },
  );
});
test("export rejects executable MIME, excessive streamed bytes and hidden response", async () => {
  await assert.rejects(
    verifiedExportBytes(response(text, "text/html"), expected, () => true),
    { code: "BROWSER_EXPORT_MISMATCH" },
  );
  await assert.rejects(
    verifiedExportBytes(response(new Uint8Array(65537)), expected, () => true),
    { code: "BROWSER_EXPORT_MISMATCH" },
  );
  await assert.rejects(
    verifiedExportBytes(response(), expected, () => false),
    { code: "BROWSER_VIEW_CHANGED" },
  );
});
test("privacy revocation while a download is awaiting bytes cancels its stream", async () => {
  let visible = true,
    cancelled = false;
  let controller!: ReadableStreamDefaultController<Uint8Array>;
  const stream = new ReadableStream<Uint8Array>({
    start(value) {
      controller = value;
    },
    cancel() {
      cancelled = true;
    },
  });
  const checking = verifiedExportBytes(
    response(stream),
    expected,
    () => visible,
  );
  visible = false;
  controller.enqueue(bytes);
  await assert.rejects(checking, { code: "BROWSER_VIEW_CHANGED" });
  assert.equal(cancelled, true);
});
test("browser UI uses volatile mutations, explicit review and plain-text source previews", () => {
  const panel = readFileSync(
    new URL(
      "../src/workspace/browser/BrowserWorkflowPanel.tsx",
      import.meta.url,
    ),
    "utf8",
  );
  const detail = readFileSync(
    new URL("../src/workspace/browser/BrowserJobDetail.tsx", import.meta.url),
    "utf8",
  );
  assert.doesNotMatch(
    panel,
    /localStorage|sessionStorage|\bwrite\s*[<(]|dangerouslySetInnerHTML/,
  );
  assert.match(panel, /const cancelMutation = usePrivateMutation/);
  assert.match(panel, /useDraftGuard/);
  assert.match(panel, /public_only: true/);
  assert.match(
    panel,
    /expected_version: job.version,\s*intent_hash: job.intent_hash/,
  );
  assert.match(detail, /Approve this exact edit and export/);
  assert.match(detail, /Read-only verification/);
  assert.match(
    detail,
    /<pre tabIndex=\{0\}>\s*\{job.request.content\}\s*<\/pre>/,
  );
});
test("public browser observation gets the bounded read timeout without changing other request timeouts", () => {
  const api = readFileSync(new URL("../src/api.ts", import.meta.url), "utf8");
  for (const path of [
    "/assistant/messages",
    "/assistant/retained-messages",
    "/browser/observations",
  ])
    assert.ok(api.includes(`"${path}"`));
  assert.match(api, /\.includes\(path\)\s*\? 75000\s*: 12000/);
  assert.match(api, /controller\.abort\(\)/);
});
