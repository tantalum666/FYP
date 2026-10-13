import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import ts from "typescript";
import { ResponseFence } from "../src/workspace/personal/responseFence.ts";
import * as retention from "../src/workspace/responsibilities/retention.ts";
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

const usage = {
  version: 1,
  retained_count: 20,
  trashed_count: 1,
  lifetime_count: 30,
  lifetime_limit: 256,
  lifetime_remaining: 226,
  state: "known",
};
const row = {
  id: "watch-one",
  title: "Synthetic history",
  version: 3,
  retention_version: 1,
  retention_state: "retained",
  status: "cancelled",
  hidden: false,
  task_ids: ["task-one"],
  fields: ["status"],
  review_budget: 10,
  reviews_used: 2,
};
function preview(action = "purge", source: any = row) {
  return {
    kind: "watch_retention_preview",
    preview_id: "preview-one",
    action,
    responsibility: source,
    counts: {
      definitions: 1,
      source_baselines: 1,
      retained_reviews: 2,
      operation_receipts: 3,
    },
    retained_operation_receipts_after: 4,
    logical_slots_released: action === "purge" ? 1 : 0,
    receipts_retained: true,
    independent_tasks_retained: true,
    independent_work_retained: true,
    expires_at: new Date(Date.now() + 300000).toISOString(),
    maintenance_usage: usage,
    revision: 5,
  };
}
const disposition = (key = "operation-one") => ({
  kind: "retention_disposition",
  responsibility_id: "watch-one",
  retention_state: "purged",
  retention_version: 2,
  original_operation_kind: "purge",
  review_id: null,
  operation_id: key,
  revision: 6,
  recorded_success: true,
});
const listing = () => ({
  responsibilities: [{ ...row, retention_state: "trashed" }],
  maintenance_usage: usage,
  revision: 5,
  server_time: new Date().toISOString(),
});
const detail = () => ({
  responsibility: { ...row },
  reviews: [1, 2].map((n) => ({
    id: `review-${n}`,
    responsibility_id: row.id,
    version: 1,
    changed_fields: ["status"],
    changed_ids: ["task-one"],
    delivery_state: "dismissed",
  })),
  selected_tasks: [
    { id: "task-one", title: "Synthetic task", available: true, version: 1 },
  ],
  revision: 5,
});
const tick = () => new Promise((resolve) => setImmediate(resolve));
function setup() {
  const hooks = new HookHarness(),
    events = new EventTarget(),
    pending: any[] = [],
    calls: any[] = [],
    changed: any[] = [],
    denials: any[] = [];
  const previous = Object.getOwnPropertyDescriptor(globalThis, "window");
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: Object.assign(events, { setTimeout, clearTimeout }),
  });
  const exports: any = {};
  const code = ts.transpileModule(
    readFileSync(
      new URL(
        "../src/workspace/responsibilities/useWatchRetention.ts",
        import.meta.url,
      ),
      "utf8",
    ),
    {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS,
        target: ts.ScriptTarget.ES2022,
      },
    },
  ).outputText;
  new Function("require", "exports", code)((name: string) => {
    if (name === "react") return hooks.react;
    if (name === "../../api")
      return {
        request: (path: string, options: any = {}) => {
          calls.push({ path, options });
          return new Promise((resolve, reject) =>
            pending.push({ path, options, resolve, reject }),
          );
        },
      };
    if (name.endsWith("responseFence")) return { ResponseFence };
    if (name === "./retention") return retention;
    throw Error(name);
  }, exports);
  const fence = new ResponseFence();
  fence.update("owner", true);
  const epoch = fence.version;
  let fresh = true,
    snapshot = 5;
  const render = () =>
    hooks.render(() =>
      exports.useWatchRetention(
        fence,
        epoch,
        fresh,
        snapshot,
        (v: any) => changed.push(v),
        (e: any) => denials.push(e),
      ),
    );
  const settle = async (value: any) => {
    pending.shift().resolve(value);
    await tick();
    return render();
  };
  const ready = async () => {
    render();
    return settle(listing());
  };
  const prepared = async (action = "purge") => {
    let state = await ready();
    state.inspect(row.id);
    state = await settle(detail());
    state.prepare(state.detail.responsibility, action);
    state = await settle(preview(action));
    return state;
  };
  return {
    render,
    ready,
    prepared,
    settle,
    pending,
    calls,
    changed,
    denials,
    fence,
    events,
    setFresh: (v: boolean) => {
      fresh = v;
    },
    revision: () => {
      snapshot++;
    },
    close: () => {
      hooks.close();
      if (previous) Object.defineProperty(globalThis, "window", previous);
      else Reflect.deleteProperty(globalThis, "window");
    },
  };
}
test("maintenance usage is exact and never guesses empty from missing/unknown/over-limit metadata", () => {
  assert.ok(retention.validMaintenanceUsage(usage));
  for (const field of [
    "retained_count",
    "trashed_count",
    "lifetime_count",
    "lifetime_remaining",
  ])
    assert.equal(
      retention.validMaintenanceUsage({ ...usage, [field]: null }),
      false,
    );
  for (const state of ["unavailable", "over_limit"]) {
    assert.ok(
      retention.validMaintenanceUsage({
        ...usage,
        state,
        retained_count: null,
        trashed_count: null,
        lifetime_count: null,
        lifetime_remaining: null,
      }),
    );
    assert.equal(retention.validMaintenanceUsage({ ...usage, state }), false);
  }
  for (const value of [
    { ...usage, trashed_count: 21 },
    { ...usage, lifetime_remaining: 0 },
    { ...usage, lifetime_count: 257 },
    { ...usage, retained_count: true },
    { ...usage, lifetime_limit: 512 },
  ])
    assert.equal(retention.validMaintenanceUsage(value), false);
});
test("exact previews pin action identity versions counts retained effects and strict purge-only consent", () => {
  const p = preview();
  assert.ok(retention.validRetentionPreview(p, row as any, "purge"));
  assert.equal(retention.retentionBody(p as any, false), null);
  assert.equal(
    retention.retentionBody(p as any, true)?.confirm_permanent_removal,
    true,
  );
  for (const action of ["trash", "restore"]) {
    const r =
      action === "restore" ? { ...row, retention_state: "trashed" } : row;
    const p = preview(action, r);
    assert.ok(retention.validRetentionPreview(p, r as any, action as any));
    assert.equal(
      "confirm_permanent_removal" in retention.retentionBody(p as any, true)!,
      false,
    );
  }
  for (const corrupt of [
    { ...p, logical_slots_released: 0 },
    { ...p, retained_operation_receipts_after: 3 },
    { ...p, independent_tasks_retained: false },
    { ...p, responsibility: { ...row, id: "other" } },
    { ...p, responsibility: { ...row, retention_version: 2 } },
    { ...p, action: "trash" },
  ])
    assert.equal(
      retention.validRetentionPreview(corrupt, row as any, "purge"),
      false,
    );
});
test("safe result union rejects labels or fake acknowledgment in opaque removed dispositions", () => {
  assert.ok(
    retention.validWatchMutationResult(disposition(), row.id, "operation-one"),
  );
  for (const corrupt of [
    { ...disposition(), title: "leak" },
    { ...disposition(), acknowledged: true },
    { ...disposition(), responsibility: row },
    { ...disposition(), recorded_success: 1 },
    { ...disposition(), operation_id: "wrong" },
  ])
    assert.equal(
      retention.validWatchMutationResult(corrupt, row.id, "operation-one"),
      false,
    );
  assert.ok(
    retention.validWatchMutationResult({
      responsibility: row,
      saved: true,
      operation_id: "operation-one",
      revision: 6,
    }),
  );
});
test("original mutation queue validates before clearing and never replaces unknown body/key", async () => {
  let count = 0;
  const calls: any[] = [];
  const queue = new retention.RetentionWriteQueue(
    async (path, options) => {
      calls.push({ path, options });
      if (++count === 1) throw { status: 0 };
      if (count === 2) return { ...disposition(), title: "unsafe" };
      return disposition();
    },
    () => "operation-one",
  );
  await assert.rejects(
    queue.send(row.id, retention.retentionBody(preview() as any, true)),
  );
  assert.equal(queue.pending, true);
  await assert.rejects(queue.send("other", {}));
  assert.equal(calls.length, 1);
  await assert.rejects(queue.retry());
  assert.equal(queue.pending, true);
  await queue.retry();
  assert.equal(queue.pending, false);
  assert.deepEqual(calls[0], calls[1]);
  assert.deepEqual(calls[0], calls[2]);
});
test("production hook only reads on opening; cancelled confirmation and captured final button write nothing", async () => {
  const h = setup();
  try {
    let s = await h.prepared();
    const old = s.preview,
      confirm = s.confirm;
    s.cancel();
    s = h.render();
    assert.equal(s.preview, null);
    confirm(old, true);
    assert.equal(
      h.calls.filter((c) => c.path.endsWith("/retention")).length,
      0,
    );
    assert.ok(h.calls.every((c) => !c.path.includes("capacity")));
  } finally {
    h.close();
  }
});
test("production final purge requires strict final click and duplicate click produces one exact mutation", async () => {
  const h = setup();
  try {
    let s = await h.prepared();
    const p = s.preview;
    s.confirm(p, false);
    assert.equal(h.pending.length, 0);
    s.confirm(p, true);
    s.confirm(p, true);
    assert.equal(h.pending.length, 1);
    const request = h.pending[0];
    assert.equal(
      JSON.parse(request.options.body).confirm_permanent_removal,
      true,
    );
    s = await h.settle(disposition(request.options.headers["X-Operation-Id"]));
    assert.equal(h.changed.length, 1);
    assert.equal(s.detail, null);
    assert.equal(s.preview, null);
    assert.equal(s.pending, false);
    assert.equal(h.pending[0].path, "/responsibilities/maintenance");
    await h.settle(listing());
  } finally {
    h.close();
  }
});
test("production unknown-result recovery preserves exact operation through read refresh and expired preview", async () => {
  const h = setup();
  try {
    let s = await h.prepared();
    s.confirm(s.preview, true);
    const original = h.pending.shift();
    original.reject({ status: 0, code: "CONNECTION_LOST" });
    await tick();
    s = h.render();
    assert.equal(s.pending, true);
    assert.equal(s.preview, null);
    s.refresh();
    s = await h.settle(listing());
    s.retry();
    const retry = h.pending[0];
    assert.deepEqual(retry.options, original.options);
    assert.equal(retry.path, original.path);
    await h.settle(disposition(retry.options.headers["X-Operation-Id"]));
    assert.equal(h.changed.length, 1);
  } finally {
    h.close();
  }
});
test("freshness and snapshot transitions immediately mask confirmation and fence old callbacks", async () => {
  for (const kind of ["stale", "revision"]) {
    const h = setup();
    try {
      let s = await h.prepared();
      const p = s.preview,
        confirm = s.confirm;
      if (kind === "stale") h.setFresh(false);
      else h.revision();
      s = h.render();
      assert.equal(s.preview, null);
      confirm(p, true);
      if (kind === "stale") {
        h.setFresh(true);
        s = h.render();
        assert.equal(s.preview, null);
        confirm(p, true);
      }
      assert.equal(
        h.calls.filter((c) => c.path.endsWith("/retention")).length,
        0,
      );
    } finally {
      h.close();
    }
  }
});
test("privacy logout and offline events synchronously fence captured confirmation and clear private state", async () => {
  for (const name of ["desk:session", "desk:personal-context", "offline"]) {
    const h = setup();
    try {
      let s = await h.prepared();
      const p = s.preview,
        confirm = s.confirm;
      h.events.dispatchEvent(new Event(name));
      confirm(p, true);
      s = h.render();
      assert.equal(s.preview, null);
      assert.equal(s.detail, null);
      assert.equal(s.list, null);
      assert.equal(
        h.calls.filter((c) => c.path.endsWith("/retention")).length,
        0,
      );
      assert.equal(h.denials.length, 1);
    } finally {
      h.close();
    }
  }
});
test("reordered actual authority denial invalidates shared fence even after a newer read succeeds", async () => {
  const h = setup();
  try {
    let s = await h.ready();
    s.refresh();
    const older = h.pending.shift();
    s.refresh();
    s = await h.settle(listing());
    assert.ok(s.list);
    older.reject({ status: 403, code: "PRIVATE_CONTEXT_HIDDEN" });
    await tick();
    s = h.render();
    assert.equal(s.list, null);
    assert.equal(s.available, false);
    assert.equal(h.denials.length, 1);
  } finally {
    h.close();
  }
});
test("postcommit authority denial never spawns a replacement operation and unmounted callbacks cannot fetch", async () => {
  const h = setup();
  let s = await h.prepared();
  s.confirm(s.preview, true);
  const original = h.pending.shift();
  original.reject({ status: 409, code: "RESPONSIBILITY_CONTEXT_CHANGED" });
  await tick();
  s = h.render();
  assert.equal(s.pending, false);
  s.retry();
  assert.equal(h.pending.length, 0);
  const oldRefresh = s.refresh;
  h.close();
  oldRefresh();
  assert.equal(h.pending.length, 0);
});

