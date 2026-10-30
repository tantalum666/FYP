import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
register(new URL("./fixtures/render-tsx-loader.mjs", import.meta.url));
const { WatchReviewCard } =
  await import("../src/workspace/responsibilities/WatchReviewCard.tsx");
const { watchError } =
  await import("../src/workspace/responsibilities/labels.ts");
const review = {
  id: "review-one",
  responsibility_id: "watch-one",
  sequence: 1,
  version: 2,
  delivery_state: "pending",
  changed_ids: ["one"],
  changed_fields: ["status", "progress"],
  first_observed_at: "2026-10-13T10:00:00Z",
  last_observed_at: "2026-10-13T11:00:00Z",
  catch_up: true,
  result_code: "SELECTED_TASK_FIELDS_CHANGED",
  title_source: "current_record",
};
const detail = {
  responsibility: { id: "watch-one", task_ids: ["one", "two"] },
  selected_tasks: [
    {
      id: "one",
      title: "<script>Synthetic current title</script>",
      available: true,
      version: 2,
    },
    { id: "two", title: "Synthetic other", available: true, version: 1 },
  ],
  reviews: [review],
};
test("actual bilingual review markup separates historical metadata/current titles, ack and Work", () => {
  for (const zh of [false, true]) {
    let ack = 0,
      compile = 0,
      inspect = 0;
    const markup = renderToStaticMarkup(
      createElement(WatchReviewCard, {
        review,
        detail,
        t: (en: string, cn: string) => (zh ? cn : en),
        disabled: false,
        onAcknowledge: () => ack++,
        onCompile: () => compile++,
        onInspect: () => inspect++,
      }),
    );
    assert.equal(ack + compile + inspect, 0);
    assert.match(markup, zh ? /所选事务有更新/ : /Selected task changes/);
    assert.match(markup, zh ? /已查看/ : /Acknowledge/);
    assert.match(
      markup,
      zh ? /整理当前事务证据/ : /Compile current task evidence/,
    );
    assert.match(markup, zh ? /不是历史快照/ : /not historical snapshots/);
    assert.match(markup, zh ? /独立审阅范围/ : /own scope review/);
    assert.match(markup, /&lt;script&gt;/);
    assert.doesNotMatch(markup, /<script>/);
    const stale = renderToStaticMarkup(
      createElement(WatchReviewCard, {
        review,
        detail,
        t: (en: string, cn: string) => (zh ? cn : en),
        disabled: true,
        onAcknowledge() {},
        onCompile() {},
        onInspect() {},
      }),
    );
    assert.equal((stale.match(/disabled=""/g) ?? []).length, 3);
    const unavailable = renderToStaticMarkup(
      createElement(WatchReviewCard, {
        review,
        detail: {
          ...detail,
          selected_tasks: detail.selected_tasks.slice(0, 1),
        },
        t: (en: string, cn: string) => (zh ? cn : en),
        disabled: false,
        onAcknowledge() {},
        onCompile() {},
        onInspect() {},
      }),
    );
    assert.match(unavailable, zh ? /不会自动缩小/ : /will not silently shrink/);
    assert.match(unavailable, /disabled=""/);
  }
});
test("watch-specific failures explain recovery in both languages without source text", () => {
  for (const code of [
    "RESPONSIBILITY_SCOPE_CHANGED",
    "RESPONSIBILITY_SOURCE_UNAVAILABLE",
    "RESPONSIBILITY_SOURCE_KIND_UNSUPPORTED",
    "RESPONSIBILITY_NOT_FOUND",
    "RESPONSIBILITY_CLOSED",
    "RESPONSIBILITY_LIMIT",
    "RESPONSIBILITY_ACTION_INVALID",
    "RESPONSIBILITY_EXPIRY_INVALID",
    "RESPONSIBILITY_OPERATION_LIMIT",
    "REVIEW_NOT_FOUND",
    "REVIEW_CHANGED",
    "REVIEW_NOT_PENDING",
    "VERSION_CONFLICT",
  ]) {
    const en = watchError({ code }, (en: string) => en),
      zh = watchError({ code }, (_en: string, cn: string) => cn);
    assert.ok(en.length > 15);
    assert.match(zh, /[\u4e00-\u9fff]/);
    assert.notEqual(en, zh);
    assert.doesNotMatch(en, /Secret/);
  }
});
