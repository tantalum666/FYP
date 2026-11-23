import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import ts from "typescript";
import { Hooks } from "./helpers/hooks.ts";
import { ResponseFence } from "../src/workspace/personal/responseFence.ts";
import type { PendingWrite } from "../src/api.ts";

const require = createRequire(import.meta.url);
const tick = () => new Promise<void>((done) => setImmediate(done));

function loadModule(file: string, mocks: Record<string, unknown>) {
  const source = readFileSync(new URL(`../src/${file}`, import.meta.url), "utf8");
  const code = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      jsx: ts.JsxEmit.ReactJSX,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
  const exports: any = {};
  new Function("require", "exports", "window", "sessionStorage", code)(
    (name: string) => mocks[name] ?? (name.startsWith(".") ? {} : require(name)),
    exports,
    mocks.window,
    mocks.sessionStorage,
  );
  return exports;
}

function nodes(tree: any): any[] {
  if (Array.isArray(tree)) return tree.flatMap(nodes);
  if (tree == null || typeof tree === "boolean") return [];
  return [tree, ...nodes(tree.props?.children)];
}

function setup(connected = true) {
  const opened: unknown[][] = [];
  const hooks = new Hooks(),
    window = Object.assign(new EventTarget(), {
      setTimeout: () => 0,
      open: (...args: unknown[]) => opened.push(args),
    });
  const view = {
    data: {
      principal: { kind: "owner", id: "owner" },
      personal_context_visible: true,
      google: { connected, connected_at: "same-connection" },
    },
    offline: false,
    stale: false,
    refresh: async () => {},
  };
  const status = {
    ...view.data.google,
    configured: true,
    version: "grant",
    review_version: connected ? "same-visible-status" : null,
  };
  const writes: any[] = [];
  const accounts: any[] = [];
  const storage = new Map<string, string>();
  const api = loadModule("api.ts", {
    window,
    sessionStorage: {
      getItem: (key: string) => storage.get(key) ?? null,
      setItem: (key: string, value: string) => storage.set(key, value),
      removeItem: (key: string) => storage.delete(key),
    },
    "./native": {
      apiFetch: (path: string, init: { body: string; headers: Record<string, string> }) => {
        if (path === "/google/status") return Response.json(status);
        if (path === "/shares") return Response.json({ shares: [] });
        return new Promise((resolve, reject) => {
          const key = init.headers["X-Operation-Id"];
          const call = {
            path,
            resolve: (body: unknown, httpStatus = 200) =>
              resolve(Response.json(body, { status: httpStatus })),
            reject,
          };
          if (key) writes.push({ ...call, operation: { path, body: JSON.parse(init.body), key } });
          else accounts.push(call);
        });
      },
    },
  });
  const { DataPanel } = loadModule("workspace/DataPanel.tsx", {
    window,
    react: hooks.react,
    "../components/DraftGuard": { useDraftGuard() {} },
    "./WorkspaceContext": { useWorkspace: () => view },
    "./personal/responseFence": { ResponseFence },
    "./GoogleImportReview": loadModule("workspace/GoogleImportReview.tsx", {}),
    "../api": api,
  });
  const render = () => nodes(hooks.render(() => DataPanel({ t: (en: string) => en })));
  const click = (label: string) => {
    const button = render().find((node) => node.type === "button" && node.props.children === label);
    assert.ok(button && !button.props.disabled, label);
    button.props.onClick();
  };
  const preview = (title: string) => ({
    preview_id: title,
    kind: "google_refresh",
    warnings: [],
    metadata: { review_version: status.review_version },
    rows: [
      {
        status: "unchanged",
        existing_id: "copy-1",
        event: { title, start_local: "2026-10-02T09:00", timezone: "UTC" },
      },
    ],
  });
  const recover = (operation: PendingWrite, result: unknown) => {
    api.clearPending(operation.key);
    window.dispatchEvent(
      new CustomEvent("desk:write-recovered", { detail: { operation, result } }),
    );
  };
  return {
    render,
    click,
    view,
    window,
    writes,
    accounts,
    opened,
    preview,
    recover,
    clearPending: () => api.clearPending(),
    retry: () => api.retryPending(),
    unmount: () => {
      hooks.close();
      hooks.slots = [];
    },
    close: () => hooks.close(),
  };
}

test("a rejected new request cannot take ownership of an earlier session's pending operation", async () => {
  const h = setup();
  try {
    h.render();
    await tick();
    h.click("Refresh imported events");
    const old = h.writes[0];
    h.window.dispatchEvent(new Event("desk:session"));
    h.render();
    await tick();
    h.click("Preview date range");
    await tick();
    h.click("Refresh imported events");
    await tick();
    assert.equal(h.writes.length, 1);
    const privateRows = h.preview("Earlier private review");
    h.recover(old.operation, privateRows);
    old.resolve(privateRows);
    await tick();
    assert.ok(!h.render().includes(privateRows.preview_id));
  } finally {
    h.close();
  }
});

