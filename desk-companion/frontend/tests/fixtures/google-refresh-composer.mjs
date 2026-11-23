// Invoked by pytest with a connected local HTTP socket and a temporary desk session.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import http from "node:http";
import { createRequire } from "node:module";
import { Socket } from "node:net";
import { Readable } from "node:stream";
import ts from "typescript";
import { Hooks } from "../helpers/hooks.ts";
import { ResponseFence } from "../../src/workspace/personal/responseFence.ts";
import * as transcript from "../../src/workspace/conversationTranscript.ts";

const cookie = readFileSync(0, "utf8");
const agent = new http.Agent({ keepAlive: true, maxSockets: 1 });
agent.createConnection = () => new Socket({ fd: Number(process.argv[2]), readable: true, writable: true });
globalThis.window = Object.assign(new EventTarget(), { setTimeout });
globalThis.document = new EventTarget();
const storage = new Map();
globalThis.sessionStorage = {
  getItem: (k) => storage.get(k) ?? null,
  setItem: (k, v) => storage.set(k, v),
  removeItem: (k) => storage.delete(k),
};
let readback;
globalThis.fetch = async (path, options) => {
  assert.ok(path.startsWith("/api/"));
  if (path === "/api/google/status" && readback) {
    readback.arrived.resolve();
    await readback.release.promise;
  }
  return new Promise((resolve, reject) => {
    const request = http.request({
      host: "localhost", path, agent, method: options.method,
      headers: { ...options.headers, cookie }, signal: options.signal,
    }, (response) => resolve(new Response(Readable.toWeb(response), {
      status: response.statusCode, headers: response.headers,
    })));
    request.on("error", reject);
    request.end(options.body);
  });
};

const api = await import("../../src/api.ts");
const view = { data: await api.request("/workspace"), offline: false, stale: false };
// An Omni-capable owner still types this local question through the HTTP composer.
Object.assign(view.data.voice, { configured: true, supports_text: true });
const hooks = new Hooks();
const noop = () => {};
const files = {
  files: [], sent: noop, clear: noop,
  upload: async (conversationId) => ({ conversationId, references: [], keys: [] }),
};
const commerce = {
  tracked: {}, rows: [], refresh: async () => [], restore: async () => null, clear: noop,
};
const mocks = {
  react: { ...hooks.react, useLayoutEffect: hooks.react.useEffect },
  "../api": api,
  "./WorkspaceContext": { useWorkspace: () => view },
  "./conversationTranscript": transcript,
  "./personal/responseFence": { ResponseFence },
  "./commerceReviews": { useCommerceReviews: () => commerce, needsDecision: () => false },
  "./useChatFiles": { useChatFiles: () => files },
  "./wake/useAliceWake": { useAliceWake: () => ({ pause: noop, rearm: noop, disable: noop }) },
  "../components/DraftGuard": { useDraftGuard: noop },
  "../companion/useAssistantFootprint": { useAssistantFootprint: noop },
  "../companion/interaction": { companionState: noop, reportInteraction: noop, showDelivery: noop },
  "../companion/delivery": { replyDelivery: noop },
};
const source = readFileSync(new URL("../../src/workspace/AssistantPanel.tsx", import.meta.url), "utf8");
const code = ts.transpileModule(source, { compilerOptions: {
  module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX,
} }).outputText;
const require = createRequire(import.meta.url), panel = {};
new Function("require", "exports", code)(
  (name) => mocks[name] ?? (name.startsWith(".") ? {} : require(name)), panel,
);
const t = (_en, zh) => zh;
function nodes(tree) {
  if (Array.isArray(tree)) return tree.flatMap(nodes);
  return tree == null || typeof tree === "boolean" ? [] : [tree, ...nodes(tree.props?.children)];
}
const render = (expanded = false) => nodes(hooks.render(() => panel.AssistantPanel({ t, immersive: true, expanded })));
const question = "刚才我的 Google 日历更新了什么？";
const summary = "Google 日历副本上次于 2026-10-01 00:00 UTC 确认刷新，更新 1 项、移除 1 项、保留 2 项（其中 1 项在 Google 暂不可用，另有 1 项未能核实）。";

async function submit() {
  const textarea = render().find((el) => el.type === "textarea");
  assert.equal(textarea.props.disabled, false);
  textarea.props.onChange({ target: { value: question } });
  const ready = render();
  const send = ready.find((el) => el.props?.["aria-label"] === "发送消息");
  assert.ok(send && !send.props.disabled);
  readback = { arrived: Promise.withResolvers(), release: Promise.withResolvers() };
  const submitted = ready.find((el) => el.type === "form").props.onSubmit({ preventDefault: noop });
  await Promise.race([
    readback.arrived.promise,
    submitted.then(() => { throw Error("Composer ended before the authenticated readback"); }),
  ]);
  return { submitted, release: readback.release.resolve };
}

try {
  const first = await submit();
  assert.ok(!render().includes(summary) && !render(true).includes(summary));
  first.release();
  await first.submitted;
  assert.equal(render().find((el) => el.props?.className === "assistant-latest").props.children, summary);
  const history = render(true);
  assert.equal(history.filter((el) => el.props?.className === "assistant-turn assistant").length, 1);
  assert.equal(history.filter((el) => el === summary).length, 1);
  assert.ok(!history.some((el) => typeof el === "string" && el.includes("Private title")));

  const pending = await submit();
  await api.write("/settings", { expected_version: 1, timezone: "Asia/Hong_Kong", hide_private: true });
  view.data = await api.request("/workspace");
  window.dispatchEvent(new Event("desk:personal-context"));
  assert.ok(!render().includes(summary) && !render(true).includes(summary));
  pending.release();
  await pending.submitted;
  assert.ok(!render().includes(summary) && !render(true).includes(summary));
  assert.equal(render().find((el) => el.type === "textarea").props.disabled, false);
  assert.equal(api.pendingWrite(), null);
  console.log("ok");
} finally {
  hooks.close();
  agent.destroy();
}
