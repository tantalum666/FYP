import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { renderToStaticMarkup } from "react-dom/server";
import * as jsxRuntime from "react/jsx-runtime";
import ts from "typescript";

// Source/SSR regressions, not browser layout measurements. Exercise the actual
// production list JSX without mounting its network and privacy-aware parent.
const panel = readFileSync(
  new URL("../src/workspace/agent/RunPanel.tsx", import.meta.url),
  "utf8",
);
const source = ts.createSourceFile(
  "RunPanel.tsx",
  panel,
  ts.ScriptTarget.Latest,
  true,
  ts.ScriptKind.TSX,
);
const lists: ts.JsxElement[] = [];
function visit(node: ts.Node) {
  if (
    ts.isJsxElement(node) &&
    node.openingElement.attributes.properties.some(
      (attr) =>
        ts.isJsxAttribute(attr) &&
        attr.name.getText(source) === "className" &&
        attr.initializer &&
        ts.isStringLiteral(attr.initializer) &&
        attr.initializer.text === "agent-run-list",
    )
  )
    lists.push(node);
  ts.forEachChild(node, visit);
}
visit(source);
assert.equal(lists.length, 1);
const compiled = ts.transpileModule(
  `export function render(value, selected, guard, t, go, stateLabel, modeLabel) {
    return (${lists[0].getText(source)});
  }`,
  {
    compilerOptions: {
      jsx: ts.JsxEmit.ReactJSX,
      module: ts.ModuleKind.CommonJS,
    },
  },
).outputText;
const module = { exports: {} as { render: (...args: any[]) => any } };
new Function("require", "exports", compiled)((name: string) => {
  assert.equal(name, "react/jsx-runtime");
  return jsxRuntime;
}, module.exports);
const css = readFileSync(
  new URL("../src/workspace/agent/agent.css", import.meta.url),
  "utf8",
);
function baseRule(selector: string) {
  const base = css.slice(0, css.indexOf("@media"));
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const rule = base.match(new RegExp(`(?:^|\\n)${escaped}\\s*\\{([^}]*)\\}`));
  assert.ok(rule, `Missing base rule for ${selector}`);
  return rule[1];
}

test("bounded retained Work list scrolls without flex-shrinking its grid cards", () => {
  const list = baseRule(".agent-run-list");
  assert.match(list, /display:\s*flex\s*;/);
  assert.match(list, /flex-direction:\s*column\s*;/);
  assert.match(list, /max-height:\s*18rem\s*;/);
  assert.match(list, /overflow-y:\s*auto\s*;/);
  // Previously default flex-shrink: 1 compressed the overflow-hidden goal row.
  assert.match(baseRule(".agent-run-choice"), /flex-shrink:\s*0\s*;/);
  assert.match(
    css,
    /@media \(min-width: 850px\)[\s\S]*?\.agent-run-list\s*\{\s*max-height:\s*32rem\s*;/,
  );
});

test("retained Work goal wrapping and two-line clamp remain scoped to its card", () => {
  const title = baseRule(".agent-run-choice strong");
  assert.match(title, /display:\s*-webkit-box\s*;/);
  assert.match(title, /-webkit-line-clamp:\s*2\s*;/);
  assert.match(title, /-webkit-box-orient:\s*vertical\s*;/);
  assert.match(title, /overflow-wrap:\s*anywhere\s*;/);
});

function renderList(zh: boolean, busy = false, selected = "run-0") {
  const t = (en: string, cn: string) => (zh ? cn : en);
  const calls: unknown[] = [];
  const runs = Array.from({ length: 100 }, (_, i) => ({
    id: `run-${i}`,
    goal:
      i === 99
        ? ""
        : zh
          ? `工作目标${i}：${"保留可辨认的长标题".repeat(20)}`
          : `Work goal ${i}: ${"long-goal-without-spaces".repeat(20)}`,
    state: "cancelled",
    mode: "deterministic",
    updated_at: "2026-10-13T11:00:00Z",
  }));
  const node = module.exports.render(
    { runs },
    selected,
    { busy },
    t,
    (next: unknown) => calls.push(next),
    () => t("Cancelled", "已取消"),
    () => t("Local evidence compilation", "本地证据整理"),
  );
  return { node, calls, markup: renderToStaticMarkup(node) };
}

test("production retained list keeps distinct long goals, status and fallback in EN/ZH", () => {
  for (const zh of [false, true]) {
    const { markup } = renderList(zh);
    assert.equal((markup.match(/<strong>/g) ?? []).length, 100);
    assert.match(markup, zh ? /工作目标0：/ : /Work goal 0:/);
    assert.match(markup, zh ? /工作目标98：/ : /Work goal 98:/);
    assert.match(markup, zh ? /未命名工作/ : /Untitled work/);
    assert.match(markup, zh ? /已取消/ : /Cancelled/);
    assert.equal((markup.match(/aria-current="true"/g) ?? []).length, 1);
    assert.doesNotMatch(markup, /disabled=""/);
    assert.equal(
      (renderList(zh, true).markup.match(/disabled=""/g) ?? []).length,
      100,
    );
  }
});

test("production retained card selection opens only a different exact run", () => {
  const { node, calls } = renderList(false);
  const cards = node.props.children[1];
  cards[0].props.onClick();
  assert.deepEqual(calls, []);
  cards[98].props.onClick();
  assert.deepEqual(calls, [{ id: "run-98", compose: false }]);
});
