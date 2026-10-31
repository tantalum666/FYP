import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { register } from "node:module";
import * as React from "react";
import * as runtime from "react/jsx-runtime";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";
import { ResponseFence } from "../src/workspace/personal/responseFence.ts";
import * as policy from "../src/workspace/agent/capturePolicy.ts";
register(new URL("./fixtures/render-tsx-loader.mjs", import.meta.url));
const { CaptureProvenance } =
  await import("../src/workspace/agent/CaptureProvenance.tsx");
const { CapacityLine } =
  await import("../src/workspace/agent/RetainedCapacity.tsx");
const id = "a".repeat(32),
  hash = "b".repeat(64),
  url = "https://www.python.org/about/",
  time = "2026-10-13T09:00:00Z";
const acquisition = {
  capture_id: id,
  url,
  received_at: time,
  http_status: 200,
  response_mime: "text/html",
  response_charset: "utf-8",
  raw_sha256: hash,
  raw_byte_count: 80,
  extracted_sha256: hash,
  extracted_byte_count: 24,
  extractor_version: "static_text_v1",
  coverage: "complete_accepted_static_extraction",
  raw_retained: false,
  rendered_coverage: "unknown",
  total_lines: 2,
};
const capture = {
  id,
  state: "review",
  version: 1,
  created_at: time,
  updated_at: time,
  expires_at: "2099-10-13T09:05:00Z",
  dispatch_possible: false,
  error_code: null,
  cancel_available: true,
  url,
  label: '<img src="https://evil.invalid/x">',
  display_name: `capture-${id}.txt`,
  intent_hash: hash,
  source_id: null,
  source_status: "not_reserved",
  acquisition: null,
};
const dim = (limit: number) => ({
  limit,
  used: 0,
  remaining: limit,
  state: "known",
});
const review = {
  ...capture,
  host: "www.python.org",
  source_capacity: {
    count: dim(100),
    bytes: dim(67108864),
    file_bytes: 1048576,
  },
  history_used: 1,
};
function component(api: any) {
  const exports: any = {};
  const code = ts.transpileModule(
    readFileSync(
      new URL("../src/workspace/agent/PublicCapture.tsx", import.meta.url),
      "utf8",
    ),
    {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS,
        target: ts.ScriptTarget.ES2022,
        jsx: ts.JsxEmit.ReactJSX,
      },
    },
  ).outputText;
  new Function("require", "exports", code)((name: string) => {
    if (name === "react") return React;
    if (name === "react/jsx-runtime") return runtime;
    if (name === "./usePublicCaptures") return { usePublicCaptures: () => api };
    if (name === "../../components/DraftGuard")
      return { useDraftGuard: () => {} };
    if (name === "./capturePolicy") return policy;
    if (name === "./RetainedCapacity") return { CapacityLine };
    if (name === "./CaptureProvenance") return { CaptureProvenance };
    if (name === "./SourcePreview") return { SourcePreview: () => null };
    throw Error(name);
  }, exports);
  return exports.PublicCapture;
}
const api = (extra: any = {}) => ({
  enabled: true,
  available: true,
  busy: false,
  error: null,
  records: [],
  cursor: null,
  selected: null,
  review: null,
  pending: [],
  ...extra,
});
function render(value: any, zh = false, hidden = false) {
  const fence = new ResponseFence();
  fence.update("owner", true);
  return renderToStaticMarkup(
    React.createElement(component(value), {
      t: (en: string, cn: string) => (zh ? cn : en),
      fence,
      epoch: fence.version,
      fresh: true,
      hidden,
    }),
  );
}
test("actual bilingual intake/review states exact bounded GET disclosure, unchecked separate consents and inert URL/label", () => {
  for (const zh of [false, true]) {
    const html = render(api({ selected: capture, review }), zh);
    assert.match(html, zh ? /添加网页/ : /Add web page/);
    assert.match(html, /200/);
    assert.match(html, /100/);
    assert.match(html, /64 MiB/);
    assert.match(html, /128 KiB/);
    assert.match(html, /24 KiB/);
    assert.match(html, zh ? /不发GET/ : /no GET/);
    assert.match(html, zh ? /原始字节/ : /Raw bytes/);
    assert.match(
      html,
      zh ? /不授权其他目的地/ : /not permission for another destination/,
    );
    assert.match(html, /&lt;img/);
    assert.doesNotMatch(html, /<img|<a[ >]|<iframe|<script|<link|checked=""/);
    assert.match(html, /<button type="button" class="primary" disabled="">/);
    assert.match(html, zh ? /不会开始工作/ : /does not start Work/);
  }
});
test("disabled still renders history/local reconciliation and cancelled source provenance without implying deletion", () => {
  for (const zh of [false, true]) {
    const html = render(
      api({
        enabled: false,
        selected: {
          ...capture,
          state: "cancelled",
          cancel_available: false,
          source_status: "verified",
          source_id: "c".repeat(32),
          acquisition,
        },
      }),
      zh,
    );
    assert.match(html, zh ? /已取消/ : /Cancelled/);
    assert.match(html, zh ? /保留字节已核验/ : /Verified retained bytes/);
    assert.match(html, zh ? /检查保留文本/ : /Inspect retained text/);
    assert.match(
      html,
      zh ? /本地核验原来源/ : /Reconcile original source locally/,
    );
    assert.match(html, zh ? /不支持.*删除/ : /no capture\/source deletion/);
    assert.doesNotMatch(html, /Approve one public GET|Save local review/);
    assert.match(html, zh ? /明确选择/ : /explicitly select/);
    assert.doesNotMatch(html, /<a[ >]|<img|dangerouslySetInnerHTML/);
  }
});
test("hidden projection renders handles/status/stop without private URL source or reconcile", () => {
  const selected = Object.fromEntries(
    [
      "id",
      "state",
      "version",
      "created_at",
      "updated_at",
      "expires_at",
      "dispatch_possible",
      "error_code",
      "cancel_available",
    ].map((k) => [k, (capture as any)[k]]),
  );
  const html = render(api({ selected, records: [selected] }), false, true);
  assert.match(html, /Stop this capture/);
  assert.match(html, /Reopen/);
  assert.doesNotMatch(
    html,
    /www.python|Exact public URL|Reconcile original|Inspect retained text|capture-aaaa/,
  );
});
test("acquisition preview is safe plaintext and invalid provenance never becomes evidence", () => {
  const en = (a: string) => a;
  const html = renderToStaticMarkup(
    React.createElement(CaptureProvenance, { value: acquisition, t: en }),
  );
  assert.match(html, /Raw response was not retained/);
  assert.match(html, /HTTP 200/);
  assert.match(html, /utf-8/);
  assert.match(html, /Extracted SHA-256/);
  assert.match(html, /24 bytes/);
  assert.match(html, /2 generated lines/);
  assert.match(html, /complete accepted static extraction only/);
  assert.match(html, /Rendered-page coverage is unknown/);
  assert.match(html, /not the original HTML/);
  assert.doesNotMatch(html, /<a[ >]|<img|<iframe/);
  for (const field of [
    "http_status",
    "raw_retained",
    "rendered_coverage",
    "extracted_sha256",
    "raw_byte_count",
  ]) {
    const invalid = renderToStaticMarkup(
      React.createElement(CaptureProvenance, {
        value: { ...acquisition, [field]: "evil" },
        t: en,
      }),
    );
    assert.match(invalid, /metadata is unavailable or invalid/);
    assert.doesNotMatch(invalid, /www.python/);
  }
});
