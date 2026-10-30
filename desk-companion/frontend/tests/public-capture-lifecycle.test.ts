import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import ts from "typescript";
import { ResponseFence } from "../src/workspace/personal/responseFence.ts";
import * as policy from "../src/workspace/agent/capturePolicy.ts";
class HookHarness {
  slots: any[] = [];
  index = 0;
  effects: (() => void)[] = [];
  react = {
    useState: (initial: any) => {
      const n = this.index++;
      this.slots[n] ??= {
        value: typeof initial === "function" ? initial() : initial,
      };
      return [
        this.slots[n].value,
        (next: any) => {
          this.slots[n].value =
            typeof next === "function" ? next(this.slots[n].value) : next;
        },
      ];
    },
    useRef: (value: any) => {
      const n = this.index++;
      this.slots[n] ??= { current: value };
      return this.slots[n];
    },
    useCallback: (callback: any, deps: any[]) => {
      const n = this.index++;
      if (!this.equal(this.slots[n]?.deps, deps))
        this.slots[n] = { deps, callback };
      return this.slots[n].callback;
    },
    useEffect: (effect: () => void | (() => void), deps: any[]) => {
      const n = this.index++;
      if (this.equal(this.slots[n]?.deps, deps)) return;
      const old = this.slots[n];
      this.slots[n] = { deps };
      this.effects.push(() => {
        old?.cleanup?.();
        this.slots[n].cleanup = effect();
      });
    },
  };
  equal(a: any[] | undefined, b: any[]) {
    return (
      !!a && a.length === b.length && a.every((v, i) => Object.is(v, b[i]))
    );
  }
  render<T>(body: () => T): T {
    this.index = 0;
    const result = body();
    this.effects.splice(0).forEach((effect) => effect());
    return result;
  }
  close() {
    this.slots.forEach((slot) => slot.cleanup?.());
  }
}
function compile(file: string, resolve: (name: string) => any) {
  const exports: any = {};
  const code = ts.transpileModule(
    readFileSync(new URL(file, import.meta.url), "utf8"),
    {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS,
        target: ts.ScriptTarget.ES2022,
        jsx: ts.JsxEmit.ReactJSX,
      },
    },
  ).outputText;
  new Function("require", "exports", code)(resolve, exports);
  return exports;
}
const id = "a".repeat(32),
  hash = "b".repeat(64),
  url = "https://www.python.org/about/";
const time = "2026-10-13T09:00:00Z";
const capture = (extra: any = {}) => ({
  id,
  state: "review",
  version: 1,
  created_at: time,
  updated_at: time,
  expires_at: "2099-10-13T09:05:00Z",
  dispatch_possible: false,
  error_code: null,
  cancel_available: true,
  url,
  label: null,
  display_name: `capture-${id}.txt`,
  intent_hash: hash,
  source_id: null,
  source_status: "not_reserved",
  acquisition: null,
  ...extra,
});
const dimension = (limit: number) => ({
  limit,
  used: 0,
  remaining: limit,
  state: "known",
});
const review = (c = capture()) => ({
  ...c,
  capture_id: c.id,
  host: "www.python.org",
  destination: c.url,
  retain_capture_record: true,
  intent_version: 1,
  disclosure_version: 1,
  method: "GET",
  public_only: true,
  credentials: "none",
  redirects: "deny",
  policy_version: 1,
  extractor_version: "static_text_v1",
  retention: "local_indefinite_no_delete_control",
  raw_retention: "none",
  source_capacity: {
    count: dimension(100),
    bytes: dimension(67108864),
    file_bytes: 262144,
  },
  history_used: 1,
  history_limit: 200,
  observed_at: time,
  advisory: true,
  untrusted: true,
  starts_work: false,
  grants_model_sharing: false,
});
const metadata = (c = capture()) =>
  Object.fromEntries(
    [
      "id",
      "state",
      "version",
      "created_at",
      "updated_at",
      "expires_at",
      "dispatch_possible",
      "error_code",
      "cancel_available",
    ].map((k) => [k, c[k]]),
  );
