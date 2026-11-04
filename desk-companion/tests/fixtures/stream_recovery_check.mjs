/**
 * Production client check: an interrupted assistant stream stays pending, and
 * recovery reuses that operation through the SSE reader. Parsing the body with
 * JSON would fail and a later new operation would duplicate the draft.
 */
const memory = new Map();
globalThis.sessionStorage = {
  getItem: (key) => memory.get(key) ?? null,
  setItem: (key, value) => memory.set(key, value),
  removeItem: (key) => memory.delete(key),
};
if (!globalThis.window) globalThis.window = globalThis;
window.dispatchEvent ??= () => true;

const keys = [];
let calls = 0;
globalThis.fetch = async (_url, options) => {
  calls += 1;
  keys.push((options.headers ?? {})["X-Operation-Id"]);
  const event =
    calls === 1
      ? { type: "preview", text: "Preparing" }
      : {
          type: "done",
          reply: {
            message: "Review this draft",
            kind: "draft",
            saved: false,
          },
        };
  return new Response(`data: ${JSON.stringify(event)}\n\n`, {
    status: 200,
    headers: { "content-type": "text/event-stream" },
  });
};

const api = await import(
  new URL("../../frontend/src/api.ts", import.meta.url).href
);

let failed = null;
try {
  await api.writeStream(
    "/assistant/messages/stream",
    { message: "Goal: fixture" },
    () => {},
  );
} catch (error) {
  failed = error;
}
if (!failed || failed.code !== "CONNECTION_LOST") {
  console.error("EOF without done was treated as complete", failed);
  process.exit(1);
}
const pending = api.pendingWrite();
if (!pending || pending.path !== "/assistant/messages/stream") {
  console.error("interrupted stream cleared the pending operation", pending);
  process.exit(1);
}
const recovered = await api.retryPending();
if (!recovered || recovered.message !== "Review this draft") {
  console.error("recovery did not read the SSE body", recovered);
  process.exit(1);
}
if (api.pendingWrite() !== null) {
  console.error("completed recovery left the operation pending");
  process.exit(1);
}
if (!keys[0] || keys[0] !== keys[1]) {
  console.error("recovery did not reuse the original operation", keys);
  process.exit(1);
}
console.log("ok");
