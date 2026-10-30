import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import ts from "typescript";
import { ResponseFence } from "../src/workspace/personal/responseFence.ts";

// Execute the production hook with deterministic hook slots and deferred reads.
// This exercises asynchronous state transitions, not a mounted browser UI.
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
function setup() {
  const previous = ["window", "document"].map(
    (key) => [key, Object.getOwnPropertyDescriptor(globalThis, key)] as const,
  );
  const events = { addEventListener() {}, removeEventListener() {} };
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: { ...events, setInterval: () => 1 },
  });
  Object.defineProperty(globalThis, "document", {
    configurable: true,
    value: { ...events, hidden: false },
  });
  const pending: {
    path: string;
    resolve: (value: unknown) => void;
    reject: (value: unknown) => void;
  }[] = [];
  const hooks = new HookHarness();
  const module = { exports: {} as any };
  const source = readFileSync(
    new URL("../src/workspace/agent/useAgentRuns.ts", import.meta.url),
    "utf8",
  );
  const compiled = ts.transpileModule(source, {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.CommonJS,
    },
  }).outputText;
  new Function("require", "exports", compiled)((name: string) => {
    if (name === "react") return hooks.react;
    if (name === "../../api")
      return {
        request: (path: string) =>
          new Promise((resolve, reject) =>
            pending.push({ path, resolve, reject }),
          ),
      };
    throw new Error(`Unexpected import ${name}`);
  }, module.exports);
  const fence = new ResponseFence();
  fence.update("owner:one:private", true);
  let selected: string | null = "run-one";
  const render = () =>
    hooks.render(() =>
      module.exports.useAgentRuns(fence, selected, fence.version),
    );
  const settle = async (failure?: unknown) => {
    const batch = pending.splice(0);
    for (const item of batch) {
      if (failure && item.path === "/agent-runs/scope") item.reject(failure);
      else
        item.resolve(
          item.path === "/agent-runs"
            ? { runs: [{ id: "run-one", goal: "Private draft" }] }
            : item.path === "/agent-runs/scope"
              ? { scope_revision: "scope-one" }
              : { run: { id: selected, version: 1 } },
        );
    }
    await new Promise((resolve) => setImmediate(resolve));
    return render();
  };
  return {
    render,
    settle,
    pending,
    fence,
    choose: (id: string | null) => {
      selected = id;
    },
    recoverable: module.exports.recoverableRunReadError,
    close() {
      hooks.close();
      for (const [key, descriptor] of previous) {
        if (descriptor) Object.defineProperty(globalThis, key, descriptor);
        else Reflect.deleteProperty(globalThis, key);
      }
    },
  };
}

test("transient refresh keeps exact snapshot mounted but stale until successful refresh", async () => {
  const h = setup();
  try {
    h.render();
    let state = await h.settle();
    const retained = state.value;
    assert.equal(state.fresh, true);
    const refresh = state.reload(true);
    state = await h.settle({ code: "CONNECTION_LOST", status: 0 });
    await refresh;
    assert.strictEqual(state.value, retained);
    assert.equal(state.fresh, false);
    assert.equal(
      !!state.value.scope,
      true,
      "RunComposer mounting condition remains true",
    );
    assert.equal(
      !!state.value.detail,
      true,
      "RunDetail mounting condition remains true",
    );
    const recovery = state.reload(true);
    state = await h.settle();
    await recovery;
    assert.equal(state.fresh, true);
    assert.equal(state.error, null);
  } finally {
    h.close();
  }
});

test("auth, privacy, missing-resource and unexpected failures clear instead of retaining", async () => {
  for (const failure of [
    { code: "AUTH_REQUIRED", status: 401 },
    { code: "PRIVATE_CONTEXT_HIDDEN", status: 403 },
    { code: "RUN_NOT_FOUND", status: 404 },
    { code: "PRIVATE_CONTEXT_HIDDEN", status: 503 },
    new Error("invalid response shape"),
  ]) {
    const h = setup();
    try {
      h.render();
      let state = await h.settle();
      const refresh = state.reload(true);
      state = await h.settle(failure);
      await refresh;
      assert.equal(state.value, null);
      assert.equal(state.fresh, false);
    } finally {
      h.close();
    }
  }
});

test("parallel late privacy denial still clears after first transient failure", async () => {
  const h = setup();
  try {
    h.render();
    const state = await h.settle();
    const refresh = state.reload(true);
    const batch = h.pending.splice(0);
    batch
      .find((item) => item.path === "/agent-runs")!
      .reject({ code: "CONNECTION_LOST", status: 0 });
    await refresh;
    assert.ok(h.render().value);
    batch
      .find((item) => item.path === "/agent-runs/scope")!
      .reject({ code: "PRIVATE_CONTEXT_HIDDEN", status: 403 });
    batch
      .find((item) => item.path.endsWith("/run-one"))!
      .resolve({ run: { id: "run-one" } });
    await new Promise((resolve) => setImmediate(resolve));
    assert.equal(h.render().value, null);
    assert.equal(h.render().error.code, "PRIVATE_CONTEXT_HIDDEN");
  } finally {
    h.close();
  }
});

test("selection and privacy epoch changes hide cached content before late reads settle", async () => {
  const h = setup();
  try {
    h.render();
    let state = await h.settle();
    const old = state.reload(true);
    h.choose("run-two");
    assert.equal(h.render().value, null);
    await h.settle();
    await old;
    state = h.render();
    assert.equal(state.value.selected, "run-two");
    h.fence.update("owner:one:private", false);
    state = h.render();
    assert.equal(state.value, null);
    assert.equal(state.fresh, false);
  } finally {
    h.close();
  }
});

test("retention is allowlisted and stale UI gates include retries, handoffs and delayed uploads", () => {
  const h = setup();
  try {
    for (const status of [408, 429, 500, 502, 503, 504])
      assert.equal(h.recoverable({ code: "REQUEST_FAILED", status }), true);
    for (const status of [0, 400, 401, 403, 404, 409, 422, 501])
      assert.equal(h.recoverable({ code: "REQUEST_FAILED", status }), false);
  } finally {
    h.close();
  }
  const file = (name: string) =>
    readFileSync(
      new URL(`../src/workspace/agent/${name}`, import.meta.url),
      "utf8",
    );
  assert.match(
    file("RunPanel.tsx"),
    /if \(!fresh\) return;\s*if \(!validWorkGoal/,
  );
  assert.match(file("RunPanel.tsx"), /fresh=\{fresh\}/);
  assert.match(file("RunDetail.tsx"), /fresh && fence.accepts\(viewEpoch\)/);
  assert.match(
    file("RunDetail.tsx"),
    /locked=\{!fresh \|\| mutation.busy \|\| cancellation.busy\}/,
  );
  assert.match(file("RunComposer.tsx"), /if \(!fresh \|\| !review/);
  assert.match(file("RunComposer.tsx"), /fresh && fence.accepts\(viewEpoch\)/);
  assert.match(
    file("SourceUpload.tsx"),
    /await readSourceFile\(file\);\s*if \(!freshNow.current \|\| !fence.accepts\(epoch\)\) return;/,
  );
  assert.match(
    file("SourceUpload.tsx"),
    /freshNow.current && fence.accepts\(fence.capture\(\)\)/,
  );
});
