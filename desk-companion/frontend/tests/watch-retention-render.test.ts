import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
register(new URL("./fixtures/render-tsx-loader.mjs", import.meta.url));
const { RetentionConfirmation, WatchUsage } =
  await import("../src/workspace/responsibilities/WatchRetention.tsx");
const { watchError } =
  await import("../src/workspace/responsibilities/labels.ts");
const usage = {
  version: 1,
  retained_count: 20,
  trashed_count: 4,
  lifetime_count: 256,
  lifetime_limit: 256,
  lifetime_remaining: 0,
  state: "known",
};
const preview = {
  kind: "watch_retention_preview",
  preview_id: "preview-one",
  action: "purge",
  responsibility: {
    id: "opaque-watch-one",
    title: "<script>Synthetic history</script>",
    status: "cancelled",
    version: 3,
    retention_version: 2,
    retention_state: "trashed",
  },
  counts: {
    definitions: 1,
    source_baselines: 2,
    retained_reviews: 9,
    operation_receipts: 8,
  },
  retained_operation_receipts_after: 9,
  logical_slots_released: 1,
  receipts_retained: true,
  independent_tasks_retained: true,
  independent_work_retained: true,
  expires_at: "2026-10-13T12:05:00Z",
  maintenance_usage: usage,
  revision: 9,
};
test("bilingual actual permanent confirmation gives exact target/counts/loss/retained receipts without sending", () => {
  for (const zh of [false, true]) {
    let clicks = 0,
      cancels = 0;
    const html = renderToStaticMarkup(
      createElement(RetentionConfirmation, {
        preview,
        t: (en: string, cn: string) => (zh ? cn : en),
        disabled: false,
        onConfirm: () => clicks++,
        onCancel: () => cancels++,
      }),
    );
    assert.equal(clicks + cancels, 0);
    assert.match(html, /role="alertdialog"/);
    assert.match(html, /opaque-watch-one/);
    assert.match(html, /&lt;script&gt;/);
    assert.doesNotMatch(html, /<script>/);
    for (const expression of zh
      ? [
          /永久移除此确切历史/,
          /释放的逻辑保存位置.*1/,
          /来源基线.*2/,
          /保存的变化审阅.*9/,
          /操作后保留的不含正文回执.*9/,
          /无法通过正常产品恢复撤销/,
          /独立开始的工作保持不变/,
          /不会擦除备份/,
          /取消并保持不变/,
        ]
      : [
          /Permanently remove this exact history/,
          /Logical saved-watch slots released.*1/,
          /Source baselines.*2/,
          /Saved change reviews.*9/,
          /Opaque operation receipts retained afterward.*9/,
          /Normal product recovery cannot undo it/,
          /independently started Work stay untouched/,
          /does not erase backups/,
          /Cancel, keep unchanged/,
        ])
      assert.match(html, expression);
    const disabled = renderToStaticMarkup(
      createElement(RetentionConfirmation, {
        preview,
        t: (en: string) => en,
        disabled: true,
        onConfirm() {},
        onCancel() {},
      }),
    );
    assert.equal((disabled.match(/disabled=""/g) ?? []).length, 2);
  }
});
test("Trash and Restore bilingual confirmation expressly preserve capacity and never restart", () => {
  for (const action of ["trash", "restore"])
    for (const zh of [false, true]) {
      const html = renderToStaticMarkup(
        createElement(RetentionConfirmation, {
          preview: { ...preview, action, logical_slots_released: 0 },
          t: (en: string, cn: string) => (zh ? cn : en),
          disabled: false,
          onConfirm() {
            throw Error("automatic mutation");
          },
          onCancel() {},
        }),
      );
      assert.match(
        html,
        zh ? /释放的逻辑保存位置.*0/ : /Logical saved-watch slots released.*0/,
      );
      assert.match(
        html,
        action === "restore"
          ? zh
            ? /不会重新开始关注/
            : /never resumes the watch/
          : zh
            ? /仍占保存位置/
            : /saved-watch slot is still used/,
      );
      assert.doesNotMatch(
        html,
        /Permanently remove this exact history|永久移除此确切历史/,
      );
    }
});
test("capacity markup uses explicit retained aggregate despite Trash omission, lifetime full and unknown states", () => {
  for (const zh of [false, true]) {
    const t = (en: string, cn: string) => (zh ? cn : en);
    const html = renderToStaticMarkup(
      createElement(WatchUsage, { usage, limit: 20, t }),
    );
    assert.match(html, /20\/20/);
    assert.match(html, /256\/256/);
    assert.match(html, zh ? /0 剩余位置/ : /0 slots remaining/);
    assert.match(html, zh ? /清理不会重置/ : /cleanup cannot reset/);
    for (const value of [
      undefined,
      {
        ...usage,
        state: "unavailable",
        retained_count: null,
        trashed_count: null,
        lifetime_count: null,
        lifetime_remaining: null,
      },
      { ...usage, retained_count: false },
    ]) {
      const unknown = renderToStaticMarkup(
        createElement(WatchUsage, { usage: value, limit: 20, t }),
      );
      assert.match(unknown, zh ? /用量未知/ : /Unknown usage/);
      assert.doesNotMatch(unknown, /0\/20|20 slots remaining|20 剩余位置/);
    }
  }
});
test("all lifecycle errors explain actionable bounded recovery in English and Chinese", () => {
  for (const code of [
    "RESPONSIBILITY_REMOVED",
    "RESPONSIBILITY_RETENTION_INVALID",
    "RESPONSIBILITY_RETAINED_STATE_REQUIRED",
    "RESPONSIBILITY_PREVIEW_EXPIRED",
    "RESPONSIBILITY_PREVIEW_CHANGED",
    "RESPONSIBILITY_METADATA_LIMIT",
    "RESPONSIBILITY_METADATA_UNAVAILABLE",
    "RESPONSIBILITY_NOT_TERMINAL",
  ]) {
    const en = watchError({ code }, (en: string) => en),
      zh = watchError({ code }, (_en: string, zh: string) => zh);
    assert.ok(en.length > 25);
    assert.match(zh, /[\u4e00-\u9fff]/);
    assert.notEqual(en, zh);
  }
});
