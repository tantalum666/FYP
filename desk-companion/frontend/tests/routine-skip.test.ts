import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import { Children, isValidElement, type ReactElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";
import { isJourneyAdvice, proposalDecisionNotice } from "../src/workspace/proposalDecision.ts";
import { Hooks } from "./helpers/hooks.ts";

function controls(node: ReactNode, tag: string): ReactElement<any>[] {
  return Children.toArray(node).flatMap(child => {
    if (!isValidElement<{ children?: ReactNode }>(child)) return [];
    return child.type === tag ? [child] : controls(child.props.children, tag);
  });
}

test("the review card confirms only the chosen original routine and cancels without a choice", () => {
  const hooks = new Hooks();
  const source = readFileSync(new URL("../src/workspace/ProposalActionCard.tsx", import.meta.url), "utf8");
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  const require = createRequire(import.meta.url);
  const component = {} as { ProposalActionCard: (props: any) => ReactElement };
  new Function("require", "exports", compiled)((name: string) => {
    if (name === "react") return hooks.react;
    if (name === "./proposalDecision") return { isJourneyAdvice };
    return name.startsWith(".") ? {} : require(name);
  }, component);

  const t = (_en: string, zh: string) => zh;
  const choices = [
    { routine_id: "hk", title: "晨间简报", occurrence_key: "2026-10-13T09:00", timezone: "Asia/Hong_Kong" },
    { routine_id: "la", title: "晨间简报", occurrence_key: "2026-10-12T09:00", timezone: "America/Los_Angeles" },
  ];
  const calls: unknown[][] = [];
  const render = () => hooks.render(() => component.ProposalActionCard({
    proposal: { kind: "routine_skip", data: { choices }, expires_at: "2026-10-12T00:05:00Z" },
    busy: false, t, onDecision: (...args: unknown[]) => calls.push(args),
  }));
  const initial = render();
  const markup = renderToStaticMarkup(initial);
  assert.match(markup, /晨间简报 · 2026-10-13 09:00 · Asia\/Hong_Kong/);
  assert.match(markup, /晨间简报 · 2026-10-12 09:00 · America\/Los_Angeles/);
  const [confirm, cancel] = controls(initial, "button");
  assert.equal(confirm.props.disabled, true);
  assert.equal(cancel.props.disabled, false);
  assert.deepEqual(calls, []);
  cancel.props.onClick();
  const [select] = controls(initial, "select");
  select.props.onChange({ target: { value: "la" } });
  const [chosen] = controls(render(), "button");
  assert.equal(chosen.props.disabled, false);
  chosen.props.onClick();
  assert.deepEqual(calls, [["cancel"], ["confirm", { routine_id: "la" }]]);
  assert.equal(proposalDecisionNotice({ kind: "routine_skip" }, "confirm", undefined, t), "已跳过这一次提醒。");
});