test("production Trash and Restore final clicks omit purge consent and never call resume", async () => {
  for (const action of ["trash", "restore"] as const) {
    const h = setup();
    try {
      let s = await h.ready();
      s.inspect(row.id);
      const record = detail();
      if (action === "restore")
        record.responsibility.retention_state = "trashed";
      s = await h.settle(record);
      s.prepare(s.detail.responsibility, action);
      s = await h.settle(preview(action, record.responsibility));
      s.confirm(s.preview, false);
      const request = h.pending[0];
      const body = JSON.parse(request.options.body);
      assert.equal(body.action, action);
      assert.equal("confirm_permanent_removal" in body, false);
      assert.ok(h.calls.every((c) => !c.path.endsWith("/actions")));
      const key = request.options.headers["X-Operation-Id"];
      const response =
        action === "trash"
          ? {
              ...disposition(key),
              retention_state: "trashed",
              original_operation_kind: "trash",
            }
          : {
              responsibility: { ...row, retention_version: 3 },
              saved: true,
              operation_id: key,
              revision: 6,
            };
      s = await h.settle(response);
      assert.equal(h.changed.length, 1);
      assert.equal(s.preview, null);
    } finally {
      h.close();
    }
  }
});
test("production rejects changed impact inventory and expired preview without mutation", async () => {
  for (const bad of ["inventory", "expired"] as const) {
    const h = setup();
    try {
      let s = await h.ready();
      s.inspect(row.id);
      s = await h.settle(detail());
      s.prepare(s.detail.responsibility, "purge");
      const p = preview();
      if (bad === "inventory") p.counts.retained_reviews = 1;
      else p.expires_at = new Date(Date.now() - 1).toISOString();
      s = await h.settle(p);
      assert.equal(s.preview, null);
      assert.ok(s.error);
      s.confirm(p, true);
      assert.equal(
        h.calls.filter((c) => c.path.endsWith("/retention")).length,
        0,
      );
    } finally {
      h.close();
    }
  }
});
test("late purge response after session invalidation cannot publish success or private content", async () => {
  const h = setup();
  try {
    let s = await h.prepared();
    s.confirm(s.preview, true);
    const request = h.pending[0];
    h.events.dispatchEvent(new Event("desk:session"));
    s = await h.settle(disposition(request.options.headers["X-Operation-Id"]));
    assert.equal(h.changed.length, 0);
    assert.equal(s.result, null);
    assert.equal(s.list, null);
    assert.equal(s.pending, false);
  } finally {
    h.close();
  }
});
