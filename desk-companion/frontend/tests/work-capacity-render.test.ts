import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import type { WorkCapacity } from "../src/workspace/agent/workCapacity.ts";
register(new URL("./fixtures/render-tsx-loader.mjs", import.meta.url));
const { WorkCapacitySummary, OutputCapacityHint, capacityBytes } =
  await import("../src/workspace/agent/RetainedCapacity.tsx");
const dim = { limit: 9, used: 9, remaining: 0, state: "known" as const };
const value: WorkCapacity = {
  basis: "retained_reservations",
  observed_at: "2026-10-13T07:00:00Z",
  advisory: true,
  sources: { count: dim, bytes: dim, file_bytes: 123 },
  artifacts: {
    count: dim,
    bytes: dim,
    file_bytes: 45,
    per_run_count: 6,
    per_run_bytes: 234,
  },
  runs: { count: dim },
  watches: { count: dim },
};
test("actual bilingual retained-capacity rendering states known full unknown and over-limit honestly", () => {
  for (const zh of [false, true]) {
    const t = (en: string, cn: string) => (zh ? cn : en);
    const full = renderToStaticMarkup(
      createElement(WorkCapacitySummary, { t, value }),
    );
    assert.match(full, /9\/9/);
    assert.match(full, zh ? /无剩余额度/ : /No remaining capacity/);
    assert.match(full, zh ? /并非磁盘/ : /not disk usage/);
    assert.match(full, zh ? /不会释放容量/ : /does not free capacity/);
    assert.doesNotMatch(full, /disabled=|<meter|<progress/);
    const missing = renderToStaticMarkup(
      createElement(WorkCapacitySummary, { t, value: null }),
    );
    assert.match(missing, zh ? /容量不可用/ : /Capacity unavailable/);
    assert.doesNotMatch(missing, /0\/|NaN/);
    const anomaly = structuredClone(value);
    anomaly.sources.count = {
      limit: 9,
      used: null,
      remaining: null,
      state: "over_limit",
    };
    anomaly.sources.bytes = {
      limit: 9,
      used: null,
      remaining: null,
      state: "unavailable",
    };
    const bad = renderToStaticMarkup(
      createElement(WorkCapacitySummary, { t, value: anomaly }),
    );
    assert.match(bad, zh ? /已超上限/ : /Over limit/);
    assert.match(bad, zh ? /不可用/ : /Unavailable/);
    assert.doesNotMatch(bad, /null|NaN/);
    const hint = renderToStaticMarkup(
      createElement(OutputCapacityHint, { t, value, deterministic: true }),
    );
    assert.match(hint, /45/);
    assert.match(hint, /234/);
    assert.match(hint, zh ? /不足两个/ : /fewer than two/);
    assert.match(
      hint,
      zh ? /同一操作仍可重试/ : /Existing-operation retries remain available/,
    );
    assert.doesNotMatch(hint, /disabled=/);
  }
});

test("storage disclosure starts collapsed with counts and warnings visible; byte labels are readable and exact when rounded", () => {
  const t = (en: string) => en;
  const full = renderToStaticMarkup(
    createElement(WorkCapacitySummary, { t, value, refresh: () => {} }),
  );
  assert.match(full, /<details class="agent-capacity"><summary>/);
  assert.doesNotMatch(full, /<details[^>]* open/);
  const summary = full.split("</summary>")[0];
  assert.match(summary, /Saved work storage/);
  assert.match(summary, /Sources: 9\/9/);
  assert.match(summary, /No remaining capacity/);
  assert.match(full, /Refresh capacity/);
  const unknown = renderToStaticMarkup(
    createElement(WorkCapacitySummary, { t, value: null }),
  ).split("</summary>")[0];
  assert.match(unknown, /Capacity unavailable/);
  assert.equal(capacityBytes(1048576, t), "1 MiB");
  assert.equal(capacityBytes(262144, t), "256 KiB");
  assert.match(capacityBytes(1025, t), /1025 bytes/);
});
