import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import ts from "typescript";
import { ResponseFence } from "../src/workspace/personal/responseFence.ts";
import * as searchTypes from "../src/workspace/agent/workSearch.ts";
import type {
  WorkSearchHit,
  WorkSearchResponse,
} from "../src/workspace/agent/workSearch.ts";
const {
  workSearchInput,
  workHitKey,
  workDetailPath,
  validWorkSearchResponse,
  workSearchDetail,
  WorkSearchFence,
} = searchTypes;
const hit = (id = "file-one"): WorkSearchHit => ({
  kind: "artifact",
  id,
  title: "Work report v1",
  timestamp: "2026-10-13T06:00:00Z",
  matched_fields: ["current_linked_goal"],
  match_reason: "linked_metadata",
  format: "markdown",
  byte_count: 42,
  recorded_status: "verified",
  run_id: "run-one",
  current_linked_goal: "Current planning goal",
  output_membership: "earlier",
  source_names: [],
});
const page = (
  items = [hit()],
  total = items.length,
  next_offset: number | null = null,
): WorkSearchResponse => ({
  items,
  total,
  next_offset,
  snapshot: "a".repeat(64),
  search_scope: "local_metadata",
  ranking: "lexical_v1",
  file_status_basis: "last_recorded",
});
const artifact = (id = "file-one") => ({
  id,
  display_name: "Exact inspected file",
  format: "markdown",
  byte_count: 42,
  sha256: "f".repeat(64),
  status: "verified",
  verification: "byte_readback",
  provenance: [],
  authorship: "deterministic",
});

test("input is explicit, literal, bounded and never includes grants or operation IDs", () => {
  assert.deepEqual(workSearchInput("  目标 FullＷidth %_ <script>  ", "all"), {
    query: "目标 FullＷidth %_ <script>",
    kind: "all",
    limit: 20,
    offset: 0,
  });
  assert.ok(workSearchInput("📝".repeat(200), "source"));
  assert.equal(workSearchInput("📝".repeat(201), "source"), null);
  assert.equal(workSearchInput(" ", "all")?.query, "");
});
test("compact pages reject malformed, mixed, duplicate, oversized and changed snapshots", () => {
  const input = workSearchInput("goal", "all")!;
  assert.equal(validWorkSearchResponse(page(), input), true);
  const invalid = [
    { ...page(), items: [{ ...hit(), matched_fields: ["tool_arguments"] }] },
    { ...page(), items: [hit(), hit()], total: 2 },
    { ...page(), search_scope: "file_content" },
    { ...page(), file_status_basis: "fresh" },
    { ...page(), total: 601 },
    { ...page(), items: [{ ...hit(), format: ["markdown"] }] },
    { ...page(), items: [{ ...hit(), kind: ["artifact"] }] },
    { ...page(), total: 3, next_offset: 1 },
    { ...page(), total: 3 },
    { ...page(), items: [{ ...hit(), output_membership: "latest_by_name" }] },
    { ...page(), items: [{ ...hit(), byte_count: -1 }] },
  ];
  for (const body of invalid)
    assert.equal(validWorkSearchResponse(body, input), false);
  assert.equal(
    validWorkSearchResponse(page(), { ...input, kind: "source" }),
    false,
  );
  assert.equal(
    validWorkSearchResponse(page(), { ...input, snapshot: "b".repeat(64) }),
    false,
  );
  assert.equal(validWorkSearchResponse(page([], 0), input), true);
});
test("same names stay distinct exact choices and paths cannot change endpoint scope", () => {
  assert.notEqual(workHitKey(hit("one")), workHitKey(hit("two")));
  assert.equal(
    workDetailPath({ kind: "run", id: "run/a?cancel=true" }),
    "/agent-runs/run%2Fa%3Fcancel%3Dtrue",
  );
  assert.equal(workDetailPath({ kind: "artifact", id: "a" }), "/artifacts/a");
  assert.equal(workDetailPath({ kind: "source", id: "s" }), "/sources/s");
});
test("only exact detail records become previews; search hits and wrong IDs are rejected", () => {
  assert.equal(workSearchDetail(hit(), hit()), null);
  assert.equal(workSearchDetail(hit(), artifact("other")), null);
  assert.equal(workSearchDetail(hit(), { artifact: artifact() }), null);
  assert.equal(
    workSearchDetail(hit(), { ...artifact(), provenance: [{}] }),
    null,
  );
  assert.equal(workSearchDetail(hit(), artifact())?.kind, "artifact");
  const source: WorkSearchHit = {
    kind: "source",
    id: "source-one",
    title: "notes.md",
    timestamp: null,
    format: "markdown",
    byte_count: 42,
    recorded_status: "verified",
    revision: 1,
    matched_fields: ["title"],
    match_reason: "exact_title",
  };
  assert.equal(workSearchDetail(source, source), null);
  assert.equal(
    workSearchDetail(source, {
      ...artifact(source.id),
      name: "notes.md",
      revision: 1,
    })?.kind,
    "source",
  );
});
test("sequence gate rejects reordered requests, hide/show, identity changes and cancellation", () => {
  const fence = new ResponseFence();
  fence.update("owner-one", true);
  const gate = new WorkSearchFence();
  const older = gate.begin(fence),
    newer = gate.begin(fence);
  assert.equal(gate.accepts(older, fence), false);
  assert.equal(gate.accepts(newer, fence), true);
  fence.update("owner-one", false);
  fence.update("owner-one", true);
  assert.equal(gate.accepts(newer, fence), false);
  const previous = gate.begin(fence);
  fence.update("owner-two", true);
  assert.equal(gate.accepts(previous, fence), false);
  const closed = gate.begin(fence);
  gate.invalidate();
  assert.equal(gate.accepts(closed, fence), false);
});

