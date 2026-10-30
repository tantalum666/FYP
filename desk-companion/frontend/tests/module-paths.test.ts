import assert from "node:assert/strict";
import { readdirSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

// Check paths rather than the host's resolution behavior: Local validation must reject
// ambiguous extensionless TS/TSX imports before they reach a case-insensitive Mac.
// Declaration companions are intentional and are not implementation modules.
function collisions(paths: string[]) {
  const modules = new Map<string, string[]>();
  const directories = new Map<string, Set<string>>();
  for (const path of [...paths].sort()) {
    if (!/\.tsx?$/i.test(path) || /\.d\.ts$/i.test(path)) continue;
    const key = path.replace(/\.tsx?$/i, "").toLowerCase();
    modules.set(key, [...(modules.get(key) ?? []), path]);
    const segments = path.split("/");
    for (let i = 1; i < segments.length; i++) {
      const directory = segments.slice(0, i).join("/");
      const variants = directories.get(directory.toLowerCase()) ?? new Set();
      variants.add(directory);
      directories.set(directory.toLowerCase(), variants);
    }
  }
  return {
    modules: [...modules.values()].filter((paths) => paths.length > 1),
    directories: [...directories.values()]
      .filter((paths) => paths.size > 1)
      .map((paths) => [...paths]),
  };
}

function sourcePaths(root: string, relative = ""): string[] {
  return readdirSync(join(root, relative), { withFileTypes: true })
    .flatMap((entry) => {
      const path = relative ? `${relative}/${entry.name}` : entry.name;
      if (entry.isDirectory()) return sourcePaths(root, path);
      // Do not silently omit a future linked source subtree from this guard.
      assert.equal(
        entry.isSymbolicLink(),
        false,
        `Unsupported source symlink: ${path}`,
      );
      return entry.isFile() ? [path] : [];
    })
    .sort();
}

test("all frontend source module paths are unambiguous on case-insensitive filesystems", () => {
  const paths = sourcePaths(fileURLToPath(new URL("../src/", import.meta.url)));
  assert.ok(
    paths.some((path) => /\.ts$/.test(path)),
    "TS source tree must be scanned",
  );
  assert.ok(
    paths.some((path) => /\.tsx$/.test(path)),
    "TSX source tree must be scanned",
  );
  assert.deepEqual(
    collisions(paths),
    { modules: [], directories: [] },
    "Rename colliding implementation modules/directories to meaningfully distinct names; extensionless imports cannot depend on case or TS/TSX extension",
  );
});

test("module guard catches nested mixed-extension and same-extension case collisions", () => {
  assert.deepEqual(
    collisions([
      "workspace/agent/publicCapture.ts",
      "workspace/agent/PublicCapture.tsx",
      "nested/Thing.ts",
      "nested/thing.ts",
      "views/Panel.tsx",
      "views/panel.tsx",
      "same/Exact.ts",
      "same/Exact.tsx",
    ]).modules,
    [
      ["nested/Thing.ts", "nested/thing.ts"],
      ["same/Exact.ts", "same/Exact.tsx"],
      ["views/Panel.tsx", "views/panel.tsx"],
      ["workspace/agent/PublicCapture.tsx", "workspace/agent/publicCapture.ts"],
    ],
  );
});

test("module guard catches case-only directories even with different child basenames", () => {
  assert.deepEqual(collisions(["views/Foo/a.ts", "views/foo/b.tsx"]), {
    modules: [],
    directories: [["views/Foo", "views/foo"]],
  });
});

test("module guard permits distinct directories, declaration companions and non-module assets", () => {
  assert.deepEqual(
    collisions([
      "a/Item.ts",
      "b/item.tsx",
      "a/Item.d.ts",
      "a/Item.css",
      "workspace/agent/PublicCapture.tsx",
      "workspace/agent/capturePolicy.ts",
    ]),
    { modules: [], directories: [] },
  );
});
