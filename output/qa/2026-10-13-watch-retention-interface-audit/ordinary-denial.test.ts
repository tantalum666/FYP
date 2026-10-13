import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import ts from "../../../desk-companion/frontend/node_modules/typescript/lib/typescript.js";
import { ResponseFence } from "../../../desk-companion/frontend/src/workspace/personal/responseFence.ts";

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
      "../../../desk-companion/frontend/src/workspace/responsibilities/useResponsibilities.ts",
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

test("AUDIT ordinary overlapping list denial must invalidate newer success",async()=>{const h=setup();try{let s=h.render();s=await h.settle();s.reload(true);const older=h.pending.splice(0);s.reload(true);s=await h.settle();assert.equal(s.fresh,true);for(const item of older){if(item.path==='/responsibilities')item.reject({status:403,code:'PRIVATE_CONTEXT_HIDDEN'});else item.resolve({tasks:[],responsibility:{id:'watch-one'},reviews:[]});}await new Promise(r=>setImmediate(r));s=h.render();assert.equal(s.fresh,false);}finally{h.close();}});
test('AUDIT hidden actual read only calls safe list, never maintenance or private capacity',async()=>{const h=setup();try{h.hide();h.render();assert.deepEqual(h.pending.map(p=>p.path),['/responsibilities']);const p=h.pending.shift();p.resolve({responsibilities:[],hidden:true,maintenance_usage:{version:1,state:'known',retained_count:20,trashed_count:20,lifetime_count:30,lifetime_limit:256,lifetime_remaining:226}});await new Promise(r=>setImmediate(r));const s=h.render();assert.equal(s.value.list.maintenance_usage.retained_count,20);assert.equal(s.value.list.responsibilities.length,0);}finally{h.close();}});
