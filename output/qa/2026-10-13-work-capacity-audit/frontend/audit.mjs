// Independent execution of production hooks/callbacks and React SSR. Not DOM/browser evidence.
import fs from "node:fs";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { createHash, webcrypto } from "node:crypto";
const root = process.cwd(),
  out = root + "/output/qa/2026-10-13-work-capacity-audit/frontend";
const req = createRequire(root + "/desk-companion/frontend/package.json"),
  ts = req("typescript");
const src = root + "/desk-companion/frontend/src/";
const sourceHashes = {};
let active;
const react = Object.fromEntries(
  ["useState", "useRef", "useCallback", "useEffect"].map((k) => [
    k,
    (...args) => active[k](...args),
  ]),
);
const jsx = (type, props) => ({ type, props });
const nodes = (x) =>
  !x || typeof x !== "object"
    ? []
    : Array.isArray(x)
      ? x.flatMap(nodes)
      : [x, ...nodes(x.props?.children)];
const text = (x) =>
  typeof x === "string" || typeof x === "number"
    ? String(x)
    : !x || typeof x !== "object"
      ? ""
      : Array.isArray(x)
        ? x.map(text).join("")
        : text(x.props?.children);
const button = (tree, label) =>
  nodes(tree).find((n) => n.type === "button" && text(n) === label);
function load(file, deps = {}, extra = "") {
  const source = fs.readFileSync(src + file, "utf8");
  sourceHashes[file] = createHash("sha256").update(source).digest("hex");
  const exports = {};
  const code = ts.transpileModule(source, {
    fileName: file,
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.CommonJS,
      jsx: ts.JsxEmit.ReactJSX,
    },
  }).outputText;
  new Function("exports", "require", code + "\n" + extra)(exports, (n) =>
    n === "react"
      ? react
      : n === "react/jsx-runtime"
        ? { jsx, jsxs: jsx, Fragment: "Fragment" }
        : n in deps
          ? deps[n]
          : (() => {
              throw Error("Unprovided " + n + " for " + file);
            })(),
  );
  return exports;
}
class Hooks {
  slots = [];
  i = 0;
  effects = [];
  closed = false;
  same(a, b) {
    return (
      !!a && a.length === b.length && a.every((v, i) => Object.is(v, b[i]))
    );
  }
  useState(v) {
    const i = this.i++;
    this.slots[i] ??= { value: typeof v === "function" ? v() : v };
    return [
      this.slots[i].value,
      (v) => {
        if (!this.closed)
          this.slots[i].value =
            typeof v === "function" ? v(this.slots[i].value) : v;
      },
    ];
  }
  useRef(v) {
    const i = this.i++;
    return (this.slots[i] ??= { current: v });
  }
  useCallback(f, d) {
    const i = this.i++;
    if (!this.same(this.slots[i]?.deps, d)) this.slots[i] = { deps: d, f };
    return this.slots[i].f;
  }
  useEffect(f, d) {
    const i = this.i++,
      old = this.slots[i];
    if (this.same(old?.deps, d)) return;
    this.slots[i] = { deps: d };
    this.effects.push(() => {
      old?.cleanup?.();
      this.slots[i].cleanup = f();
    });
  }
  render(fn) {
    active = this;
    this.i = 0;
    const tree = fn();
    this.effects.splice(0).forEach((f) => f());
    return tree;
  }
  close() {
    this.closed = true;
    this.slots.forEach((s) => s.cleanup?.());
  }
}
let intervals = [],
  timeouts = [];
