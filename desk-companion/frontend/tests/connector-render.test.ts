import assert from "node:assert/strict";
import test from "node:test";
import { registerHooks } from "node:module";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import ts from "typescript";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import type { ConnectorIntent } from "../src/workspace/connectors/types.ts";

// Production component markup, not a mounted browser or pointer-interaction test.
registerHooks({
  resolve(specifier, context, next) {
    if (specifier.startsWith(".") && context.parentURL) {
      const base = new URL(specifier, context.parentURL);
      for (const extension of [".ts", ".tsx"]) {
        const candidate = new URL(base.href + extension);
        if (existsSync(candidate)) return next(candidate.href, context);
      }
    }
    return next(specifier, context);
  },
  load(url, context, next) {
    if (url.startsWith("file:") && /\.tsx?$/.test(url))
      return {
        format: "module",
        shortCircuit: true,
        source: ts.transpileModule(readFileSync(fileURLToPath(url), "utf8"), {
          compilerOptions: {
            module: ts.ModuleKind.ESNext,
            target: ts.ScriptTarget.ES2022,
            jsx: ts.JsxEmit.ReactJSX,
            verbatimModuleSyntax: true,
          },
        }).outputText,
      };
    if (url.endsWith(".css"))
      return {
        format: "module",
        shortCircuit: true,
        source: "export default undefined;",
      };
    return next(url, context);
  },
});
const { ConnectorIntentDetail } =
  await import("../src/workspace/connectors/ConnectorIntentDetail.tsx");
const hash = "a".repeat(64);
const intent: ConnectorIntent = {
  id: "b".repeat(32),
  state: "review",
  version: 1,
  intent_hash: hash,
  created_at: "2026-10-13T05:00:00Z",
  updated_at: "2026-10-13T05:00:00Z",
  expires_at: "2030-01-01T00:00:00Z",
  dispatched: false,
  cancel_requested: false,
  intent: {
    tool_id: "mcp.public.lookup",
    connector_id: "public",
    tool_name: "lookup",
    endpoint: "https://connector.example.test/mcp",
    server_name: "Configured fixture",
    server_version: "1.0",
    destination_scope: "Public fixture",
    effect: "read",
    arguments: { secret: "PRIVATE_ARG", text: '<script>alert("x")</script>' },
    data_policy: "public_or_synthetic",
    descriptor_sha256: hash,
    grant_sha256: hash,
    notice: "PRIVATE_NOTICE",
    provider_destination: {
      id: "model-id",
      kind: "text",
      provider: "ActualConfiguredProvider",
      endpoint: "https://model.example.test/generate",
    },
  },
};
const noop = () => {};
const base = {
  intent,
  privateVisible: true,
  fresh: true,
  reviewable: true,
  acknowledged: false,
  approvalLocked: false,
  cancellationLocked: false,
  onAcknowledge: noop,
  onApprove: noop,
  onCancel: noop,
};
const render = (props = {}, zh = false) =>
  renderToStaticMarkup(
    createElement(ConnectorIntentDetail, {
      ...base,
      t: (en: string, cn: string) => (zh ? cn : en),
      ...props,
    }),
  );

test("actual English and Chinese review markup shows exact endpoint, configured server, tool, arguments, effect and binding", () => {
  for (const zh of [false, true]) {
    const markup = render({}, zh);
    for (const expected of [
      "https://connector.example.test/mcp",
      "Configured fixture",
      "lookup",
      "PRIVATE_ARG",
      "PRIVATE_NOTICE",
      hash,
      "https://model.example.test/generate",
      "ActualConfiguredProvider",
    ])
      assert.ok(markup.includes(expected));
    assert.match(
      markup,
      zh ? /读取 · 参数仍会传出/ : /Read · arguments still leave/,
    );
    assert.match(markup, zh ? /有界摘录/ : /bounded excerpt/);
    assert.match(markup, /type="checkbox"/);
    assert.doesNotMatch(markup, /checked=""/);
    assert.match(markup, /<button[^>]*class="primary"[^>]*disabled=""/);
    assert.doesNotMatch(markup, /<script|<a\b/);
    assert.match(markup, /&lt;script&gt;/);
  }
});

test("hidden detail renders only safe status and Cancel even when accidentally given a full object", () => {
  for (const zh of [false, true]) {
    const markup = render(
      {
        privateVisible: false,
        approvalLocked: true,
        intent: {
          ...intent,
          result: {
            text: ["PRIVATE_RESULT"],
            structured_content: { value: "PRIVATE_STRUCTURE" },
            is_error: false,
            untrusted: true,
            verified: false,
            sha256: hash,
            snapshot_sha256: hash,
          },
        },
      },
      zh,
    );
    assert.doesNotMatch(
      markup,
      /PRIVATE|Configured fixture|connector\.example|model\.example|ActualConfigured|type="checkbox"|Approve this exact|批准此次完整/,
    );
    assert.match(markup, zh ? /取消此次调用/ : /Cancel this call/);
    assert.doesNotMatch(markup, /disabled=""/);
  }
});

test("pending or unknown approval cannot disable independent cancellation", () => {
  const markup = render({ approvalLocked: true, acknowledged: true });
  assert.match(markup, /<button[^>]*class="primary"[^>]*disabled=""/);
  const cancelButton = markup.match(
    /<button[^>]*class="secondary connector-stop"[^>]*>/,
  )?.[0];
  assert.ok(cancelButton);
  assert.doesNotMatch(cancelButton, /disabled/);
  assert.match(
    render({ fresh: false }),
    /class="secondary connector-stop" disabled=""/,
  );
});

test("observed results are escaped plain text with independent-verification caveat, never active links or markup", () => {
  const observed = {
    ...intent,
    state: "observed_result",
    result: {
      text: [
        '<img src=x onerror="steal()"> [click](javascript:steal()) <a href="https://evil.test">claim success</a>',
      ],
      structured_content: { html: "<script>execute()</script>" },
      is_error: false,
      untrusted: true,
      verified: false,
      sha256: hash,
      snapshot_sha256: hash,
    },
  };
  for (const zh of [false, true]) {
    const markup = render({ intent: observed }, zh);
    assert.match(markup, zh ? /尚未独立核验/ : /not independently verified/);
    assert.match(
      markup,
      zh ? /未受信任的服务器结果/ : /Untrusted server result/,
    );
    assert.match(markup, /&lt;img/);
    assert.match(markup, /&lt;script&gt;/);
    assert.doesNotMatch(
      markup,
      /<img|<script|<a\b|type="checkbox"|class="primary"/,
    );
  }
});

test("unknown effect is not rendered as success or as an executable retry", () => {
  const markup = render({
    intent: { ...intent, state: "unknown_effect", dispatched: true },
    reviewable: false,
  });
  assert.match(markup, /Outcome unknown · do not repeat the call/);
  assert.match(markup, /does not retry external execution or claim rollback/);
  assert.doesNotMatch(markup, /<button|type="checkbox"/);
});
