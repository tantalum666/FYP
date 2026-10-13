import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { ResponseFence } from "../src/workspace/personal/responseFence.ts";
import type {
  WorkSearchHit,
  WorkSearchResponse,
} from "../src/workspace/agent/workSearch.ts";

// Render real production components with React, not copied markup. This is SSR
// coverage; mounted browser interactions and layout acceptance remain separate.
register(new URL("./fixtures/render-tsx-loader.mjs", import.meta.url));
const { WorkSearchResults, WorkSearchPanel, matchedFieldLabel } =
  await import("../src/workspace/agent/WorkSearchPanel.tsx");
const { agentError } = await import("../src/workspace/agent/labels.ts");
const { ApiError } = await import("../src/api.ts");
const common = {
  title: "<script>alert('same name')</script>",
  timestamp: "2026-10-13T06:00:00Z",
  matched_fields: ["current_linked_goal"] as const,
  match_reason: "linked_metadata" as const,
  format: "markdown" as const,
  byte_count: 123,
  recorded_status: "verified" as const,
  source_names: [],
};
const artifacts: WorkSearchHit[] = [
  "current",
  "earlier",
  "unknown",
  "unlinked",
].map((membership, i) => ({
  ...common,
  kind: "artifact",
  id: `artifact-${i}`,
  matched_fields: ["current_linked_goal"],
  output_membership: membership as
    "current" | "earlier" | "unknown" | "unlinked",
  run_id: membership === "unlinked" ? null : "run-linked",
  current_linked_goal:
    membership === "unlinked" ? null : "<img src=x onerror=alert(1)>",
}));
const source: WorkSearchHit = {
  kind: "source",
  id: "source-one",
  title: "来源 notes.csv",
  timestamp: null,
  matched_fields: ["title"],
  match_reason: "phrase",
  format: "csv",
  byte_count: null,
  recorded_status: "unknown",
  revision: 1,
};
const run: WorkSearchHit = {
  kind: "run",
  id: "run-one",
  title: "Current goal 当前目标",
  timestamp: common.timestamp,
  matched_fields: ["source_name"],
  match_reason: "linked_metadata",
  state: "paused",
  version: 7,
  mode: "deterministic",
  plan_revision: 2,
  source_names: ["notes.csv"],
};
const response = (items: WorkSearchHit[]): WorkSearchResponse => ({
  items,
  total: items.length,
  snapshot: "a".repeat(64),
  next_offset: null,
  search_scope: "local_metadata",
  ranking: "lexical_v1",
  file_status_basis: "last_recorded",
});

test("actual results render separate choices, honest relationships and safe text in both languages", () => {
  for (const zh of [false, true]) {
    let opens = 0;
    const t = (en: string, cn: string) => (zh ? cn : en);
    const markup = renderToStaticMarkup(
      createElement(WorkSearchResults, {
        page: response([...artifacts, source, run]),
        t,
        disabled: false,
        opening: null,
        onOpen: () => {
          opens++;
        },
      }),
    );
    assert.equal(opens, 0);
    for (const item of [...artifacts, source, run])
      assert.ok(markup.includes(item.id));
    assert.equal((markup.match(/<li /g) ?? []).length, 6);
    assert.equal((markup.match(/<button /g) ?? []).length, 6);
    assert.doesNotMatch(
      markup,
      /<script>|<img|href=|Download file|Resume|Approve/,
    );
    assert.match(markup, /&lt;script&gt;/);
    assert.match(markup, /&lt;img/);
    for (const label of zh
      ? [
          "找到多个记录",
          "上次记录",
          "已核验",
          "当前输出",
          "较早输出",
          "输出关系未知",
          "未关联工作",
          "当前关联目标",
          "匹配字段",
          "关联来源",
          "日期未知",
          "大小未知",
          "打开此工作",
        ]
      : [
          "Several records match",
          "Last recorded",
          "verified",
          "Current output",
          "Earlier output",
          "Output relationship unknown",
          "No linked work",
          "Current linked goal",
          "Matched fields",
          "Linked sources",
          "Date unknown",
          "Size unknown",
          "Open this work",
        ])
      assert.ok(markup.includes(label), label);
    assert.doesNotMatch(
      markup,
      /Saved bytes independently read back|已独立读回保存字节/,
    );
    assert.equal(matchedFieldLabel("id", t), zh ? "记录ID" : "Record ID");
  }
});
test("actual result rendering disables all choices while exact opening is pending", () => {
  const markup = renderToStaticMarkup(
    createElement(WorkSearchResults, {
      page: response(artifacts),
      t: (en: string) => en,
      disabled: true,
      opening: "artifact:artifact-1",
      onOpen: () => {},
    }),
  );
  assert.equal((markup.match(/disabled=""/g) ?? []).length, 4);
  assert.equal((markup.match(/Opening exact record/g) ?? []).length, 1);
});
test("actual empty private search form states its local scope and has no automatic preview", () => {
  for (const zh of [false, true]) {
    const fence = new ResponseFence();
    fence.update("owner:private", true);
    const markup = renderToStaticMarkup(
      createElement(WorkSearchPanel, {
        t: (en: string, cn: string) => (zh ? cn : en),
        fence,
        epoch: fence.version,
        fresh: true,
        onOpenRun: () => {
          throw new Error("SSR must never open a run");
        },
      }),
    );
    assert.match(markup, zh ? /查找已保存工作/ : /Find saved work/);
    assert.match(
      markup,
      zh ? /不搜索文件正文/ : /File contents are not searched/,
    );
    assert.match(markup, /type="search"/);
    assert.match(markup, /autoComplete="off"/);
    assert.equal((markup.match(/<option /g) ?? []).length, 4);
    assert.doesNotMatch(
      markup,
      /<li |Source preview|Output files|Download file|disabled=""/,
    );
  }
});
test("actual stale search disables query, filter and submit in both languages", () => {
  const fence = new ResponseFence();
  fence.update("owner:private", true);
  for (const zh of [false, true]) {
    const markup = renderToStaticMarkup(
      createElement(WorkSearchPanel, {
        t: (en: string, cn: string) => (zh ? cn : en),
        fence,
        epoch: fence.version,
        fresh: false,
        onOpenRun: () => {},
      }),
    );
    assert.equal((markup.match(/disabled=""/g) ?? []).length, 3);
    assert.match(markup, zh ? /重新打开搜索/ : /Reopen search/);
    assert.doesNotMatch(markup, /artifact-|run-one|source-one/);
  }
});
test("search errors give explicit refresh/record/privacy limits in English and Chinese", () => {
  for (const zh of [false, true]) {
    const t = (en: string, cn: string) => (zh ? cn : en);
    for (const code of [
      "WORK_SEARCH_CHANGED",
      "WORK_SEARCH_CAPACITY_EXCEEDED",
      "WORK_SEARCH_METADATA_INVALID",
      "WORK_SEARCH_PRIVACY_CHANGED",
      "WORK_SEARCH_RESPONSE_INVALID",
      "WORK_SEARCH_QUERY_LIMIT",
    ]) {
      const label = agentError(new ApiError(code, 409), t);
      assert.ok(label.length > 10);
      assert.ok(!label.includes(code));
    }
    assert.match(
      agentError(new ApiError("WORK_SEARCH_CHANGED", 409), t),
      zh ? /第一页/ : /first page/,
    );
  }
});