const win = new EventTarget();
win.setInterval = (f, ms) => {
  intervals.push({ f, ms });
  return intervals.length;
};
win.setTimeout = (f, ms) => {
  timeouts.push({ f, ms });
  return timeouts.length;
};
win.confirm = () => true;
Object.assign(globalThis, {
  window: win,
  document: Object.assign(new EventTarget(), { hidden: false }),
});
const settle = () => new Promise((r) => setImmediate(r));
const t = (en) => en;
const { ResponseFence } = load("workspace/personal/responseFence.ts");
const capacityTypes = load("workspace/agent/workCapacity.ts");
const browser = load("workspace/browser/types.ts");
const agentTypes = load("workspace/agent/types.ts", {
  "../browser/types.ts": browser,
});
const capUI = load("workspace/agent/RetainedCapacity.tsx");
const dim = (limit, used = 0) => ({
  limit,
  used,
  remaining: Math.max(0, limit - used),
  state: used > limit ? "over_limit" : "known",
});
const capacity = (used = 0) => ({
  basis: "retained_reservations",
  observed_at: "2026-10-13T07:00:00Z",
  advisory: true,
  sources: {
    count: dim(100, used),
    bytes: dim(67108864, used),
    file_bytes: 1048576,
  },
  artifacts: {
    count: dim(400, 400),
    bytes: dim(67108864, 67108864),
    file_bytes: 262144,
    per_run_count: 4,
    per_run_bytes: 1048576,
  },
  runs: { count: dim(100, 100) },
  watches: { count: dim(20, 20) },
});
const scope = {
  scope_revision: "a".repeat(64),
  modes: ["deterministic", "model"],
  destinations: [],
  sources: [],
  tasks: [
    { id: "task-one", title: "Private task", version: 2 },
    { id: "task-two", title: "Private task two", version: 1 },
  ],
  events: [],
  limits: {},
  business_context_allowed: true,
};
const run = {
  id: "run-one",
  goal: "PRIVATE RUN GOAL",
  state: "running",
  state_reason: null,
  mode: "deterministic",
  version: 2,
  plan_revision: 1,
  created_at: "now",
  updated_at: "now",
  source_ids: [],
  task_ids: ["task-one"],
  event_ids: [],
  artifact_ids: [],
  proposal_ids: [],
  model_calls: 0,
  evidence_count: 0,
  plan: [],
  evidence: [],
};
const detail = {
  run,
  artifacts: [],
  proposals: [],
  browser_jobs: [],
  connector_intents: [],
};
function env() {
  const hooks = new Hooks(),
    calls = [],
    fence = new ResponseFence();
  fence.update("owner:A", true);
  const api = {
    request: (path, options) =>
      new Promise((resolve, reject) =>
        calls.push({ path, options, resolve, reject }),
      ),
    ApiError: class extends Error {},
    errorText: () => "",
  };
  const hook = load("workspace/agent/useWorkCapacity.ts", {
    "../../api": api,
    "../personal/responseFence": { ResponseFence },
    "./workCapacity": capacityTypes,
  });
  const render = () =>
    hooks.render(() => hook.useWorkCapacity(fence, fence.version));
  return { hooks, calls, fence, api, hook, render, close: () => hooks.close() };
}
const results = [];
async function test(name, f) {
  try {
    await f();
    results.push({ name, status: "passed" });
  } catch (e) {
    results.push({ name, status: "failed", error: e.stack });
    console.error(name + "\n" + e.stack);
  }
}
await test("Capacity hook mount/explicit refresh is read-only and adds no timer or provider request", async () => {
  const w = env(),
    before = intervals.length;
  w.render();
  assert.deepEqual(
    w.calls.map((x) => x.path),
    ["/work/capacity"],
  );
  w.calls.shift().resolve(capacity(7));
  await settle();
  for (let i = 0; i < 8; i++) w.render();
  assert.equal(w.calls.length, 0);
  assert.equal(intervals.length, before);
  assert.equal(w.render().value.sources.count.used, 7);
  const p = w.render().refresh();
  assert.deepEqual(
    w.calls.map((x) => x.path),
    ["/work/capacity"],
  );
  w.calls.shift().resolve(capacity(8));
  await p;
  assert.equal(w.render().value.sources.count.used, 8);
  w.close();
});
for (const event of ["desk:session", "desk:personal-context", "offline"])
  await test(
    "Immediate " +
      event +
      " clears counts and refuses late responses/stale refresh callback",
    async () => {
      const w = env();
      w.render();
      const old = w.calls.shift(),
        refresh = w.render().refresh;
      win.dispatchEvent(new Event(event));
      old.resolve(capacity(3));
      await settle();
      assert.equal(w.render().value, null);
      await refresh();
      assert.equal(w.calls.length, 0);
      w.close();
    },
  );
for (const variant of [
  "identity-A-B-A",
  "hide-show",
  "stale-recover",
  "unmount",
])
  await test(
    "Epoch lifecycle " + variant + " cannot resurrect old response",
    async () => {
      const w = env();
      w.render();
      const old = w.calls.shift(),
        refresh = w.render().refresh;
      if (variant === "unmount") {
        w.close();
        old.resolve(capacity(9));
        await settle();
        await refresh();
        assert.equal(w.calls.length, 0);
        return;
      }
      w.fence.update(
        variant === "identity-A-B-A" ? "owner:B" : "owner:A",
        variant === "identity-A-B-A",
      );
      assert.equal(w.render().value, null);
      const middle = w.calls.splice(0);
      w.fence.update("owner:A", true);
      w.render();
      const latest = w.calls.shift();
      for (const x of middle) x.resolve(capacity(2));
      old.resolve(capacity(1));
      await settle();
      assert.equal(w.render().value, null);
      latest.resolve(capacity(7));
      await settle();
      assert.equal(w.render().value.sources.count.used, 7);
      w.close();
    },
  );
await test("Out-of-order same-epoch success and ordinary failure only honor newest request", async () => {
  const w = env();
  w.render();
  const old = w.calls.shift();
  const p = w.render().refresh();
  w.calls.shift().resolve(capacity(9));
  await p;
  old.reject({ status: 503 });
  await settle();
  assert.equal(w.render().value.sources.count.used, 9);
  assert(w.fence.accepts(w.fence.version));
  w.close();
});
for (const denial of [
  { status: 401 },
  { status: 403 },
  { status: 409, code: "WORK_CAPACITY_PRIVACY_CHANGED" },
  { status: 409, code: "CONTEXT_CHANGED" },
  { code: "PRIVATE_CONTEXT_HIDDEN" },
])
  await test(
    "Same-epoch reordered access denial invalidates shared fence " +
      JSON.stringify(denial),
    async () => {
      const w = env();
      w.render();
      const old = w.calls.shift(),
        epoch = w.fence.version;
      const p = w.render().refresh();
      w.calls.shift().resolve(capacity(5));
      await p;
      old.reject(denial);
      await settle();
      assert.equal(w.fence.accepts(epoch), false);
      assert.equal(w.render().value, null);
      w.close();
    },
  );
