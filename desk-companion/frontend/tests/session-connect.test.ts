import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import ts from "typescript";

class ApiError extends Error {
  code: string;
  status: number;
  constructor(code: string, status: number) {
    super(code);
    this.code = code;
    this.status = status;
  }
}

function sessionModule(request: (path: string, options?: any) => Promise<any>) {
  const source = readFileSync(
    new URL("../src/session.ts", import.meta.url),
    "utf8",
  );
  const code = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  }).outputText;
  const module = { exports: {} as any };
  new Function("require", "module", "exports", code)(
    (name: string) => {
      assert.equal(name, "./api");
      return { ApiError, request };
    },
    module,
    module.exports,
  );
  return module.exports as { openSession: () => Promise<any> };
}

test("concurrent surfaces share one passwordless bootstrap and never replay business writes", async () => {
  const calls: Array<{ path: string; options?: any }> = [];
  const session = { principal: { kind: "owner", id: "owner" } };
  const module = sessionModule(async (path, options) => {
    calls.push({ path, options });
    if (path === "/session") throw new ApiError("AUTH_REQUIRED", 401);
    return session;
  });
  const replies = await Promise.all([
    module.openSession(),
    module.openSession(),
    module.openSession(),
  ]);
  assert.deepEqual(replies, [session, session, session]);
  assert.deepEqual(calls, [
    { path: "/session", options: undefined },
    { path: "/session/connect", options: { method: "POST", body: "{}" } },
  ]);
});

test("a valid connected identity does not bootstrap or change its role", async () => {
  const calls: string[] = [];
  const paired = { principal: { kind: "display", id: "fixture-screen" } };
  const module = sessionModule(async (path) => {
    calls.push(path);
    return paired;
  });
  assert.equal(await module.openSession(), paired);
  assert.deepEqual(calls, ["/session"]);
});

test("denied or failed connection is surfaced without retry loops and allows an explicit retry", async () => {
  let attempts = 0;
  const module = sessionModule(async (path) => {
    if (path === "/session") throw new ApiError("AUTH_REQUIRED", 401);
    attempts += 1;
    if (attempts === 1) throw new ApiError("LOCAL_OWNER_UNAVAILABLE", 403);
    return { principal: { kind: "owner", id: "owner" } };
  });
  await assert.rejects(
    module.openSession(),
    (error: ApiError) => error.status === 403,
  );
  assert.equal(attempts, 1);
  assert.equal((await module.openSession()).principal.kind, "owner");
  assert.equal(attempts, 2);
});

test("an offline session read does not mint another identity", async () => {
  const calls: string[] = [];
  const module = sessionModule(async (path) => {
    calls.push(path);
    throw new ApiError("CONNECTION_LOST", 0);
  });
  await assert.rejects(module.openSession());
  assert.deepEqual(calls, ["/session"]);
});
