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
  const hooks = new HookHarness();
  const posts: any[] = []; const reloads:any[]=[];
  const pending: any[] = [];
  const row = {
    id: "watch-one",
    version: 3,
    retention_state: "retained",
    retention_version: 1,
    hidden: false,
    status: "active",
    title: "Synthetic private watch",
    task_ids: ["one"],
    fields: ["status"],
    review_budget: 10,
    reviews_used: 1,
    daily_review_budget: 5,
    daily_used: 1,
    pending_count: 1,
  };
  const review = {
    id: "review-one",
    responsibility_id: "watch-one",
    version: 2,
    delivery_state: "pending",
    changed_ids: ["one"],
    changed_fields: ["status"],
  };
  let fresh = true;
  let selected: string | null = null;
  let value: any = {
    list: {
      responsibilities: [row],
      pending_count: 1,
      revision: 1,
      limits: {},
    },
    catalog: { tasks: [] },
    scope: null,
    detail: null,
  };
  const fence = new ResponseFence();
  fence.update("owner:private", true);
  const epoch = fence.version;
  const module = { exports: {} as any },
    mutations = { exports: {} as any };
  function compile(path: string, exports: any, resolve: (name: string) => any) {
    const compiled = ts.transpileModule(
      readFileSync(new URL(path, import.meta.url), "utf8"),
      {
        compilerOptions: {
          target: ts.ScriptTarget.ES2022,
          module: ts.ModuleKind.CommonJS,
          jsx: ts.JsxEmit.ReactJSX,
        },
      },
    ).outputText;
    new Function("require", "exports", compiled)(resolve, exports);
  }
  compile(
    "../../../desk-companion/frontend/src/workspace/personal/usePrivateMutation.ts",
    mutations.exports,
    (name) => {
      if (name === "react") return hooks.react;
      if (name === "../../api")
        return {
          request: (path: string, options: any) => {
            posts.push({ path, ...options });
            return new Promise((resolve, reject) =>
              pending.push({ resolve, reject }),
            );
          },
        };
      if (name === "./privateWrite") return { PrivateWriteQueue };
      throw new Error(name);
    },
  );
  compile(
    "../../../desk-companion/frontend/src/workspace/responsibilities/ResponsibilitiesPanel.tsx",
    module.exports,
    (name) => {
      if (name === "react") return hooks.react;
      if (name === "react/jsx-runtime")
        return {
          jsx: (type: any, props: any) => ({ type, props }),
          jsxs: (type: any, props: any) => ({ type, props }),
        };
      if (name === "../personal/usePrivateMutation") return mutations.exports;
      if (name === "../../components/DraftGuard") return { useDraftGuard() {} };
      if (name === "./useResponsibilities")
        return {
          useResponsibilities: (
            _f: any,
            _e: any,
            _h: any,
            id: string | null,
          ) => {
            selected = id;
            return {
              value: {
                ...value,
                detail: id
                  ? {
                      responsibility: row,
                      selected_tasks: [
                        {
                          id: "one",
                          available: true,
                          title: "Task",
                          version: 1,
                        },
                      ],
                      reviews: [review],
                      revision: 1,
                    }
                  : null,
              },
              fresh,
              error: null,
              loading: false,
              reload: async () => { reloads.push(id); },
            };
          },
        };
      if (name === "./types") return watchTypes;
      if (name === "./retention") return retentionTypes;
      if (name === "./labels")
        return {
          actionLabel: (a: string) => a,
          statusLabel: (s: string) => s,
          fieldLabel: (f: string) => f,
          watchError: () => "safe error",
        };
      if (name === "./WatchReviewCard")
        return { WatchReviewCard: "WatchReviewCard" };
      if (name === "./WatchRetention") return {WatchRetention:"WatchRetention",WatchUsage:"WatchUsage"};
      if (name === "./CurrentTask") return { CurrentTask: "CurrentTask" };
      if (name.endsWith(".css")) return {};
      return {};
    },
  );
  const render = () =>
    hooks.render(() =>
      module.exports.WatchWorkspace({
        fence,
        epoch,
        hidden: false,
        t: (en: string) => en,
        onCompile: (goal: any) => compiled.push(goal),
      }),
    );
  const compiled: any[] = [];
  const settle = async (error?: any) => {
    const write = pending.shift();
    if (error) write.reject(error);
    else
      write.resolve({
        responsibility: row,
        saved: true,
        operation_id: "synthetic-key",
        revision: 1,
      });
    await new Promise((resolve) => setImmediate(resolve));
    return render();
  };
  return {
    render,
    posts,
    reloads,
    pending,
    settle,
    fence,
    compiled,
    stale: (next: boolean) => {
      fresh = !next;
    },
    changeRevision: () => {
      value = {
        ...value,
        list: { ...value.list, revision: value.list.revision + 1 },
      };
    },
    close: () => hooks.close(),
  };
}
import { PrivateWriteQueue } from "../../../desk-companion/frontend/src/workspace/personal/privateWrite.ts";
import * as retentionTypes from "../../../desk-companion/frontend/src/workspace/responsibilities/retention.ts";
import * as watchTypes from "../../../desk-companion/frontend/src/workspace/responsibilities/types.ts";
function nodes(tree: any): any[] {
  if (!tree || typeof tree !== "object") return [];
  if (Array.isArray(tree)) return tree.flatMap(nodes);
  return [tree, ...nodes(tree.props?.children)];
}
function textOf(node: any): string {
  if (node == null) return "";
  if (typeof node !== "object") return String(node);
  if (Array.isArray(node)) return node.map(textOf).join("");
  return textOf(node.props?.children);
}
function button(tree: any, label: string) {
  const match = nodes(tree).find(
    (node) => node.type === "button" && textOf(node) === label,
  );
  assert.ok(match, label);
  return match;
}
function review(tree: any) {
  const match = nodes(tree).find((node) => node.type === "WatchReviewCard");
  assert.ok(match);
  return match;
}
test('AUDIT ordinary acknowledgement disposition clears selected detail without calling stale selected reload',async()=>{const h=setup();try{let tree=h.render();button(tree,'Open reviews').props.onClick();tree=h.render();review(tree).props.onAcknowledge();h.pending.shift().resolve({kind:'retention_disposition',responsibility_id:'watch-one',retention_state:'purged',retention_version:2,original_operation_kind:'acknowledge',review_id:'review-one',operation_id:'synthetic-key',revision:3,recorded_success:true});await new Promise(r=>setImmediate(r));tree=h.render();assert.equal(nodes(tree).filter(n=>n.type==='WatchReviewCard').length,0);assert.deepEqual(h.reloads,[]);assert.equal(h.compiled.length,0);}finally{h.close();}});
test('AUDIT maintenance callback clears ordinary selection before any reload and makes no Work handoff',()=>{const h=setup();try{let tree=h.render();button(tree,'Open reviews').props.onClick();tree=h.render();button(tree,'Manage terminal history and Trash').props.onClick();tree=h.render();const maintenance=nodes(tree).find(n=>n.type==='WatchRetention');assert.ok(maintenance);maintenance.props.onChanged({kind:'retention_disposition'});tree=h.render();assert.equal(nodes(tree).filter(n=>n.type==='WatchReviewCard').length,0);assert.deepEqual(h.reloads,[]);assert.equal(h.compiled.length,0);assert.equal(h.posts.length,0);}finally{h.close();}});