for (const startBeforeReset of [true, false]) {
  test(`a reopened panel accepts recovery only when started in its active session (${startBeforeReset})`, async () => {
    const h = setup();
    try {
      h.render();
      await tick();
      h.click("Refresh imported events");
      h.writes[0].reject(new Error("Lost response"));
      await tick();
      const previous = startBeforeReset ? h.retry() : null;
      h.unmount();
      if (startBeforeReset) h.window.dispatchEvent(new Event("desk:session"));
      h.render();
      await tick();
      h.render();
      const retry = previous ?? h.retry();
      const rows = h.preview("Recovered private review");
      h.writes[1].resolve(rows);
      await retry;
      assert.equal(h.render().includes(rows.preview_id), !startBeforeReset);
    } finally {
      h.close();
    }
  });
}

for (const result of ["discarded", "expired"]) {
  test(`a late ${result} result cannot disturb the new owner's review`, async () => {
    const h = setup();
    try {
      h.render();
      await tick();
      h.click("Refresh imported events");
      h.writes[0].resolve(h.preview("First review"));
      await tick();
      h.click("Discard preview");
      const discard = h.writes[1];
      h.window.dispatchEvent(new Event("desk:session"));
      h.clearPending();
      h.render();
      await tick();
      h.click("Refresh imported events");
      h.writes[2].resolve(h.preview("New owner's review"));
      await tick();
      if (result === "discarded") discard.resolve({ discarded: true });
      else discard.resolve({ error: { code: "IMPORT_EXPIRED" } }, 410);
      h.recover(discard.operation, { discarded: true });
      await tick();
      const nodes = h.render();
      assert.ok(nodes.includes("New owner's review"));
      assert.ok(!nodes.some((node) => node.props?.role === "alert"));
    } finally {
      h.close();
    }
  });
}

test("the owner can resolve one unverified copy in the compact review", async () => {
  const h = setup();
  try {
    h.render();
    await tick();
    h.click("Refresh imported events");
    const review = h.preview("Keep or replace");
    const row = review.rows[0];
    h.writes[0].resolve({
      ...review,
      rows: [
        { ...row, status: "unverified", proposed_status: "changed", existing_id: "choose-me" },
        { ...row, status: "unverified", proposed_status: "deleted", existing_id: "keep-me" },
        { ...row, status: "unavailable", existing_id: "inaccessible" },
      ],
    });
    await tick();
    const rows = h.render();
    assert.ok(rows.includes("0 to update · 0 to remove · 3 to keep"));
    assert.ok(rows.includes("Unavailable on Google · keep local copy"));
    const choices = rows.filter((n) => n.type === "input" && n.props.type === "checkbox");
    assert.deepEqual(
      choices.map((n) => [n.props.value, n.props.checked]),
      [
        ["choose-me", false],
        ["keep-me", false],
      ],
    );
    choices[0].props.onChange({ currentTarget: { value: "choose-me", checked: true } });
    assert.ok(h.render().includes("1 to update · 0 to remove · 2 to keep"));
    h.click("Confirm local refresh");
    const confirm = h.writes[1];
    assert.equal(confirm.operation.path, "/exchange/Keep or replace/apply");
    assert.deepEqual(confirm.operation.body, {
      replace_matching: false,
      resolve_event_ids: ["choose-me"],
    });
    confirm.resolve({ updated: 1, removed: 0, kept: 2 });
    await tick();
    assert.ok(h.render().includes("1 updated · 0 removed · 2 kept"));
  } finally {
    h.close();
  }
});

for (const connected of [false, true]) {
  test(`a delayed Google ${connected ? "disconnect" : "connect"} result stays in its session`, async () => {
    const h = setup(connected);
    try {
      h.render();
      await tick();
      h.click(connected ? "Disconnect" : "Connect Google");
      h.window.dispatchEvent(new Event("desk:session"));
      h.render();
      await tick();
      h.accounts[0].resolve(
        connected
          ? { provider_revocation_confirmed: true }
          : { url: "https://fixture.invalid/consent" },
      );
      await tick();
      assert.deepEqual(h.opened, []);
      assert.ok(!h.render().some((n) => n.props?.role === "status"));
    } finally {
      h.close();
    }
  });
}

for (const change of ["principal", "desk:session", "desk:personal-context"]) {
  test(`a delayed Google review and its recovery stay in their original epoch after ${change}`, async () => {
    const h = setup();
    try {
      h.render();
      await tick();
      h.click("Refresh imported events");
      const old = h.writes[0],
        privateRows = h.preview("Previous owner's private meeting");
      if (change === "principal") h.view.data.principal.id = "other-owner";
      else h.window.dispatchEvent(new Event(change));
      h.render();
      await tick();
      h.render();
      old.resolve(privateRows);
      await tick();
      assert.ok(!h.render().includes(privateRows.preview_id));
      h.recover(old.operation, privateRows);
      assert.ok(!h.render().includes(privateRows.preview_id));

      h.click("Refresh imported events");
      const current = h.writes[1],
        currentRows = h.preview("Current owner's meeting");
      current.reject(new Error("Lost response"));
      await tick();
      const retry = h.retry();
      assert.deepEqual(h.writes[2].operation, current.operation);
      h.writes[2].resolve(currentRows);
      await retry;
      assert.ok(h.render().includes(currentRows.preview_id));
    } finally {
      h.close();
    }
  });
}
