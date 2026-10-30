import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import ts from "typescript";
import { ResponseFence } from "../src/workspace/personal/responseFence.ts";
import * as capacityTypes from "../src/workspace/agent/workCapacity.ts";
// Executed production hooks/callbacks with deterministic hook slots; not a browser DOM.
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
const dimension = (used = 0) => ({
  limit: 7,
  used,
  remaining: 7 - used,
  state: "known",
});
const response = (used = 0) => ({
  basis: "retained_reservations",
  observed_at: "2026-10-13T07:00:00Z",
  advisory: true,
  sources: { count: dimension(used), bytes: dimension(), file_bytes: 3 },
  artifacts: {
    count: dimension(),
    bytes: dimension(),
    file_bytes: 3,
    per_run_count: 2,
    per_run_bytes: 6,
  },
  runs: { count: dimension() },
  watches: { count: dimension() },
});
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
function setup(visible = true) {
  const hooks = new HookHarness(),
    events = new EventTarget();
  const previous = Object.getOwnPropertyDescriptor(globalThis, "window");
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: events,
  });
  const pending: any[] = [];
  const mod = compile("../src/workspace/agent/useWorkCapacity.ts", (name) => {
    if (name === "react") return hooks.react;
    if (name === "../../api")
      return {
        request: (path: string) =>
          new Promise((resolve, reject) =>
            pending.push({ path, resolve, reject }),
          ),
      };
    if (name.endsWith("responseFence")) return { ResponseFence };
    if (name === "./workCapacity") return capacityTypes;
    throw new Error(name);
  });
  const fence = new ResponseFence();
  fence.update("owner", visible);
  const render = () =>
    hooks.render(() => mod.useWorkCapacity(fence, fence.version));
  return {
    hooks,
    events,
    pending,
    fence,
    render,
    close() {
      hooks.close();
      if (previous) Object.defineProperty(globalThis, "window", previous);
      else Reflect.deleteProperty(globalThis, "window");
    },
  };
}
const tick = () => new Promise((resolve) => setImmediate(resolve));
test("one opening reads only capacity; explicit refresh is independent and last request wins", async () => {
  const h = setup();
  try {
    h.render();
    assert.deepEqual(
      h.pending.map((x) => x.path),
      ["/work/capacity"],
    );
    const first = h.pending.shift();
    h.render();
    assert.equal(h.pending.length, 0);
    const refresh = h.render().refresh();
    h.pending.shift().resolve(response(5));
    await refresh;
    first.resolve(response(1));
    await tick();
    assert.equal(h.render().value.sources.count.used, 5);
    const fail = h.render().refresh();
    h.pending.shift().reject(new Error("unavailable"));
    await fail;
    assert.equal(h.render().value, null);
    assert.equal(h.render().loading, false);
    assert.equal(h.pending.length, 0);
  } finally {
    h.close();
  }
});
test("all privacy/session/offline events fence before rerender and old callbacks cannot request", async () => {
  for (const event of ["desk:session", "desk:personal-context", "offline"]) {
    const h = setup();
    try {
      h.render();
      const callback = h.render().refresh;
      const old = h.pending.shift();
      h.events.dispatchEvent(new Event(event));
      old.resolve(response());
      await tick();
      assert.equal(h.render().value, null);
      await callback();
      assert.equal(h.pending.length, 0);
    } finally {
      h.close();
    }
  }
});
test("hidden mount, stale and A-B-A epochs, plus unmount reject late observations", async () => {
  const hidden = setup(false);
  hidden.render();
  assert.equal(hidden.pending.length, 0);
  hidden.close();
  const h = setup();
  try {
    h.render();
    const old = h.pending.shift();
    h.fence.update("owner", false);
    assert.equal(h.render().value, null);
    assert.equal(h.pending.length, 0);
    h.fence.update("owner", true);
    h.render();
    const current = h.pending.shift();
    old.resolve(response(1));
    await tick();
    assert.equal(h.render().value, null);
    current.resolve(response(4));
    await tick();
    assert.equal(h.render().value.sources.count.used, 4);
    const callback = h.render().refresh;
    const promise = callback();
    const late = h.pending.shift();
    h.hooks.close();
    late.resolve(response(2));
    await promise;
    assert.equal(h.render().value, null);
    await callback();
    assert.equal(h.pending.length, 0);
  } finally {
    h.close();
  }
});
test("malformed dimensions never turn unknown into empty or partial capacity", () => {
  assert.equal(capacityTypes.validWorkCapacity(response()), true);
  for (const used of [
    true,
    "0",
    -1,
    NaN,
    Infinity,
    0.5,
    Number.MAX_SAFE_INTEGER + 1,
    null,
  ]) {
    const value = response();
    (value.sources.count as any).used = used;
    assert.equal(capacityTypes.validWorkCapacity(value), false);
  }
  for (const value of [
    { limit: 7, used: null, remaining: null, state: "unavailable" },
    { limit: 7, used: null, remaining: null, state: "over_limit" },
    { limit: 7, used: 8, remaining: 0, state: "over_limit" },
  ])
    assert.equal(capacityTypes.validCapacityDimension(value), true);
  assert.equal(
    capacityTypes.validCapacityDimension({
      limit: 7,
      used: null,
      remaining: 0,
      state: "unavailable",
    }),
    false,
  );
});
const jsx = (type: any, props: any) => ({ type, props });
const nodes = (tree: any): any[] =>
  !tree || typeof tree !== "object"
    ? []
    : Array.isArray(tree)
      ? tree.flatMap(nodes)
      : [tree, ...nodes(tree.props?.children)];
