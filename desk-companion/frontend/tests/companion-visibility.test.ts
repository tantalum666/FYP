import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import ts from "typescript";

// Exercise the expression actually wired to PageCompanion, rather than a
// duplicate visibility policy. These are source-level regressions; browser
// hit testing and pointer interactions require the separate acceptance run.
function blockedExpression(relativePath: string) {
  const text = readFileSync(new URL(relativePath, import.meta.url), "utf8");
  const source = ts.createSourceFile(
    relativePath,
    text,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TSX,
  );
  const expressions: string[] = [];
  function visit(node: ts.Node) {
    if (
      ts.isJsxSelfClosingElement(node) &&
      node.tagName.getText(source) === "PageCompanion"
    ) {
      const blocked = node.attributes.properties.find(
        (attribute) =>
          ts.isJsxAttribute(attribute) &&
          attribute.name.getText(source) === "blocked",
      );
      assert.ok(blocked && ts.isJsxAttribute(blocked));
      assert.ok(blocked.initializer && ts.isJsxExpression(blocked.initializer));
      assert.ok(blocked.initializer.expression);
      expressions.push(blocked.initializer.expression.getText(source));
    }
    ts.forEachChild(node, visit);
  }
  visit(source);
  assert.equal(expressions.length, 1);
  return (state: Record<string, unknown>): boolean =>
    new Function(...Object.keys(state), `return (${expressions[0]});`)(
      ...Object.values(state),
    );
}

const webBlocked = blockedExpression("../src/App.tsx");
const deviceBlocked = blockedExpression("../src/device/DeviceApp.tsx");
const webState = {
  page: "today",
  editor: null,
  detail: null,
  showReminders: false,
  leavePage: null,
  workspacePanel: null,
};

test("Web settings temporarily hide A1 and leaving settings restores visibility", () => {
  // Repeat navigation: the privacy checkbox must remain reachable even after
  // a previous settings visit or an arbitrary saved companion placement.
  for (let visit = 0; visit < 3; visit++) {
    assert.equal(webBlocked({ ...webState, page: "device" }), true);
    for (const page of ["today", "calendar", "tasks", "records"])
      assert.equal(webBlocked({ ...webState, page }), false);
  }
});

test("Web review, edit and management panels still hide A1 on every page", () => {
  for (const page of ["today", "calendar", "tasks", "records", "device"])
    for (const panel of [
      "editor",
      "detail",
      "showReminders",
      "leavePage",
      "workspacePanel",
    ])
      assert.equal(webBlocked({ ...webState, page, [panel]: true }), true);
});

test("the independent device display keeps A1 and only yields to its panels", () => {
  const state = { panel: null, editor: null, detail: null, reminders: false };
  assert.equal(deviceBlocked(state), false);
  for (const panel of Object.keys(state)) {
    assert.equal(deviceBlocked({ ...state, [panel]: true }), true);
    assert.equal(deviceBlocked(state), false);
  }
});

test("temporary blocking uses the existing hidden root without persisting a new mode", () => {
  const companion = readFileSync(
    new URL("../src/companion/PageCompanion.tsx", import.meta.url),
    "utf8",
  );
  const css = readFileSync(
    new URL("../src/companion/companion.css", import.meta.url),
    "utf8",
  );
  assert.match(companion, /hidden=\{blocked\}/);
  assert.match(companion, /const moving = [^;]*!blocked;/);
  assert.match(
    css,
    /\.a1-companion\[hidden\]\s*\{\s*display:\s*none !important;/,
  );
  const blockingEffect = companion.match(
    /useEffect\(\(\) => \{\s*if \(blocked\) \{([\s\S]*?)\}\s*\}, \[blocked\]\)/,
  );
  assert.ok(blockingEffect);
  assert.match(blockingEffect[1], /cancelDrag\(\)/);
  assert.match(blockingEffect[1], /cancelResize\(\)/);
  assert.doesNotMatch(
    blockingEffect[1],
    /persist\(|store\(|setPreference\(|chooseMode\(|localStorage/,
  );
});