// Deterministically execute the actual production hook with deferred transport.
// This is request/lifecycle evidence, not a mounted browser/click test.
class HookHarness {
  slots: any[] = [];
  index = 0;
  effects: (() => void)[] = [];
  react = {
    useState: (initial: any) => {
      const n = this.index++;
      this.slots[n] ??= { value: initial };
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
    useEffect: (effect: () => void | (() => void), deps: any[]) => {
      const n = this.index++,
        old = this.slots[n];
      if (
        old?.deps.length === deps.length &&
        old.deps.every((x: unknown, i: number) => Object.is(x, deps[i]))
      )
        return;
      this.slots[n] = { deps };
      this.effects.push(() => {
        old?.cleanup?.();
        this.slots[n].cleanup = effect();
      });
    },
  };
  render<T>(body: () => T) {
    this.index = 0;
    const result = body();
    this.effects.splice(0).forEach((f) => f());
    return result;
  }
  close() {
    this.slots.forEach((slot) => slot.cleanup?.());
  }
}
class TestApiError extends Error {
  code: string;
  status: number;
  constructor(code: string, status = 0) {
    super(code);
    this.code = code;
    this.status = status;
  }
}
function setup() {
  const prior = Object.getOwnPropertyDescriptor(globalThis, "window");
  const events = new Map<string, Set<() => void>>();
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: {
      addEventListener(name: string, action: () => void) {
        if (!events.has(name)) events.set(name, new Set());
        events.get(name)!.add(action);
      },
      removeEventListener(name: string, action: () => void) {
        events.get(name)?.delete(action);
      },
    },
  });
  const pending: {
    path: string;
    options: RequestInit | undefined;
    resolve: (v: unknown) => void;
    reject: (v: unknown) => void;
  }[] = [];
  const calls: { path: string; options: RequestInit | undefined }[] = [];
  const hooks = new HookHarness(),
    module = { exports: {} as any };
  const compiled = ts.transpileModule(
    readFileSync(
      new URL("../src/workspace/agent/useWorkSearch.ts", import.meta.url),
      "utf8",
    ),
    {
      compilerOptions: {
        target: ts.ScriptTarget.ES2022,
        module: ts.ModuleKind.CommonJS,
      },
    },
  ).outputText;
  new Function("require", "exports", compiled)((name: string) => {
    if (name === "react") return hooks.react;
    if (name === "../personal/responseFence") return { ResponseFence };
    if (name === "./workSearch") return searchTypes;
    if (name === "../../api")
      return {
        ApiError: TestApiError,
        request: (path: string, options?: RequestInit) => {
          calls.push({ path, options });
          return new Promise((resolve, reject) =>
            pending.push({ path, options, resolve, reject }),
          );
        },
      };
    throw new Error(`Unexpected import ${name}`);
  }, module.exports);
  const fence = new ResponseFence();
  fence.update("owner-one", true);
  let fresh = true;
  const render = () =>
    hooks.render(() =>
      module.exports.useWorkSearch(fence, fence.version, fresh),
    );
  return {
    render,
    fence,
    pending,
    calls,
    events,
    fresh(value: boolean) {
      fresh = value;
    },
    async settle() {
      await new Promise((resolve) => setImmediate(resolve));
      return render();
    },
    close() {
      hooks.close();
      if (prior) Object.defineProperty(globalThis, "window", prior);
      else Reflect.deleteProperty(globalThis, "window");
    },
  };
}