test("production upload callbacks preserve selected draft and consent through capacity full/unavailable", async () => {
  const hooks = new HookHarness(),
    calls: any[] = [];
  let capacity: any = response(7);
  const fence = new ResponseFence();
  fence.update("owner", true);
  const mutation = {
    busy: false,
    pending: false,
    error: null,
    run: async (...args: any[]) => {
      calls.push(args);
    },
    retry: async () => false,
  };
  const mod = compile("../src/workspace/agent/SourceUpload.tsx", (name) => {
    if (name === "react") return hooks.react;
    if (name === "react/jsx-runtime") return { jsx, jsxs: jsx };
    if (name === "./useUploadMutation")
      return { useUploadMutation: () => mutation };
    if (name === "../../components/DraftGuard")
      return { useDraftGuard: () => {} };
    if (name === "./upload")
      return {
        readSourceFile: async () => ({
          path: "/sources",
          body: { operation_id: "original" },
        }),
      };
    if (name === "./labels") return { agentError: () => "error" };
    if (name === "../../api") return { ApiError: Error };
    if (name === "./RetainedCapacity")
      return {
        CapacityLine: () => null,
        capacityBytes: (n: number) => String(n),
      };
    if (name === "./RequestFeedback") return { RequestFeedback: () => null };
    throw new Error(name);
  });
  const render = () =>
    hooks.render(() =>
      mod.SourceUpload({
        t: (en: string) => en,
        fence,
        fresh: true,
        capacity,
        onUploaded: () => {},
        onDraftChange: () => {},
      }),
    );
  let tree = render();
  nodes(tree)
    .find((n) => n.props?.type === "file")
    .props.onChange({ target: { files: [{ name: "file.txt", size: 3 }] } });
  tree = render();
  nodes(tree)
    .find((n) => n.props?.type === "checkbox")
    .props.onChange({ target: { checked: true } });
  tree = render();
  capacity = null;
  tree = render();
  assert.equal(
    nodes(tree).find((n) => n.props?.type === "checkbox").props.checked,
    true,
  );
  let button = nodes(tree).find(
    (n) => n.type === "button" && n.props.children === "Upload selected source",
  );
  assert.equal(button.props.disabled, false);
  capacity = response(7);
  tree = render();
  button = nodes(tree).find(
    (n) => n.type === "button" && n.props.children === "Upload selected source",
  );
  assert.equal(button.props.disabled, false);
  button.props.onClick();
  await tick();
  assert.equal(calls.length, 1);
  assert.equal(calls[0][1].operation_id, "original");
  hooks.close();
});
test("actual access denial fences all shared private views, including reordered denial; ordinary failure does not", async () => {
  for (const error of [
    { status: 401 },
    { status: 403 },
    { code: "WORK_CAPACITY_PRIVACY_CHANGED" },
    { code: "PRIVATE_CONTEXT_HIDDEN" },
  ]) {
    const h = setup();
    try {
      h.render();
      const old = h.pending.shift();
      const refresh = h.render().refresh();
      h.pending.shift().resolve(response(3));
      await refresh;
      assert.ok(h.render().value);
      old.reject(error);
      await tick();
      assert.equal(h.fence.accepts(h.fence.version), false);
      assert.equal(h.render().value, null);
    } finally {
      h.close();
    }
  }
  const h = setup();
  try {
    h.render();
    h.pending
      .shift()
      .reject({ status: 409, code: "WORK_CAPACITY_UNAVAILABLE" });
    await tick();
    assert.equal(h.fence.accepts(h.fence.version), true);
    assert.equal(h.render().value, null);
  } finally {
    h.close();
  }
});