class ApiError extends Error {
  code: string;
  status: number;
  constructor(code: string, status = 0) {
    super(code);
    this.code = code;
    this.status = status;
  }
}
const tick = () => new Promise((resolve) => setImmediate(resolve));
function setup(hidden = false, freshInitially = true) {
  const hooks = new HookHarness(),
    events = new EventTarget(),
    pending: any[] = [];
  const previous = Object.getOwnPropertyDescriptor(globalThis, "window");
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: events,
  });
  const mod = compile("../src/workspace/agent/usePublicCaptures.ts", (name) => {
    if (name === "react") return hooks.react;
    if (name === "../../api")
      return {
        ApiError,
        request: (path: string, options: any) =>
          new Promise((resolve, reject) =>
            pending.push({ path, options, resolve, reject }),
          ),
      };
    if (name.endsWith("responseFence")) return { ResponseFence };
    if (name === "./capturePolicy") return policy;
    throw Error(name);
  });
  const fence = new ResponseFence();
  fence.update("owner", true);
  let fresh = freshInitially;
  const render = () =>
    hooks.render(() =>
      mod.usePublicCaptures(fence, fence.version, fresh, hidden),
    );
  return {
    hooks,
    events,
    pending,
    fence,
    render,
    setFresh: (v: boolean) => {
      fresh = v;
    },
    close() {
      hooks.close();
      if (previous) Object.defineProperty(globalThis, "window", previous);
      else Reflect.deleteProperty(globalThis, "window");
    },
  };
}
async function ready(h: ReturnType<typeof setup>, enabled = true) {
  h.render();
  assert.equal(h.pending[0].path, "/public-research/capabilities");
  h.pending
    .shift()
    .resolve({ enabled, history_limit: 200, source_cleanup: false });
  await tick();
  return h.render();
}
async function prepared(h: ReturnType<typeof setup>) {
  const promise = h.render().prepare(url, "", true);
  const req = h.pending.shift();
  req.resolve({
    capture: capture(),
    review: review(),
    operation_id: req.options.headers["X-Operation-Id"],
  });
  assert.equal(await promise, true);
  return h.render();
}
test("capability defaults off, initial stale mount can recover capability, no automatic list or network mutation", async () => {
  const h = setup(false, false);
  try {
    await ready(h);
    assert.equal(h.render().enabled, false);
    h.setFresh(true);
    assert.equal(h.render().enabled, true);
    assert.equal(h.pending.length, 0);
  } finally {
    h.close();
  }
});
test("disabled capture allows saved history reads but never preparation", async () => {
  const h = setup();
  try {
    let api = await ready(h, false);
    assert.equal(await api.prepare(url, "", true), false);
    const read = api.read();
    assert.match(h.pending[0].path, /metadata_only=false/);
    h.pending.shift().resolve({ captures: [], next_cursor: null });
    await read;
    assert.equal(h.pending.length, 0);
  } finally {
    h.close();
  }
});
test("prepare stores exact review and separate approval uses strict acknowledgments and double click lock", async () => {
  const h = setup();
  try {
    await ready(h);
    assert.equal(await h.render().prepare(url, "", false), false);
    let api = await prepared(h);
    assert.equal(api.selected.url, url);
    assert.equal(await api.approve(api.review, false, true), false);
    const approve = api.approve(api.review, true, true);
    assert.equal(await api.approve(api.review, true, true), false);
    assert.equal(h.pending.length, 1);
    const req = h.pending.shift();
    assert.deepEqual(JSON.parse(req.options.body), {
      expected_version: 1,
      intent_hash: hash,
      public_only: true,
      retain_snapshot: true,
    });
    req.resolve({
      capture: capture({ state: "queued", version: 2 }),
      operation_id: req.options.headers["X-Operation-Id"],
    });
    await approve;
    api = h.render();
    assert.equal(api.selected.state, "queued");
    assert.equal(api.review, null);
    assert.equal(api.pending.length, 0);
    assert.equal(h.pending.length, 0);
  } finally {
    h.close();
  }
});
test("lost prepare response pins identical body key and only explicit retry recovers original", async () => {
  const h = setup();
  try {
    await ready(h);
    const promise = h.render().prepare(url, "", true);
    const req = h.pending.shift();
    req.reject(new ApiError("CONNECTION_LOST"));
    assert.equal(await promise, false);
    let api = h.render();
    assert.equal(api.pending.length, 1);
    assert.equal(await api.prepare(url, "other", true), false);
    assert.equal(h.pending.length, 0);
    const retry = api.retry(api.pending[0]);
    const second = h.pending.shift();
    assert.deepEqual(second.options, req.options);
    second.resolve({
      capture: capture(),
      review: review(),
      operation_id: second.options.headers["X-Operation-Id"],
    });
    await retry;
    assert.equal(h.render().selected.id, id);
  } finally {
    h.close();
  }
});
test("unknown approval can be stopped without generating a replacement capture, preserving original key", async () => {
  const h = setup();
  try {
    await ready(h);
    let api = await prepared(h);
    const a = api.approve(api.review, true, true);
    h.pending.shift().reject(new ApiError("CONNECTION_LOST"));
    await a;
    api = h.render();
    const original = api.pending[0];
    const stop = api.stop(api.selected);
    const req = h.pending.shift();
    req.resolve({
      capture: metadata(
        capture({ state: "cancelled", version: 3, cancel_available: false }),
      ),
      operation_id: req.options.headers["X-Operation-Id"],
    });
    await tick();
    assert.match(h.pending[0].path, /metadata_only=false/);
    h.pending.shift().resolve({
      capture: capture({
        state: "cancelled",
        version: 3,
        cancel_available: false,
      }),
    });
    await stop;
    api = h.render();
    assert.equal(api.selected.state, "cancelled");
    assert.equal(api.pending[0], original);
    assert.equal(h.pending.length, 0);
  } finally {
    h.close();
  }
});
test("hidden uses scalar list/detail/stop only, rejects leaked private keys and cannot prepare reconcile or approve", async () => {
  const h = setup(true);
  try {
    await ready(h);
    assert.equal(await h.render().prepare(url, "", true), false);
    let p = h.render().read();
    assert.match(h.pending[0].path, /metadata_only=true/);
    h.pending.shift().resolve({ captures: [capture()], next_cursor: null });
    await p;
    assert.equal(h.render().records.length, 0);
    p = h.render().read(id);
    h.pending.shift().resolve({ capture: metadata() });
    await p;
    let api = h.render();
    assert.equal(await api.reconcile(api.selected), false);
    assert.equal(await api.approve(review(), true, true), false);
    p = api.stop(api.selected);
    const req = h.pending.shift();
    req.resolve({
      capture: metadata(
        capture({ state: "cancelled", version: 2, cancel_available: false }),
      ),
      operation_id: req.options.headers["X-Operation-Id"],
    });
    await p;
    assert.equal(h.pending.length, 0);
    assert.equal(h.render().selected.url, undefined);
  } finally {
    h.close();
  }
});
test("all session privacy offline events revoke old callbacks pending retries and late response", async () => {
  for (const event of ["desk:session", "desk:personal-context", "offline"]) {
    const h = setup();
    try {
      await ready(h);
      const api = await prepared(h);
      const a = api.approve(api.review, true, true);
      const req = h.pending.shift();
      h.events.dispatchEvent(new Event(event));
      req.resolve({
        capture: capture({ state: "queued", version: 2 }),
        operation_id: req.options.headers["X-Operation-Id"],
      });
      await a;
      assert.equal(h.render().selected, null);
      assert.equal(await api.prepare(url, "", true), false);
      assert.equal(await api.approve(api.review, true, true), false);
      assert.equal(h.pending.length, 0);
    } finally {
      h.close();
    }
  }
});
test("stale freshness pauses mutation and retries without discarding original unknown request", async () => {
  const h = setup();
  try {
    await ready(h);
    const p = h.render().prepare(url, "", true);
    h.pending.shift().reject(new ApiError("CONNECTION_LOST"));
    await p;
    const api = h.render(),
      operation = api.pending[0];
    h.setFresh(false);
    h.render();
    assert.equal(await api.retry(operation), false);
    assert.equal(h.pending.length, 0);
    h.setFresh(true);
    assert.equal(h.render().pending[0], operation);
  } finally {
    h.close();
  }
});
test("old read access denial revokes newer view", async () => {
  for (const denial of [
    { status: 401 },
    { status: 403 },
    { code: "CAPTURE_PRIVACY_CHANGED" },
  ]) {
    const h = setup();
    try {
      await ready(h);
      const p1 = h.render().read(id),
        old = h.pending.shift();
      const p2 = h.render().read(id);
      h.pending.shift().resolve({ capture: capture(), review: review() });
      await p2;
      assert.ok(h.render().selected);
      old.reject(denial);
      await p1;
      assert.equal(h.fence.accepts(h.fence.version), false);
      assert.equal(h.render().selected, null);
    } finally {
      h.close();
    }
  }
});
test("unmount and A-B-A privacy epochs never revive old callbacks or replies", async () => {
  const h = setup();
  try {
    await ready(h);
    const api = await prepared(h);
    const p = api.read(id),
      req = h.pending.shift();
    h.fence.update("hidden", false);
    h.fence.update("owner", true);
    req.resolve({ capture: capture(), review: review() });
    await p;
    assert.equal(await api.approve(api.review, true, true), false);
    h.hooks.close();
    assert.equal(await api.read(id), false);
    assert.equal(h.pending.length, 0);
  } finally {
    h.close();
  }
});
test("refresh immediately invalidates approval callback; malformed mutation response preserves original pending", async () => {
  const h = setup();
  try {
    await ready(h);
    const api = await prepared(h);
    const read = api.read(id);
    assert.equal(await api.approve(api.review, true, true), false);
    h.pending.shift().resolve({ capture: capture(), review: review() });
    await read;
    const current = h.render();
    const p = current.approve(current.review, true, true);
    const req = h.pending.shift();
    req.resolve({
      capture: capture({ id: "c".repeat(32), state: "queued", version: 2 }),
      operation_id: req.options.headers["X-Operation-Id"],
    });
    await p;
    assert.equal(h.render().pending.length, 1);
  } finally {
    h.close();
  }
});
test("strict parser rejects malformed scalar policy capacity and hidden projections", () => {
  assert.equal(policy.validPublicCapture(capture(), false), true);
  assert.equal(policy.validCaptureReview(review(), capture()), true);
  for (const v of [true, 0, "1", NaN, Infinity, 1.5])
    assert.equal(
      policy.validPublicCapture(capture({ version: v }), false),
      false,
    );
  for (const key of [
    "method",
    "credentials",
    "redirects",
    "retention",
    "policy_version",
    "starts_work",
    "grants_model_sharing",
    "destination",
    "disclosure_version",
  ]) {
    assert.equal(
      policy.validCaptureReview({ ...review(), [key]: "unsafe" }, capture()),
      false,
    );
  }
  assert.equal(policy.validPublicCapture(capture(), true), false);
  assert.equal(policy.validCaptureReview(undefined, metadata() as any), false);
  assert.equal(
    policy.validCaptureReview(
      { id, version: 1, state: "review" },
      metadata() as any,
    ),
    false,
  );
  assert.equal(
    policy.validPublicCapture(capture({ source_status: "verified" }), false),
    false,
  );
});
const jsx = (type: any, props: any) => ({ type, props });
const nodes = (v: any): any[] =>
  !v || typeof v !== "object"
    ? []
    : Array.isArray(v)
      ? v.flatMap(nodes)
      : [v, ...nodes(v.props?.children)];
