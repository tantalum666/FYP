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
  const hooks = new HookHarness();
  const posts: any[] = [];
  const reloadedSelections: any[] = [];
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
    "../src/workspace/personal/usePrivateMutation.ts",
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
    "../src/workspace/responsibilities/ResponsibilitiesPanel.tsx",
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
              reload: async () => {
                reloadedSelections.push(id);
              },
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
  const settle = async (error?: any, result?: any) => {
    const write = pending.shift();
    if (error) write.reject(error);
    else
      write.resolve(
        result ?? {
          responsibility: row,
          saved: true,
          operation_id: "synthetic-key",
          revision: 1,
        },
      );
    await new Promise((resolve) => setImmediate(resolve));
    return render();
  };
  return {
    render,
    posts,
    reloadedSelections,
    selected: () => selected,
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
import { PrivateWriteQueue } from "../src/workspace/personal/privateWrite.ts";
import * as retentionTypes from "../src/workspace/responsibilities/retention.ts";
import * as watchTypes from "../src/workspace/responsibilities/types.ts";
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
test("actual watch callbacks never acknowledge on read, and unknown ack retries exact body/key only after fresh read", async () => {
  const h = setup();
  try {
    let tree = h.render();
    assert.equal(h.posts.length, 0);
    button(tree, "Open reviews").props.onClick();
    tree = h.render();
    assert.equal(h.posts.length, 0);
    review(tree).props.onAcknowledge();
    assert.equal(h.posts.length, 1);
    assert.equal(
      h.posts[0].path,
      "/responsibilities/watch-one/reviews/review-one/acknowledge",
    );
    assert.equal(
      h.posts[0].body,
      JSON.stringify({ expected_review_version: 2 }),
    );
    tree = await h.settle({ code: "CONNECTION_LOST", status: 0 });
    const original = h.posts[0];
    h.stale(true);
    tree = h.render();
    const retry = button(tree, "Retry the same request");
    assert.equal(retry.props.disabled, true);
    retry.props.onClick();
    assert.equal(h.posts.length, 1);
    h.stale(false);
    tree = h.render();
    button(tree, "Retry the same request").props.onClick();
    assert.equal(h.posts.length, 2);
    assert.deepEqual(h.posts[1], original);
    await h.settle();
  } finally {
    h.close();
  }
});
test("actual stale acknowledgment, compile and inspect callbacks are fenced across new snapshot or hidden epoch", () => {
  const h = setup();
  try {
    let tree = h.render();
    button(tree, "Open reviews").props.onClick();
    tree = h.render();
    const old = review(tree);
    h.changeRevision();
    h.render();
    old.props.onAcknowledge();
    old.props.onCompile(["one"]);
    old.props.onInspect("one");
    assert.equal(h.posts.length, 0);
    assert.equal(h.compiled.length, 0);
    tree = h.render();
    const current = review(tree);
    h.fence.update("owner:hidden", false);
    current.props.onAcknowledge();
    current.props.onCompile(["one"]);
    assert.equal(h.posts.length, 0);
    assert.equal(h.compiled.length, 0);
  } finally {
    h.close();
  }
});
test("actual mutation privacy denial clears private view and prevents replay under old identity", async () => {
  const h = setup();
  try {
    let tree = h.render();
    button(tree, "Open reviews").props.onClick();
    tree = h.render();
    review(tree).props.onAcknowledge();
    tree = await h.settle({ code: "PRIVATE_CONTEXT_HIDDEN", status: 403 });
    assert.doesNotMatch(textOf(tree), /Synthetic private watch/);
    assert.match(textOf(tree), /Owner access changed/);
    assert.equal(h.fence.accepts(1), false);
  } finally {
    h.close();
  }
});

test("production current-task access denial or redacted success invalidates fence and reports parent; current status is bilingual", async () => {
  for (const response of ["denied", "redacted", "visible"] as const) {
    const hooks = new HookHarness(),
      fence = new ResponseFence();
    fence.update("owner:visible", true);
    const epoch = fence.version;
    let resolve!: (value: unknown) => void, reject!: (reason: unknown) => void;
    let denied = 0;
    const module = { exports: {} as any };
    const compiled = ts.transpileModule(
      readFileSync(
        new URL(
          "../src/workspace/responsibilities/CurrentTask.tsx",
          import.meta.url,
        ),
        "utf8",
      ),
      {
        compilerOptions: {
          target: ts.ScriptTarget.ES2022,
          module: ts.ModuleKind.CommonJS,
          jsx: ts.JsxEmit.ReactJSX,
        },
      },
    ).outputText;
    new Function("require", "exports", compiled)((name: string) => {
      if (name === "react") return hooks.react;
      if (name === "react/jsx-runtime")
        return {
          jsx: (type: any, props: any) => ({ type, props }),
          jsxs: (type: any, props: any) => ({ type, props }),
        };
      if (name === "../../api")
        return {
          request: () =>
            new Promise((a, b) => {
              resolve = a;
              reject = b;
            }),
        };
      if (name === "./labels") return { watchError: () => "safe error" };
      throw new Error(name);
    }, module.exports);
    let zh = false;
    const render = () =>
      hooks.render(() =>
        module.exports.CurrentTask({
          id: "one",
          fence,
          epoch,
          fresh: true,
          t: (en: string, cn: string) => (zh ? cn : en),
          close() {},
          onAccessDenied() {
            denied++;
          },
        }),
      );
    try {
      render();
      if (response === "denied")
        reject({ code: "PRIVATE_CONTEXT_HIDDEN", status: 403 });
      else
        resolve({
          task: {
            id: "one",
            status: "completed",
            title: "Synthetic current record",
            redacted: response === "redacted",
            steps: [],
            timezone: "UTC",
          },
          evidence: [],
        });
      await new Promise((resolve) => setImmediate(resolve));
      const tree = render();
      if (response !== "visible") {
        assert.equal(denied, 1);
        assert.equal(fence.accepts(epoch), false);
        assert.equal(tree, null);
      } else {
        assert.match(textOf(tree), /Status: Completed/);
        zh = true;
        assert.match(textOf(render()), /状态: 已完成/);
        assert.equal(denied, 0);
      }
    } finally {
      hooks.close();
    }
  }
});

test("committed-but-fenced context change clears private view and tells owner to inspect history instead of new retry", async () => {
  const h = setup();
  try {
    let tree = h.render();
    button(tree, "Open reviews").props.onClick();
    tree = h.render();
    review(tree).props.onAcknowledge();
    tree = await h.settle({
      code: "RESPONSIBILITY_CONTEXT_CHANGED",
      status: 409,
    });
    assert.doesNotMatch(textOf(tree), /Synthetic private watch/);
    assert.match(textOf(tree), /may already have saved/);
    assert.equal(h.fence.accepts(1), false);
  } finally {
    h.close();
  }
});

test("recorded removed disposition clears selected ordinary detail before refresh instead of fetching removed detail", async () => {
  const h = setup();
  try {
    let tree = h.render();
    button(tree, "Open reviews").props.onClick();
    tree = h.render();
    assert.equal(h.selected(), "watch-one");
    review(tree).props.onAcknowledge();
    tree = await h.settle(undefined, {
      kind: "retention_disposition",
      responsibility_id: "watch-one",
      retention_state: "purged",
      retention_version: 3,
      original_operation_kind: "acknowledge",
      review_id: "review-one",
      operation_id: "synthetic-key",
      revision: 2,
      recorded_success: true,
    });
    assert.equal(h.selected(), null);
    assert.equal(h.reloadedSelections.length, 0);
    assert.equal(
      nodes(tree).filter((n) => n.type === "WatchReviewCard").length,
      0,
    );
  } finally {
    h.close();
  }
});

test("unmounted watch callbacks cannot acknowledge or compile under a still-valid shared owner", () => {
  const h = setup();
  let tree = h.render();
  button(tree, "Open reviews").props.onClick();
  tree = h.render();
  const captured = review(tree);
  h.close();
  captured.props.onAcknowledge();
  captured.props.onCompile(["one"]);
  assert.equal(h.posts.length, 0);
  assert.equal(h.compiled.length, 0);
});
