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
    new URL(
      "../src/workspace/responsibilities/useResponsibilities.ts",
      import.meta.url,
    ),
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
    if (name === "../agent/useAgentRuns")
      return {
        recoverableRunReadError: (e: any) =>
          !!e &&
          typeof e === "object" &&
          !/AUTH|SESSION|OWNER|PRIVATE|PRIVACY/.test(e.code ?? "") &&
          ((e.code === "CONNECTION_LOST" && e.status === 0) ||
            [408, 429, 500, 502, 503, 504].includes(e.status)),
      };
    if (name === "./types")
      return {
        metadataOnly: (row: any) => ({
          id: row.id,
          status: row.status,
          hidden: true,
        }),
      };
    throw new Error(`Unexpected import ${name}`);
  }, module.exports);
  const fence = new ResponseFence();
  fence.update("owner:one:private", true);
  let selected: string | null = "watch-one";
  let hidden = false;
  let path: string | null = null;
  const render = () =>
    hooks.render(() =>
      module.exports.useResponsibilities(
        fence,
        fence.version,
        hidden,
        selected,
        path,
      ),
    );
  const settle = async (failure?: unknown) => {
    const batch = pending.splice(0);
    for (const item of batch) {
      if (failure && item.path === "/responsibilities/scope")
        item.reject(failure);
      else
        item.resolve(
          item.path === "/responsibilities"
            ? {
                responsibilities: [{ id: "watch-one", title: "Private title" }],
                hidden: false,
              }
            : item.path === "/responsibilities/scope"
              ? { scope_revision: "scope-one", tasks: [] }
              : { responsibility: { id: selected, version: 1 }, reviews: [] },
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
    hide: () => {
      hidden = true;
      fence.update("owner:one:metadata", true);
    },
    selection: (next: string | null) => {
      path = next;
    },
    close() {
      hooks.close();
      for (const [key, descriptor] of previous) {
        if (descriptor) Object.defineProperty(globalThis, key, descriptor);
        else Reflect.deleteProperty(globalThis, key);
      }
    },
  };
}

test("production watch hook reads only on mount and preserves unknown-write host during transient refresh", async () => {
  const h = setup();
  try {
    h.render();
    let state = await h.settle();
    const old = state.value;
    assert.equal(state.fresh, true);
    const read = state.reload(true);
    state = await h.settle({ code: "CONNECTION_LOST", status: 0 });
    await read;
    assert.strictEqual(state.value, old);
    assert.equal(state.fresh, false);
    const next = state.reload(true);
    state = await h.settle();
    await next;
    assert.equal(state.fresh, true);
  } finally {
    h.close();
  }
});
test("watch hook rejects late detail from a previous selection and never posts acknowledgment", async () => {
  const h = setup();
  try {
    h.render();
    let state = await h.settle();
    const old = state.reload(true);
    const before = h.pending.splice(0);
    h.choose("watch-two");
    assert.equal(h.render().value, null);
    await h.settle();
    for (const item of before)
      item.resolve(
        item.path === "/responsibilities"
          ? { responsibilities: [], hidden: false }
          : item.path === "/responsibilities/scope"
            ? { tasks: [] }
            : { responsibility: { id: "watch-one" }, reviews: [] },
      );
    await old;
    state = h.render();
    assert.equal(state.value.detail.responsibility.id, "watch-two");
    assert.ok(before.every((item) => !item.path.includes("acknowledge")));
  } finally {
    h.close();
  }
});
test("parallel late privacy denial clears after transient failure and hidden reads never fetch source scope/detail", async () => {
  const h = setup();
  try {
    h.render();
    let state = await h.settle();
    const read = state.reload(true);
    const batch = h.pending.splice(0);
    batch
      .find((item) => item.path === "/responsibilities")!
      .reject({ code: "CONNECTION_LOST", status: 0 });
    await read;
    assert.ok(h.render().value);
    batch
      .find((item) => item.path === "/responsibilities/scope")!
      .reject({ code: "PRIVATE_CONTEXT_HIDDEN", status: 403 });
    batch
      .find((item) => item.path.endsWith("watch-one"))!
      .resolve({ responsibility: { id: "watch-one" }, reviews: [] });
    await new Promise((resolve) => setImmediate(resolve));
    assert.equal(h.render().value, null);
    h.hide();
    h.render();
    assert.deepEqual(
      h.pending.map((item) => item.path),
      ["/responsibilities"],
    );
    state = await h.settle();
    assert.equal(state.value.list.responsibilities[0].title, undefined);
    assert.equal(state.value.scope, null);
    assert.equal(state.value.detail, null);
  } finally {
    h.close();
  }
});
test("field/selection query changes and privacy epochs fence delayed results", async () => {
  const h = setup();
  try {
    h.render();
    let state = await h.settle();
    const read = state.reload(true);
    h.selection("/responsibilities/scope?task_id=two&field=progress");
    assert.equal(h.render().value, null);
    await h.settle();
    await read;
    state = h.render();
    assert.ok(state.value.key.includes("task_id=two"));
    h.fence.update("owner:other", false);
    assert.equal(h.render().value, null);
  } finally {
    h.close();
  }
});