test("actual search hook never reads on mount, edits or filter change; submit POST has no mutation key", async () => {
  const h = setup();
  try {
    let state = h.render();
    assert.equal(h.calls.length, 0);
    state.setQuery("private goal");
    state.setKind("artifact");
    state = h.render();
    assert.equal(h.calls.length, 0);
    state.submit();
    assert.equal(h.pending.length, 1);
    assert.equal(h.pending[0].path, "/work/search");
    assert.deepEqual(h.pending[0].options, {
      method: "POST",
      body: JSON.stringify({
        query: "private goal",
        kind: "artifact",
        limit: 20,
        offset: 0,
      }),
    });
    h.pending.shift()!.resolve(page());
    state = await h.settle();
    assert.equal(state.value.page.total, 1);
    assert.equal(state.detail, null);
    assert.equal(h.calls.length, 1, "results never auto-open the only match");
  } finally {
    h.close();
  }
});
test("actual query B remains visible when query A completes later", async () => {
  const h = setup();
  try {
    let state = h.render();
    state.setQuery("A");
    state = h.render();
    state.submit();
    const a = h.pending.shift()!;
    state.setQuery("B");
    state = h.render();
    state.submit();
    const b = h.pending.shift()!;
    b.resolve(page([hit("B")]));
    state = await h.settle();
    assert.equal(state.value.page.items[0].id, "B");
    a.resolve(page([hit("A")]));
    state = await h.settle();
    assert.equal(state.value.input.query, "B");
    assert.equal(state.value.page.items[0].id, "B");
  } finally {
    h.close();
  }
});
test("actual exact detail selection uses a bare record, no start/resume/download/grant calls", async () => {
  const h = setup();
  try {
    let state = h.render();
    state.submit();
    h.pending.shift()!.resolve(page([hit("file-one"), hit("file-two")]));
    state = await h.settle();
    assert.equal(h.calls.length, 1);
    const opening = state.open(hit("file-two"));
    assert.equal(h.pending[0].path, "/artifacts/file-two");
    assert.equal(h.pending[0].options, undefined);
    h.pending.shift()!.resolve(artifact("file-two"));
    assert.equal((await opening)?.kind, "artifact");
    state = h.render();
    assert.equal(state.detail.value.id, "file-two");
    assert.equal(await state.open(hit("not-in-results")), null);
    assert.equal(h.calls.length, 2);
  } finally {
    h.close();
  }
});
test("a newer selection and close clear older exact-detail promises", async () => {
  const h = setup();
  try {
    let state = h.render();
    state.submit();
    h.pending.shift()!.resolve(page([hit("one"), hit("two")]));
    state = await h.settle();
    const one = state.open(hit("one")),
      a = h.pending.shift()!;
    const two = state.open(hit("two")),
      b = h.pending.shift()!;
    b.resolve(artifact("two"));
    await two;
    a.resolve(artifact("one"));
    assert.equal(await one, null);
    state = h.render();
    assert.equal(state.detail.value.id, "two");
    const reopen = state.open(hit("one"));
    const last = h.pending.shift()!;
    state.clearDetail();
    last.resolve(artifact("one"));
    assert.equal(await reopen, null);
    assert.equal(h.render().detail, null);
  } finally {
    h.close();
  }
});
test("stale/hide/identity transitions synchronously mask query and results and reject late file details", async () => {
  for (const transition of ["stale", "hide", "identity"]) {
    const h = setup();
    try {
      let state = h.render();
      state.setQuery("private query");
      state = h.render();
      state.submit();
      h.pending.shift()!.resolve(page());
      state = await h.settle();
      const opening = state.open(hit()),
        delayed = h.pending.shift()!;
      if (transition === "stale") h.fresh(false);
      else
        h.fence.update(
          transition === "hide" ? "owner-one" : "owner-two",
          transition !== "hide",
        );
      state = h.render();
      assert.equal(state.query, "");
      assert.equal(state.value, null);
      assert.equal(state.detail, null);
      delayed.resolve(artifact());
      assert.equal(await opening, null);
      h.fresh(true);
      h.fence.update("owner-two", true);
      state = h.render();
      state = h.render();
      assert.equal(state.query, "");
      assert.equal(state.value, null);
      assert.equal(h.calls.length, 2);
    } finally {
      h.close();
    }
  }
});
test("session and offline events fence immediately before any rerender", async () => {
  for (const name of ["desk:session", "offline"]) {
    const h = setup();
    try {
      let state = h.render();
      state.submit();
      const delayed = h.pending.shift()!;
      for (const event of h.events.get(name) ?? []) event();
      delayed.resolve(page());
      state = await h.settle();
      assert.equal(state.active, false);
      assert.equal(state.value, null);
      assert.equal(state.query, "");
    } finally {
      h.close();
    }
  }
});
test("pagination is explicit and bound to submitted filter/query/snapshot; conflicts require new submit", async () => {
  const h = setup();
  try {
    let state = h.render();
    state.setQuery("original");
    state = h.render();
    state.submit();
    h.pending.shift()!.resolve(
      page(
        Array.from({ length: 20 }, (_, i) => hit(`file-${i}`)),
        21,
        20,
      ),
    );
    state = await h.settle();
    state.setQuery("not yet submitted");
    state.setKind("source");
    state = h.render();
    state.nextPage();
    const pending = h.pending.shift()!;
    assert.deepEqual(JSON.parse(String(pending.options?.body)), {
      query: "original",
      kind: "all",
      limit: 20,
      offset: 20,
      snapshot: "a".repeat(64),
    });
    pending.reject(new TestApiError("WORK_SEARCH_CHANGED", 409));
    state = await h.settle();
    assert.equal(state.value, null);
    assert.equal(state.error.code, "WORK_SEARCH_CHANGED");
    assert.equal(h.calls.length, 2);
    state.submit();
    assert.equal(JSON.parse(String(h.pending[0].options?.body)).offset, 0);
    h.pending.shift()!.resolve(page([], 0));
    await h.settle();
  } finally {
    h.close();
  }
});
test("late privacy denial clears newer search results rather than reviving older metadata", async () => {
  const h = setup();
  try {
    let state = h.render();
    state.submit();
    const old = h.pending.shift()!;
    state.submit();
    h.pending.shift()!.resolve(page());
    state = await h.settle();
    assert.ok(state.value);
    old.reject(new TestApiError("WORK_SEARCH_PRIVACY_CHANGED", 403));
    state = await h.settle();
    assert.equal(state.value, null);
    assert.equal(state.active, false);
    assert.equal(state.query, "");
  } finally {
    h.close();
  }
});
test("search integration retains navigation guards and the private/metadata split", () => {
  const read = (name: string) =>
    readFileSync(
      new URL(`../src/workspace/agent/${name}`, import.meta.url),
      "utf8",
    );
  const panel = read("RunPanel.tsx");
  assert.match(
    panel,
    /if \(guard\.busy\) return;\s*if \(guard\.dirty\) setNavigate\(next\)/,
  );
  assert.match(
    panel,
    /onClick=\{\(\) =>\s*go\(\{ id: selected, compose: false, search: !showSearch \}\)/,
  );
  assert.match(panel, /onOpenRun=\{\(id\) => go\(\{ id, compose: false \}\)\}/);
  assert.match(panel, /fresh=\{fresh && !detailRefreshing\}/);
  assert.match(panel, /visible \? \(\s*<RunWorkspace/);
  const search = read("useWorkSearch.ts");
  assert.doesNotMatch(
    search,
    /setInterval|localStorage|sessionStorage|X-Operation-Id/,
  );
  assert.doesNotMatch(
    read("WorkSearchPanel.tsx"),
    /dangerouslySetInnerHTML|\/actions|\/download|as ArtifactRecord|as SourceRecord/,
  );
});

test("previous page retains the exact snapshot and never restarts implicitly", async () => {
  const h = setup();
  try {
    let state = h.render();
    state.submit();
    const firstPage = page(
      Array.from({ length: 20 }, (_, i) => hit(`file-${i}`)),
      21,
      20,
    );
    h.pending.shift()!.resolve(firstPage);
    state = await h.settle();
    state.nextPage();
    h.pending.shift()!.resolve(page([hit("last-file")], 21));
    state = await h.settle();
    assert.equal(state.value.input.offset, 20);
    state.previousPage();
    const back = h.pending.shift()!;
    assert.deepEqual(JSON.parse(String(back.options?.body)), {
      query: "",
      kind: "all",
      limit: 20,
      offset: 0,
      snapshot: "a".repeat(64),
    });
    back.resolve(firstPage);
    state = await h.settle();
    assert.equal(state.value.input.offset, 0);
    assert.equal(state.value.page.items.length, 20);
  } finally {
    h.close();
  }
});
test("run and source choices read their exact detail endpoints before handing off", async () => {
  const h = setup();
  try {
    const run: WorkSearchHit = {
      kind: "run",
      id: "run-exact",
      title: "Work",
      timestamp: null,
      matched_fields: ["id"],
      match_reason: "exact_id",
      state: "paused",
      mode: "deterministic",
      version: 1,
      plan_revision: 1,
      source_names: [],
    };
    const source: WorkSearchHit = {
      kind: "source",
      id: "source-exact",
      title: "notes.txt",
      timestamp: null,
      matched_fields: ["id"],
      match_reason: "exact_id",
      format: "text",
      byte_count: 5,
      recorded_status: "verified",
      revision: 1,
    };
    let state = h.render();
    state.submit();
    h.pending.shift()!.resolve(page([run, source]));
    state = await h.settle();
    const opening = state.open(run);
    const read = h.pending.shift()!;
    assert.equal(read.path, "/agent-runs/run-exact");
    assert.equal(read.options, undefined);
    read.resolve({
      run: { id: run.id, version: 8 },
      steps: [],
      events: [],
      artifacts: [],
      proposals: [],
    });
    assert.equal((await opening)?.value.run.version, 8);
    state = h.render();
    const preview = state.open(source);
    const sourceRead = h.pending.shift()!;
    assert.equal(sourceRead.path, "/sources/source-exact");
    sourceRead.resolve({
      id: source.id,
      name: "notes.txt",
      format: "text",
      byte_count: 5,
      sha256: "b".repeat(64),
      status: "verified",
      revision: 1,
    });
    assert.equal((await preview)?.kind, "source");
    assert.deepEqual(
      h.calls.map((call) => call.path),
      ["/work/search", "/agent-runs/run-exact", "/sources/source-exact"],
    );
  } finally {
    h.close();
  }
});