await test("Denial from an old identity epoch does not revoke new identity capacity", async () => {
  const w = env();
  w.render();
  const old = w.calls.shift();
  w.fence.update("owner:B", true);
  w.render();
  w.calls.shift().resolve(capacity(6));
  await settle();
  old.reject({ status: 403 });
  await settle();
  assert.equal(w.render().value.sources.count.used, 6);
  assert(w.fence.accepts(w.fence.version));
  w.close();
});
for (const failure of [
  { status: 409, code: "WORK_CAPACITY_UNAVAILABLE" },
  { status: 503 },
  { code: "CONNECTION_LOST", status: 0 },
])
  await test(
    "Ordinary failure has unknown capacity without changing shared authority " +
      JSON.stringify(failure),
    async () => {
      const w = env();
      w.render();
      w.calls.shift().resolve(capacity());
      await settle();
      const epoch = w.fence.version,
        p = w.render().refresh();
      w.calls.shift().reject(failure);
      await p;
      assert.equal(w.render().value, null);
      assert.equal(w.render().loading, false);
      assert.equal(w.fence.version, epoch);
      assert(w.fence.accepts(epoch));
      w.close();
    },
  );
await test("Malformed server dimensions cannot show false empty capacity", async () => {
  const w = env();
  w.render();
  let c = capacity();
  c.sources.bytes.used = true;
  w.calls.shift().resolve(c);
  await settle();
  assert.equal(w.render().value, null);
  for (const used of [
    null,
    true,
    "0",
    -1,
    0.1,
    NaN,
    Infinity,
    Number.MAX_SAFE_INTEGER + 1,
  ]) {
    c = capacity();
    c.runs.count.used = used;
    assert.equal(capacityTypes.validWorkCapacity(c), false);
  }
  assert(
    capacityTypes.validCapacityDimension({
      limit: 100,
      used: null,
      remaining: null,
      state: "over_limit",
    }),
  );
  assert(
    capacityTypes.validCapacityDimension({
      limit: 100,
      used: null,
      remaining: null,
      state: "unavailable",
    }),
  );
  w.close();
});
function workspace() {
  const w = env();
  const runs = load("workspace/agent/useAgentRuns.ts", { "../../api": w.api });
  const handlers = [];
  let state = {
    data: {
      principal: { kind: "owner", id: "owner" },
      personal_context_visible: true,
      voice: { config_revision: 1 },
    },
    offline: false,
    stale: false,
  };
  const module = load(
    "workspace/agent/RunPanel.tsx",
    {
      "../../native": { apiOrigin: () => "" },
      "../../components/Dialogs": { Modal: "Modal" },
      "../../components/DraftGuard": {
        useDraftState: () => ({ busy: false, dirty: false }),
      },
      "../WorkspaceContext": { useWorkspace: () => state },
      "../personal/responseFence": { ResponseFence },
      "./labels": {
        agentError: () => "",
        modeLabel: (x) => x,
        stateLabel: (x) => x,
      },
      "./RunComposer": { RunComposer: "RunComposer" },
      "./RunDetail": { RunDetail: "RunDetail" },
      "./RunMetadataPanel": { RunMetadataPanel: "RunMetadataPanel" },
      "./runMetadata": load("workspace/agent/runMetadata.ts"),
      "./types": agentTypes,
      "./useAgentRuns": runs,
      "./WorkSearchPanel": { WorkSearchPanel: "WorkSearchPanel" },
      "./useWorkCapacity": w.hook,
      "./RetainedCapacity": { WorkCapacitySummary: "WorkCapacitySummary" },
      "./agent.css": {},
    },
    "exports.auditWorkspace=RunWorkspace;",
  );
  const props = {
    t,
    fence: w.fence,
    epoch: w.fence.version,
    onReviewProposal: (id) => handlers.push(["proposal", id]),
    onReviewBrowserJob: (id) => handlers.push(["browser", id]),
    onReviewConnectorIntent: (id) => handlers.push(["connector", id]),
  };
  const render = () => w.hooks.render(() => module.auditWorkspace(props));
  const resolve = () => {
    for (const call of w.calls.splice(0))
      call.resolve(
        call.path === "/work/capacity"
          ? capacity(100)
          : call.path === "/agent-runs"
            ? { runs: [run] }
            : call.path === "/agent-runs/scope"
              ? scope
              : detail,
      );
  };
  return {
    ...w,
    module,
    props,
    handlers,
    render,
    resolve,
    changeState: (v) => (state = v),
  };
}
await test("Actual Work workspace capacity failure preserves scope/composer and stop/inspect eligibility", async () => {
  const w = workspace();
  w.render();
  w.resolve();
  await settle();
  let tree = w.render();
  assert.equal(button(tree, "Start persistent work").props.disabled, false);
  button(tree, "Start persistent work").props.onClick();
  tree = w.render();
  let composer = nodes(tree).find((n) => n.type === "RunComposer");
  assert.equal(composer.props.scope, scope);
  assert.equal(composer.props.fresh, true);
  const key = composer.props.key;
  nodes(tree)
    .find((n) => n.type === "WorkCapacitySummary")
    .props.refresh();
  assert.deepEqual(
    w.calls.map((c) => c.path),
    ["/work/capacity"],
  );
  w.calls.shift().reject({ status: 503 });
  await settle();
  tree = w.render();
  composer = nodes(tree).find((n) => n.type === "RunComposer");
  assert.equal(composer.props.scope, scope);
  assert.equal(composer.props.key, key);
  assert.equal(composer.props.fresh, true);
  assert.equal(composer.props.capacity, null);
  w.close();
});
await test("Actual Work workspace capacity denial masks retained private views on next render", async () => {
  const w = workspace();
  w.render();
  w.resolve();
  await settle();
  let tree = w.render();
  nodes(tree)
    .find(
      (n) => n.type === "button" && n.props.className === "agent-run-choice",
    )
    .props.onClick();
  w.render();
  w.resolve();
  await settle();
  tree = w.render();
  assert(nodes(tree).find((n) => n.type === "RunDetail"));
  nodes(tree)
    .find((n) => n.type === "WorkCapacitySummary")
    .props.refresh();
  w.calls.shift().reject({ status: 403, code: "PRIVATE_CONTEXT_HIDDEN" });
  await settle();
  tree = w.render();
  assert(!text(tree).includes("PRIVATE RUN GOAL"));
  assert(!nodes(tree).find((n) => n.type === "RunDetail"));
  assert(!nodes(tree).find((n) => n.type === "RunComposer"));
  assert(button(tree, "Start persistent work").props.disabled);
  w.close();
});
await test("Access denial also revokes previously rendered linked-review callbacks immediately", async () => {
  const w = workspace();
  w.render();
  w.resolve();
  await settle();
  nodes(w.render())
    .find(
      (n) => n.type === "button" && n.props.className === "agent-run-choice",
    )
    .props.onClick();
  w.render();
  w.resolve();
  await settle();
  const tree = w.render(),
    child = nodes(tree).find((n) => n.type === "RunDetail");
  nodes(tree)
    .find((n) => n.type === "WorkCapacitySummary")
    .props.refresh();
  w.calls.shift().reject({ status: 403, code: "PRIVATE_CONTEXT_HIDDEN" });
  await settle();
  child.props.onReviewProposal("private-proposal");
  child.props.onReviewBrowserJob("private-browser-job");
  child.props.onReviewConnectorIntent("private-connector");
  assert.deepEqual(
    w.handlers,
    [],
    "Old private callbacks survived capacity access denial",
  );
  w.close();
});
function real(x) {
  if (!x || typeof x !== "object") return x;
  if (Array.isArray(x))
    return x.map((v, i) => {
      const node = real(v);
      return React.isValidElement(node)
        ? React.cloneElement(node, { key: i })
        : node;
    });
  if (typeof x.type === "function") return real(x.type(x.props));
  return React.createElement(x.type === "Fragment" ? React.Fragment : x.type, {
    ...x.props,
    children: real(x.props?.children),
  });
}
const React = req("react"),
  server = req("react-dom/server");