test("production intake callbacks retain volatile draft, require record acknowledgment and register dirty navigation", async () => {
  const hooks = new HookHarness(),
    events = new EventTarget();
  const previous = Object.getOwnPropertyDescriptor(globalThis, "window");
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: events,
  });
  const fence = new ResponseFence();
  fence.update("owner", true);
  const calls: any[] = [],
    guards: any[] = [];
  let fresh = true;
  const api = {
    enabled: true,
    available: true,
    busy: false,
    error: null,
    records: [capture()],
    cursor: null,
    selected: null,
    review: null,
    pending: [],
    prepare: async (...args: any[]) => {
      calls.push(args);
      return true;
    },
    read: async (...args: any[]) => {
      calls.push(args);
    },
  };
  const mod = compile("../src/workspace/agent/PublicCapture.tsx", (name) => {
    if (name === "react") return hooks.react;
    if (name === "react/jsx-runtime") return { jsx, jsxs: jsx };
    if (name === "./usePublicCaptures") return { usePublicCaptures: () => api };
    if (name === "../../components/DraftGuard")
      return { useDraftGuard: (...args: any[]) => guards.push(args) };
    if (name === "./capturePolicy") return policy;
    if (name === "./RetainedCapacity") return { CapacityLine: () => null };
    if (name === "./SourcePreview") return { SourcePreview: () => null };
    if (name === "./CaptureProvenance")
      return { CaptureProvenance: () => null };
    throw Error(name);
  });
  const render = () =>
    hooks.render(() =>
      mod.PublicCapture({
        t: (en: string) => en,
        fence,
        epoch: fence.version,
        fresh,
      }),
    );
  const button = (tree: any, label: string) =>
    nodes(tree).find((n) => n.type === "button" && n.props.children === label);
  try {
    let tree = render();
    nodes(tree)
      .find((n) => n.type === "input" && n.props.type === "text")
      .props.onChange({ target: { value: url } });
    tree = render();
    assert.equal(guards.at(-1)[0], true);
    assert.equal(
      button(tree, "Save local review · no GET").props.disabled,
      true,
    );
    button(tree, "Reopen").props.onClick();
    tree = render();
    assert.equal(calls.length, 0);
    assert.ok(nodes(tree).some((n) => n.props?.role === "alert"));
    nodes(tree)
      .find((n) => n.props?.type === "checkbox")
      .props.onChange({ target: { checked: true } });
    tree = render();
    const save = button(tree, "Save local review · no GET");
    assert.equal(save.props.disabled, false);
    fresh = false;
    render();
    await save.props.onClick();
    await tick();
    assert.equal(calls.length, 0);
    fresh = true;
    tree = render();
    button(tree, "Save local review · no GET").props.onClick();
    await tick();
    tree = render();
    assert.deepEqual(calls, [[url, "", true]]);
    assert.equal(guards.at(-1)[0], false);
    const old = button(tree, "List retained captures").props.onClick;
    hooks.close();
    old();
    assert.equal(calls.length, 1);
  } finally {
    hooks.close();
    if (previous) Object.defineProperty(globalThis, "window", previous);
    else Reflect.deleteProperty(globalThis, "window");
  }
});

