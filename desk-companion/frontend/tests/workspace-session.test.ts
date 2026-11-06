import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import ts from "typescript";
import { Hooks } from "./helpers/hooks.ts";

class ApiError extends Error {
  status: number;
  constructor(status: number) {
    super("fixture");
    this.status = status;
  }
}

test("actual session hook preserves an offline identity but clears rejected access", async () => {
  const hooks = new Hooks();
  const events = new EventTarget();
  const errors: unknown[] = [];
  const owner = { principal: { kind: "owner", id: "owner" } };
  let next: () => Promise<any> = async () => owner;
  const source = readFileSync(
    new URL("../src/useWorkspaceSession.ts", import.meta.url),
    "utf8",
  );
  const code = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  }).outputText;
  const module = { exports: {} as any };
  new Function("require", "module", "exports", "window", code)(
    (name: string) =>
      name === "react"
        ? hooks.react
        : name === "./api"
          ? { ApiError }
          : { openSession: () => next() },
    module,
    module.exports,
    events,
  );
  const render = () =>
    hooks.render(() =>
      module.exports.useWorkspaceSession((error: unknown) =>
        errors.push(error),
      ),
    );
  render();
  await new Promise((resolve) => setImmediate(resolve));
  let current = render();
  assert.equal(current.session, owner);
  next = async () => {
    throw new ApiError(0);
  };
  await current.recoverSession();
  current = render();
  assert.equal(current.session, owner);
  next = async () => {
    throw new ApiError(403);
  };
  await current.recoverSession();
  current = render();
  assert.equal(current.session, null);
  assert.equal(current.expired, true);
  assert.equal(errors.length, 2);
  hooks.close();
});