await test("Actual bilingual SSR renders full/unavailable/over-limit and per-run limits without usage claim", () => {
  for (const zh of [false, true]) {
    const tr = (en, cn) => (zh ? cn : en);
    const full = server.renderToStaticMarkup(
      real(capUI.WorkCapacitySummary({ value: capacity(100), t: tr })),
    );
    assert.match(full, /100\/100/);
    assert.match(full, zh ? /无剩余额度/ : /No remaining capacity/);
    assert.match(full, zh ? /不会释放容量/ : /does not free capacity/);
    assert.match(full, zh ? /并非磁盘/ : /not disk usage/);
    assert.doesNotMatch(full, /<meter|<progress|disabled=/);
    fs.writeFileSync(
      out + "/capacity-full-" + (zh ? "zh" : "en") + ".html",
      full,
    );
    const absent = server.renderToStaticMarkup(
      real(capUI.WorkCapacitySummary({ value: null, t: tr })),
    );
    assert.match(absent, zh ? /容量不可用/ : /Capacity unavailable/);
    assert.doesNotMatch(absent, /0\/|NaN|null/);
    const c = capacity();
    c.sources.count = {
      limit: 100,
      used: null,
      remaining: null,
      state: "over_limit",
    };
    c.sources.bytes = {
      limit: 67108864,
      used: null,
      remaining: null,
      state: "unavailable",
    };
    const odd = server.renderToStaticMarkup(
      real(capUI.WorkCapacitySummary({ value: c, t: tr })),
    );
    assert.match(odd, zh ? /已超上限/ : /Over limit/);
    assert.doesNotMatch(odd, /NaN|null/);
    const hint = server.renderToStaticMarkup(
      real(
        capUI.OutputCapacityHint({
          value: capacity(),
          t: tr,
          deterministic: true,
        }),
      ),
    );
    assert.match(hint, zh ? /并非当前运行用量/ : /not current per-run usage/);
    assert.match(hint, zh ? /不足两个/ : /fewer than two/);
    assert.match(
      hint,
      zh ? /同一操作仍可重试/ : /Existing-operation retries remain available/,
    );
    assert.doesNotMatch(hint, /disabled=/);
  }
});
const queue = load("workspace/personal/privateWrite.ts");
function composerWorld(voice = false) {
  const w = env();
  let cap = capacity(100),
    now = Date.now();
  const origin = voice
    ? {
        voice_origin_ref: "origin-one",
        expires_at: new Date(now + 60000).toISOString(),
        provider: "fixture",
        input_ids: ["input-one"],
        reviewed: true,
      }
    : undefined;
  const mutation = load("workspace/personal/usePrivateMutation.ts", {
    "../../api": w.api,
    "./privateWrite": queue,
  });
  const deps = {
    "../voiceWork/VoiceWorkPanel": { VoiceOriginLabel: "VoiceOriginLabel" },
    "../../components/Dialogs": { Modal: "Modal" },
    "../../components/DraftGuard": { useDraftGuard() {} },
    "../personal/usePrivateMutation": mutation,
    "./labels": { modeLabel: (x) => x },
    "./types": agentTypes,
    "./RetainedCapacity": { OutputCapacityHint: "OutputCapacityHint" },
  };
  for (const name of [
    "RequestFeedback",
    "SourceUpload",
    "SourcePreview",
    "RunBrowserSelection",
    "RunConnectorSelection",
    "RunContextSelection",
  ])
    deps["./" + name] = { [name]: name };
  const { RunComposer } = load("workspace/agent/RunComposer.tsx", deps);
  const props = {
    t,
    scope,
    fence: w.fence,
    fresh: true,
    capacity: cap,
    initialGoal: "Compile the exact tasks",
    ...(voice
      ? { voiceOrigin: origin }
      : { exactTaskIds: ["task-one", "task-two"] }),
    onClose() {},
    onCreated() {},
    onRefresh() {},
  };
  const render = () =>
    w.hooks.render(() => RunComposer({ ...props, capacity: cap }));
  const selectAndReview = () => {
    render();
    let tree = render();
    if (voice) {
      const label = nodes(tree).find(
        (n) =>
          n.type === "label" &&
          text(n).includes("Private task") &&
          !text(n).includes("two"),
      );
      nodes(label)
        .find((n) => n.type === "input")
        .props.onChange({ target: { checked: true } });
      tree = render();
    }
    const retention = nodes(tree).find(
      (n) => n.type === "label" && text(n).startsWith("Retain this goal"),
    );
    nodes(retention)
      .find((n) => n.type === "input")
      .props.onChange({ target: { checked: true } });
    tree = render();
    nodes(tree)
      .find((n) => n.type === "form")
      .props.onSubmit({ preventDefault() {} });
    return render();
  };
  return {
    ...w,
    render,
    selectAndReview,
    props,
    origin,
    setCap: (v) => (cap = v),
  };
}
await test("Actual composer exact watched IDs and retention survive full/missing capacity without scope reset", async () => {
  const w = composerWorld();
  let tree = w.selectAndReview();
  const start = button(tree, "Start this persistent work");
  assert(!start.props.disabled);
  w.setCap(null);
  tree = w.render();
  assert(!nodes(tree).some((n) => n.type === "form"));
  assert(!button(tree, "Start this persistent work").props.disabled);
  w.setCap(capacity(100));
  tree = w.render();
  button(tree, "Start this persistent work").props.onClick();
  await settle();
  const call = w.calls.shift();
  assert.deepEqual(JSON.parse(call.options.body).task_ids, [
    "task-one",
    "task-two",
  ]);
  assert.equal(
    JSON.parse(call.options.body).scope_revision,
    scope.scope_revision,
  );
  assert.equal(JSON.parse(call.options.body).voice_origin_ref, undefined);
  assert.equal(JSON.parse(call.options.body).provider_destination_id, null);
  call.resolve({ run });
  await settle();
  w.close();
});
await test("Actual voice-origin unknown mutation survives capacity changes and expiry with same exact retry", async () => {
  const w = composerWorld(true),
    originalNow = Date.now;
  try {
    let tree = w.selectAndReview();
    button(tree, "Start this persistent work").props.onClick();
    await settle();
    const first = w.calls.shift();
    assert.equal(JSON.parse(first.options.body).voice_origin_ref, "origin-one");
    first.reject({ status: 0, code: "CONNECTION_LOST" });
    await settle();
    w.setCap(null);
    tree = w.render();
    const feedback = nodes(tree).find((n) => n.type === "RequestFeedback");
    assert.equal(feedback.props.mutation.pending, true);
    assert.equal(feedback.props.mutation.busy, false);
    Date.now = () => Date.parse(w.origin.expires_at) + 1;
    const p = feedback.props.mutation.retry();
    const retry = w.calls.shift();
    assert.equal(retry.path, first.path);
    assert.equal(retry.options.body, first.options.body);
    assert.equal(
      retry.options.headers["X-Operation-Id"],
      first.options.headers["X-Operation-Id"],
    );
    assert.equal(JSON.parse(retry.options.body).voice_origin_ref, "origin-one");
    retry.resolve({ run });
    await p;
    w.setCap(capacity(100));
    tree = w.render();
    const before = w.calls.length;
    button(tree, "Start this persistent work").props.onClick();
    await settle();
    assert.equal(
      w.calls.length,
      before,
      "Expired voice must not fall back to new typed operation",
    );
  } finally {
    Date.now = originalNow;
    w.close();
  }
});
await test("Composer saved start/retry callbacks reject confirmed capacity access revocation", async () => {
  const w = composerWorld();
  let tree = w.selectAndReview(),
    start = button(tree, "Start this persistent work").props.onClick;
  w.fence.update("denied", false);
  start();
  await settle();
  assert.equal(w.calls.length, 0);
  w.close();
});
await test("Production upload draft consent and unknown retry stay intact at full and unavailable capacity", async () => {
  const w = env();
  let cap = capacity(100),
    reads = 0;
  const upload = load("workspace/agent/upload.ts", {
      "./types.ts": agentTypes,
    }),
    mutation = load("workspace/agent/useUploadMutation.ts", {
      "../../api": w.api,
      "../personal/privateWrite": queue,
      "./upload": upload,
    });
  const { SourceUpload } = load("workspace/agent/SourceUpload.tsx", {
    "./RetainedCapacity": { ...capUI, CapacityLine: "CapacityLine" },
    "../../api": w.api,
    "../../components/DraftGuard": { useDraftGuard() {} },
    "./labels": { agentError: () => "" },
    "./RequestFeedback": { RequestFeedback: "RequestFeedback" },
    "./upload": upload,
    "./useUploadMutation": mutation,
  });
  const render = () =>
    w.hooks.render(() =>
      SourceUpload({
        t,
        fence: w.fence,
        fresh: true,
        capacity: cap,
        onUploaded() {},
        onDraftChange() {},
      }),
    );
  let tree = render();
  nodes(tree)
    .find((n) => n.props?.type === "file")
    .props.onChange({
      target: {
        files: [
          {
            name: "source.txt",
            size: 4,
            arrayBuffer: async () => {
              reads++;
              return new TextEncoder().encode("data").buffer;
            },
          },
        ],
      },
    });
  tree = render();
  nodes(tree)
    .find((n) => n.props?.type === "checkbox")
    .props.onChange({ target: { checked: true } });
  cap = null;
  tree = render();
  assert(nodes(tree).find((n) => n.props?.type === "checkbox").props.checked);
  assert(!button(tree, "Upload selected source").props.disabled);
  assert.equal(reads, 0);
  button(tree, "Upload selected source").props.onClick();
  await settle();
  const first = w.calls.shift();
  assert.equal(first.options.body, "data");
  first.reject({ status: 0, code: "CONNECTION_LOST" });
  await settle();
  cap = capacity(100);
  tree = render();
  let feedback = nodes(tree).find((n) => n.type === "RequestFeedback");
  assert(feedback.props.mutation.pending);
  assert(!feedback.props.mutation.busy);
  const retry = feedback.props.mutation.retry(),
    second = w.calls.shift();
  assert.equal(second.path, first.path);
  assert.equal(second.options.body, first.options.body);
  assert.equal(
    second.options.headers["X-Operation-Id"],
    first.options.headers["X-Operation-Id"],
  );
  assert.equal(
    reads,
    1,
    "Retry must use original exact body, not reread/reselect",
  );
  second.resolve({ source: { id: "source-one" } });
  await retry;
  w.close();
});
await test("Actual RunDetail pause/cancel original-operation retry remains usable at full global capacity", async () => {
  const w = env();
  const mutation = load("workspace/personal/usePrivateMutation.ts", {
    "../../api": w.api,
    "./privateWrite": queue,
  });
  const deps = {
    "../voiceWork/VoiceWorkPanel": { VoiceOriginLabel: "VoiceOriginLabel" },
    "../../components/DraftGuard": { useDraftGuard() {} },
    "../personal/usePrivateMutation": mutation,
    "./labels": {
      blockLabel: (x) => x,
      modeLabel: (x) => x,
      stateLabel: (x) => x,
    },
    "./types": agentTypes,
  };
  for (const name of [
    "ArtifactList",
    "RunBrowserJobs",
    "RunConnectorResults",
    "RequestFeedback",
  ])
    deps["./" + name] = { [name]: name };
  const { RunDetail } = load("workspace/agent/RunDetail.tsx", deps);
  const render = () =>
    w.hooks.render(() =>
      RunDetail({
        detail: { ...detail, steps: [], events: [] },
        t,
        fence: w.fence,
        fresh: true,
        onChanged() {},
      }),
    );
  let tree = render();
  assert(!button(tree, "Pause").props.disabled);
  assert(!button(tree, "Cancel work").props.disabled);
  button(tree, "Pause").props.onClick();
  tree = render();
  button(tree, "Apply to this version").props.onClick();
  await settle();
  let first = w.calls.shift();
  assert.equal(JSON.parse(first.options.body).action, "pause");
  first.reject({ status: 0, code: "CONNECTION_LOST" });
  await settle();
  tree = render();
  assert(
    !button(tree, "Cancel work").props.disabled,
    "Unknown pause must not disable independent cancellation",
  );
  button(tree, "Cancel work").props.onClick();
  tree = render();
  button(tree, "Confirm cancellation").props.onClick();
  await settle();
  let cancel = w.calls.shift();
  assert.equal(JSON.parse(cancel.options.body).action, "cancel");
  cancel.resolve({});
  await settle();
  tree = render();
  const pending = nodes(tree).find(
    (n) => n.type === "RequestFeedback" && n.props.mutation.pending,
  );
  const replay = pending.props.mutation.retry(),
    second = w.calls.shift();
  assert.equal(second.options.body, first.options.body);
  assert.equal(
    second.options.headers["X-Operation-Id"],
    first.options.headers["X-Operation-Id"],
  );
  second.resolve({});
  await replay;
  w.close();
});
await test("Production artifact preview and byte-verified download execute with no capacity gate", async () => {
  const w = env(),
    bytes = new TextEncoder().encode("saved output"),
    downloads = [],
    fetches = [];
  let exported;
  const exportDone = new Promise((resolve) => (exported = resolve));
  const artifact = {
    id: "artifact-one",
    display_name: "Synthetic report",
    format: "text",
    byte_count: bytes.byteLength,
    sha256: createHash("sha256").update(bytes).digest("hex"),
    status: "verified",
    verification: "byte_readback",
    authorship: "deterministic",
    provenance: [],
  };
  const { ArtifactList } = load("workspace/agent/ArtifactList.tsx", {
    "../../api": w.api,
    "../../native": {
      isNative: true,
      native: {
        exportFile: async (x) => {
          downloads.push(x);
          exported();
        },
      },
      apiFetch: async (path) => {
        fetches.push(path);
        return { ok: true, arrayBuffer: async () => bytes.buffer };
      },
    },
    "./labels": { agentError: () => "" },
    "./types": agentTypes,
  });
  const render = () =>
    w.hooks.render(() =>
      ArtifactList({ artifacts: [artifact], t, fence: w.fence }),
    );
  let tree = render();
  assert(!button(tree, "Preview text").props.disabled);
  assert(!button(tree, "Download file").props.disabled);
  button(tree, "Preview text").props.onClick();
  w.calls
    .shift()
    .resolve({ artifact, content: "saved output", truncated: false });
  await settle();
  assert(text(render()).includes("saved output"));
  button(render(), "Download file").props.onClick();
  let deadline;
  try {
    await Promise.race([
      exportDone,
      new Promise((_, reject) => {
        deadline = setTimeout(
          () => reject(Error("Fixture download did not complete")),
          2000,
        );
      }),
    ]);
  } finally {
    clearTimeout(deadline);
  }
  assert.deepEqual(fetches, ["/artifacts/artifact-one/download"]);
  assert.equal(downloads.length, 1);
  assert.equal(
    Buffer.from(downloads[0].bodyBase64, "base64").toString(),
    "saved output",
  );
  w.close();
});