test("production rollback below review observation must prevent approve POST", async () => {
  const h = setup();
  const original = Date.now;
  try {
    await ready(h);
    Date.now = () => Date.parse(time) + 1000;
    const c = capture({
      expires_at: new Date(Date.parse(time) + 300000).toISOString(),
    });
    const p = h.render().prepare(url, "", true),
      req = h.pending.shift();
    req.resolve({
      capture: c,
      review: review(c),
      operation_id: req.options.headers["X-Operation-Id"],
    });
    await p;
    const api = h.render();
    Date.now = () => Date.parse(time) - 1000;
    const promise = api.approve(api.review, true, true);
    assert.equal(
      h.pending.length,
      0,
      "clock rollback must not dispatch approval",
    );
    assert.equal(await promise, false);
  } finally {
    Date.now = original;
    h.close();
  }
});
test("production source preview stale access denial revokes a newer visible page", async () => {
  const hooks = new HookHarness(),
    pending: any[] = [];
  const fence = new ResponseFence();
  fence.update("owner", true);
  const source = {
    id,
    name: "synthetic.txt",
    sha256: hash,
    format: "text",
    byte_count: 2000,
    revision: 1,
    status: "verified",
    provenance_kind: "public_web_snapshot",
  };
  const mod = compile("../src/workspace/agent/SourcePreview.tsx", (name) => {
    if (name === "react") return hooks.react;
    if (name === "react/jsx-runtime") return { jsx, jsxs: jsx };
    if (name === "../../api")
      return {
        request: (path: string) =>
          new Promise((resolve, reject) =>
            pending.push({ path, resolve, reject }),
          ),
      };
    if (name === "../../components/Dialogs") return { Modal: "modal" };
    if (name === "./labels") return { agentError: () => "error" };
    if (name === "./capturePolicy") return policy;
    if (name === "./CaptureProvenance")
      return { CaptureProvenance: "provenance" };
    throw Error(name);
  });
  const render = () =>
    hooks.render(() =>
      mod.SourcePreview({
        source,
        t: (en: string) => en,
        fence,
        onClose: () => {},
      }),
    );
  const response = (start = 1) => ({
    id,
    name: source.name,
    content: "private retained synthetic content",
    start_line: start,
    end_line: start + 199,
    total_lines: 1000,
    truncated: true,
    sha256: hash,
    revision: 1,
  });
  try {
    render();
    pending.shift().resolve(response());
    await tick();
    let tree = render();
    nodes(tree)
      .find((n) => n.type === "button" && n.props.children === "Next lines")
      .props.onClick();
    render();
    const older = pending.shift();
    // Return to page one while the page-two request is outstanding using captured page-one callback.
    nodes(tree)
      .find((n) => n.type === "button" && n.props.children === "First lines")
      .props.onClick();
    render();
    pending.shift().resolve(response());
    await tick();
    render();
    older.reject({ status: 403, code: "OWNER_REQUIRED" });
    await tick();
    assert.equal(
      fence.accepts(fence.version),
      false,
      "stale denial must revoke current preview authority",
    );
  } finally {
    hooks.close();
  }
});
test("production disabled still reconciles and stops; queued refresh never posts approval", async () => {
  const h = setup();
  try {
    await ready(h, false);
    let p = h.render().read(id);
    h.pending
      .shift()
      .resolve({ capture: capture({ state: "queued", version: 2 }) });
    await p;
    let api = h.render();
    assert.equal(await api.approve(review(), true, true), false);
    p = api.reconcile(api.selected);
    let req = h.pending.shift();
    assert.match(req.path, /\/reconcile$/);
    req.resolve({
      capture: capture({ state: "queued", version: 2 }),
      verification: "no_final_source",
      operation_id: req.options.headers["X-Operation-Id"],
    });
    await p;
    p = h.render().read(id);
    req = h.pending.shift();
    assert.equal(req.options, undefined);
    req.resolve({ capture: capture({ state: "queued", version: 2 }) });
    await p;
    api = h.render();
    p = api.stop(api.selected);
    req = h.pending.shift();
    req.resolve({
      capture: metadata(
        capture({ state: "cancelled", version: 3, cancel_available: false }),
      ),
      operation_id: req.options.headers["X-Operation-Id"],
    });
    await tick();
    req = h.pending.shift();
    assert.equal(req.options, undefined);
    req.resolve({
      capture: capture({
        state: "cancelled",
        version: 3,
        cancel_available: false,
      }),
    });
    await p;
    assert.equal(h.pending.length, 0);
  } finally {
    h.close();
  }
});
test("production visible stop rejects private extra response and privacy change blocks followup read", async () => {
  for (const revoke of [false, true]) {
    const h = setup();
    try {
      await ready(h);
      let api = await prepared(h);
      const p = api.stop(api.selected),
        req = h.pending.shift();
      if (revoke) h.events.dispatchEvent(new Event("desk:personal-context"));
      req.resolve({
        capture: revoke
          ? metadata(
              capture({
                state: "cancelled",
                version: 2,
                cancel_available: false,
              }),
            )
          : capture({
              state: "cancelled",
              version: 2,
              cancel_available: false,
            }),
        operation_id: req.options.headers["X-Operation-Id"],
      });
      assert.equal(await p, false);
      assert.equal(h.pending.length, 0);
      api = h.render();
      assert.equal(api.pending.length, revoke ? 0 : 1);
    } finally {
      h.close();
    }
  }
});
test("production monotonic elapsed expires approval with frozen wall clock", async () => {
  const h = setup();
  const wall = Date.now;
  const desc = Object.getOwnPropertyDescriptor(performance, "now");
  let mono = 1000;
  Object.defineProperty(performance, "now", {
    configurable: true,
    value: () => mono,
  });
  try {
    Date.now = () => Date.parse(time) + 1000;
    await ready(h);
    const c = capture({
      expires_at: new Date(Date.now() + 300000).toISOString(),
    });
    const p = h.render().prepare(url, "", true),
      req = h.pending.shift();
    req.resolve({
      capture: c,
      review: review(c),
      operation_id: req.options.headers["X-Operation-Id"],
    });
    await p;
    const api = h.render();
    mono += 300001;
    const a = api.approve(api.review, true, true);
    assert.equal(
      h.pending.length,
      0,
      "elapsed monotonic deadline must block POST",
    );
    assert.equal(await a, false);
  } finally {
    Date.now = wall;
    if (desc) Object.defineProperty(performance, "now", desc);
    else Reflect.deleteProperty(performance, "now");
    h.close();
  }
});
test("review window independently expires on monotonic time and never revives after clock rollback", () => {
  const expires = new Date(301000).toISOString();
  const monotonic = new policy.CaptureReviewWindow(expires, 1000, 500);
  assert.equal(monotonic.remaining(1000, 300501), 0);
  assert.equal(monotonic.remaining(1000, 500), 0);
  const rollback = new policy.CaptureReviewWindow(expires, 1000, 500);
  assert.equal(rollback.remaining(999, 501), 0);
  assert.equal(rollback.remaining(1000, 502), 0);
  const capped = new policy.CaptureReviewWindow(
    "2099-01-01T00:00:00Z",
    1000,
    500,
  );
  assert.equal(capped.remaining(1000, 500), 300000);
});
test("same review reread cannot renew a revoked deadline", async () => {
  const h = setup(),
    original = Date.now;
  try {
    await ready(h);
    const initial = Date.parse(time) + 1000;
    Date.now = () => initial;
    let api = await prepared(h);
    Date.now = () => initial - 1;
    assert.equal(await api.approve(api.review, true, true), false);
    Date.now = () => initial + 1000;
    const p = h.render().read(id);
    h.pending.shift().resolve({ capture: capture(), review: review() });
    await p;
    api = h.render();
    assert.equal(api.reviewReady, false);
    assert.equal(await api.approve(api.review, true, true), false);
    assert.equal(h.pending.length, 0);
  } finally {
    Date.now = original;
    h.close();
  }
});