await test("Latest collapsed native summary exposes full/unknown/over-limit warnings before expansion", () => {
  for (const [kind, label] of [
    ["full", "No remaining capacity"],
    ["unknown", "Capacity unavailable"],
    ["over", "Over limit"],
  ]) {
    const value = kind === "unknown" ? null : capacity(100);
    if (kind === "over")
      value.sources.count = {
        limit: 100,
        used: null,
        remaining: null,
        state: "over_limit",
      };
    const tree = capUI.WorkCapacitySummary({ value, t });
    assert.equal(tree.type, "details");
    assert.equal(tree.props.open, undefined);
    const summary = nodes(tree).find((n) => n.type === "summary");
    assert(text(summary).includes(label));
    assert(text(summary).includes("Saved work storage"));
  }
  assert.equal(capUI.capacityBytes(67108864, t), "64 MiB");
  assert.equal(capUI.capacityBytes(1024, t), "1 KiB");
  assert.equal(capUI.capacityBytes(1030, t), "1.01 KiB (1030 bytes)");
});
await test("Actual Work entry uses owner/visible-only capacity workspace; hidden owner preserves metadata controls", () => {
  const w = workspace(),
    h = new Hooks();
  const render = () => h.render(() => w.module.RunPanel({ t }));
  render();
  let tree = render();
  button(tree, "Work tasks").props.onClick();
  tree = render();
  assert(
    nodes(tree).some(
      (n) => typeof n.type === "function" && n.type.name === "RunWorkspace",
    ),
  );
  for (const [kind, hidden, offline, stale, allowed] of [
    ["owner", true, false, false, true],
    ["paired", false, false, false, false],
    ["display", false, false, false, false],
    ["device-agent", false, false, false, false],
    ["owner", false, true, false, false],
    ["owner", false, false, true, false],
  ]) {
    w.changeState({
      data: {
        principal: { kind, id: kind },
        personal_context_visible: !hidden,
        voice: { config_revision: 1 },
      },
      offline,
      stale,
    });
    render();
    tree = render();
    assert.equal(button(tree, "Work tasks").props.disabled, !allowed);
    if (allowed) {
      button(tree, "Work tasks").props.onClick();
      tree = render();
      assert(nodes(tree).some((n) => n.type === "RunMetadataPanel"));
      assert(
        !nodes(tree).some(
          (n) => typeof n.type === "function" && n.type.name === "RunWorkspace",
        ),
      );
    }
  }
  assert.equal(w.calls.length, 0);
  h.close();
  w.close();
});
for (const hidden of [false, true])
  await test(
    "Watch " +
      (hidden ? "hidden metadata" : "visible") +
      " saved count and cancellation do not depend on capacity endpoint",
    async () => {
      const w = env();
      const watchTypes = load("workspace/responsibilities/types.ts");
      const runs = load("workspace/agent/useAgentRuns.ts", {
        "../../api": w.api,
      });
      const hook = load("workspace/responsibilities/useResponsibilities.ts", {
        "../../api": w.api,
        "../agent/useAgentRuns": runs,
        "./types": watchTypes,
      });
      const mutation = load("workspace/personal/usePrivateMutation.ts", {
        "../../api": w.api,
        "./privateWrite": queue,
      });
      const labels = load("workspace/responsibilities/labels.ts", {
        "../../api": w.api,
      });
      const { WatchWorkspace } = load(
        "workspace/responsibilities/ResponsibilitiesPanel.tsx",
        {
          "../../native": { apiOrigin: () => "" },
          "../../components/Dialogs": { Modal: "Modal" },
          "../../components/DraftGuard": { useDraftGuard() {} },
          "../WorkspaceContext": {},
          "../personal/responseFence": { ResponseFence },
          "../personal/usePrivateMutation": mutation,
          "./labels": labels,
          "./types": watchTypes,
          "./useResponsibilities": hook,
          "./WatchReviewCard": { WatchReviewCard: "WatchReviewCard" },
          "./CurrentTask": { CurrentTask: "CurrentTask" },
          "./responsibilities.css": {},
        },
      );
      let row = {
        id: "watch-one",
        title: "PRIVATE WATCH",
        version: 1,
        generation: 1,
        status: "active",
        created_at: "now",
        updated_at: "now",
        baseline_at: "now",
        expires_at: "later",
        review_budget: 20,
        reviews_used: 0,
        daily_review_budget: 10,
        budget_day: "2026-10-13",
        daily_used: 0,
        blocked_code: null,
        pending_count: 0,
        hidden,
        task_ids: ["task-one"],
        fields: ["status"],
      };
      const list = () => ({
        responsibilities: [row],
        pending_count: 0,
        hidden,
        revision: 1,
        server_time: "now",
        limits: { definitions: 20 },
      });
      const render = () =>
        w.hooks.render(() =>
          WatchWorkspace({
            t,
            fence: w.fence,
            epoch: w.fence.version,
            hidden,
            onCompile() {},
          }),
        );
      const resolve = () => {
        for (const c of w.calls.splice(0)) {
          assert.notEqual(c.path, "/work/capacity");
          c.resolve(
            c.path === "/responsibilities"
              ? list()
              : {
                  tasks: scope.tasks,
                  selected_task_ids: [],
                  fields: [],
                  scope_revision: null,
                  server_time: "now",
                  limits: {},
                  truncated: false,
                },
          );
        }
      };
      render();
      assert.deepEqual(
        w.calls.map((c) => c.path),
        hidden
          ? ["/responsibilities"]
          : ["/responsibilities", "/responsibilities/scope"],
      );
      resolve();
      await settle();
      let tree = render();
      assert.match(text(tree), /Saved definitions: 1\/20/);
      assert.match(text(tree), /19 slots remaining/);
      assert.match(text(tree), /Cancelled, expired and budget-exhausted/);
      if (hidden) assert(!text(tree).includes("PRIVATE WATCH"));
      const cancel = nodes(tree).find(
        (n) => n.type === "button" && text(n) === "Cancel watch",
      );
      assert(cancel && !cancel.props.disabled);
      cancel.props.onClick();
      tree = render();
      button(tree, "Confirm control").props.onClick();
      await settle();
      const call = w.calls.shift();
      assert.equal(JSON.parse(call.options.body).action, "cancel");
      row = { ...row, status: "cancelled", version: 2 };
      call.resolve({});
      await settle();
      resolve();
      await settle();
      tree = render();
      assert.match(text(tree), /Saved definitions: 1\/20/);
      assert.match(text(tree), /19 slots remaining/);
      w.close();
    },
  );

fs.writeFileSync(
  out + "/results.json",
  JSON.stringify(
    {
      at: new Date().toISOString(),
      method:
        "Independent production hook/callback execution and React SSR, no browser DOM",
      results,
      sourceHashes,
    },
    null,
    2,
  ),
);
console.log(
  JSON.stringify(
    {
      passed: results.filter((r) => r.status === "passed").length,
      failed: results.filter((r) => r.status === "failed"),
    },
    null,
    2,
  ),
);
if (results.some((r) => r.status === "failed")) process.exitCode = 1;
